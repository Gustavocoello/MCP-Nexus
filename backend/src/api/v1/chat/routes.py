from ast import stmt
import os
import json
import asyncio
import threading
from queue import Queue, Empty
from sqlalchemy import select, delete
from werkzeug.utils import secure_filename
from src.config.time_helper import get_now
from src.database.models.models import Chat, Message, Document, User, UserToken
from src.database.config.connection import SessionLocal
from src.services.cache.redis_sidebar import SidebarCache
from src.services.cache.redis_cache import ChatCache
from src.config.logging_config import get_logger
from src.services.integrations.onedrive_service import upload_to_onedrive, get_user_onedrive_token
from src.services.llm.providers.utils import generate_prompt, extract_text_from_file, analyze_image_with_azure, can_upload_image
from src.services.llm.llm_router import completion,completion_stream
from src.services.llm.chat.chat_service import build_payload, execute_mcp_tool
from src.services.llm.memory.service import MAX_RAW, summarize_and_trim
from src.services.auth.clerk.clerk_middleware import clerk_required
from src.services.auth.mcp.mcp_jwt import generate_mcp_jwt
from flask import Blueprint, jsonify, Response, request, stream_with_context, session, copy_current_request_context, g
from src.mcps.client.client_manager import MCPClientManager

# -- Logger --
logger = get_logger('routes')
# -- Event Queue --
event_queue = Queue()
# -- MCP Client --
mcp_client = MCPClientManager(user_id=None)  # user_id se asignará dinámicamente en cada llamada

## -------------- Mensajes de la IA con memoria -----------
chat_bp = Blueprint('chat', __name__, url_prefix='/api/chat')

## ----------- Mensajes de la IA sin memoria --------------
""" Create a blueprint for search API """
search_bp = Blueprint('search', __name__, url_prefix='/api/search')

@search_bp.route("/prompt", methods=["POST"])
def handle_search_prompt():
    # Limitar a 5 intentos por sesión para usuarios anónimos
    counter = session.get('anon_prompt_count', 0)

    if counter >= 5:
        return jsonify({
            "error": "Has alcanzado el límite de 5 mensajes de prueba.",
            "login_required": True
        }), 403

    session['anon_prompt_count'] = counter + 1
    logger.debug(f'print:{counter}')
    print("BODY RECIBIDO:", request.json)
    try:
        data = request.json

        if not data or 'prompt' not in data:
            logger.error("No prompt received in request")
            return jsonify({"error": "Se requiere un prompt"}), 400

        logger.debug(f"Search prompt recibido: {data['prompt']}")
        
        result = generate_prompt({"description": data['prompt']})

        if result == "Todos los servicios de IA no estan disponibles actualmente.":
            return jsonify({"error": result}), 503
        
        return jsonify({
            "result": result,
            "remaining": max(0, 5 - session['anon_prompt_count'])
        })

    except Exception as e:
        error_msg = f"Error al procesar prompt: {str(e)}"
        logger.exception(error_msg)
        return jsonify({"error": error_msg}), 500


# ------------- route principal -------------

#--------------- EVENTS QUEUE ---------------
@chat_bp.route("/events")
def events():
    def stream():
        while True:
            try:
                # Espera un evento pero con un timeout de 20 segundos
                # Esto evita que el hilo se quede bloqueado para siempre
                try:
                    event = event_queue.get(timeout=20)
                    yield f"data: {json.dumps(event)}\n\n"
                except Empty:
                    # Esto es un "keep-alive" para que el navegador no cierre la conexión
                    yield f"data: {json.dumps({'type': 'ping'})}\n\n"
            except Exception as e:
                logger.error(f"Error en stream SSE: {e}")
                break

    return Response(stream(), mimetype="text/event-stream")
# ----------------- GET ---------------------
@chat_bp.route('', methods=['GET'], strict_slashes=False)
@clerk_required
def get_all_chats():
    db_session = SessionLocal()
    try:
        # get_chats intenta Redis, si falla va a DB, guarda en Redis y te lo da.
        chats = SidebarCache.get_chats(g.user_id, db_session=db_session)
        return jsonify(chats)
    except Exception as e:
        logger.exception("Error al obtener chats")
        return jsonify({"error": str(e)}), 500
    finally:
        db_session.close()
        
@chat_bp.route('/<chat_id>/messages/recent', methods=['GET'])
@clerk_required
def get_recent_messages(chat_id):
    db_session = SessionLocal()
    try:
        # Redis (ChatCache ya tiene lógica de fallback)
        messages = ChatCache.get_messages(chat_id, db_session=db_session)
        
        return jsonify(messages)
    except Exception as e:
        logger.exception(f"Error en mensajes recientes de {chat_id}")
        return jsonify({"error": str(e)}), 500
    finally:
        db_session.close()

@chat_bp.route('/<chat_id>/messages', methods=['GET'])
@clerk_required
def get_chat_messages(chat_id):
    db_session = SessionLocal()
    try:
        chat = db_session.query(Chat).filter(Chat.id == chat_id, Chat.user_id == g.user_id).first()
        if not chat:
            logger.warning(f"Chat no encontrado o acceso denegado al chat {chat_id}")
            return jsonify({'error': 'Chat no encontrado o acceso denegado'}), 404
        
        stmt = select(Message).where(Message.chat_id == chat_id).order_by(Message.created_at.asc())
        messages = db_session.execute(stmt).scalars().all()
        
        return jsonify([{
            "id": msg.id,
            "role": msg.role,
            "content": msg.content,
            "created_at": msg.created_at.isoformat()
        } for msg in messages])
        
    except Exception as e:
        logger.exception("Error al obtener mensajes del chat")
        return jsonify({"error": str(e)}), 500
    finally:
        db_session.close()
    
# ----------------- DELETE -------------------
    
@chat_bp.route('/<chat_id>', methods=['DELETE'])
@clerk_required
def delete_chat(chat_id):
    db_session = SessionLocal() # Inicia sesión
    try: 
        # 1. BUSCAMOS EL CHAT (Solo una línea, usando la sesión)
        chat = db_session.query(Chat).filter(Chat.id == chat_id, Chat.user_id == g.user_id).first()
        
        # 2. VALIDACIÓN
        if not chat:
            return jsonify({"error": "Chat no encontrado o acceso denegado"}), 403

        # 3. ACCIÓN
        db_session.delete(chat)
        db_session.commit() # Guarda los cambios en la DB (Windows/Linux)
        
        # === AVISAR A REDIS ===
        SidebarCache.invalidate_user(g.user_id)
        print(f"[Redis] Sidebar invalidado por eliminación de chat: {chat_id}")
        
        return jsonify({"message": "Chat eliminado correctamente"}), 200

    except Exception as e:
        db_session.rollback() # Si algo falla, deshace el intento de borrado
        logger.exception("Error al eliminar chat")
        return jsonify({"error": str(e)}), 500
    finally:
        db_session.close() 


# ----------------- POST ---------------------  
  
# ------------ POST (crear chat) -------------    
@chat_bp.route('', methods=['POST'], strict_slashes=False)
@clerk_required
def create_chat():
    db_session = SessionLocal() # Inicia la sesión manual
    try:
        if not g.user_id:
            return jsonify({"error": "Usuario no autenticado"}), 401

        # CREACIÓN DEL CHAT
        # Simplemente creamos el objeto y lo añadimos a la sesión
        new_chat = Chat(user_id=g.user_id, title="Sin título")
        
        db_session.add(new_chat)
        db_session.commit() # Guarda en la DB (Windows o Linux)
        
        print(f"[DEBUG] Nuevo chat creado para: {g.user_id}")
        
        # === AVISAR A REDIS ===
        SidebarCache.invalidate_user(g.user_id)
        print(f"[Redis] Sidebar invalidado por creación de chat: {new_chat.id}")
        
        return jsonify({
            "id": new_chat.id,
            "title": new_chat.title,
            "created_at": new_chat.created_at.isoformat()
        }), 201

    except Exception as e:
        db_session.rollback() # Si falla la conexión, cancela la operación
        logger.exception("Error al crear chat")
        return jsonify({"error": str(e)}), 500
        
    finally:
        db_session.close()

# --------------- POST (enviar mensaje) ---------------
@chat_bp.route('/<chat_id>/message', methods=['POST'], strict_slashes=False)
@clerk_required
def send_message(chat_id):
    db_session = SessionLocal()
    try:
        # 1. Find or create chat
        chat = db_session.query(Chat).filter(
            Chat.id == chat_id,
            Chat.user_id == g.user_id
        ).first()

        if not chat:
            chat = Chat(id=chat_id, user_id=g.user_id, title="Sin titulo")
            db_session.add(chat)
            db_session.flush()
        elif chat.user_id != g.user_id:
            return jsonify({"error": "Access denied"}), 403

        # 2. Validate input
        user_text = (request.json.get("text") or "").strip()
        if not user_text:
            return jsonify({"error": "Empty message"}), 400

        # 3. Save user message
        chat.updated_at = get_now()
        user_message = Message(chat_id=chat.id, role="user", content=user_text)
        db_session.add(user_message)

        # 4. Handle image / file context
        hidden_context = request.json.get("hidden_context", "").strip()
        if hidden_context:
            db_session.query(Message).filter_by(chat_id=chat.id, role="context").delete()
            context_msg = Message(chat_id=chat.id, role="context", content=hidden_context)
            db_session.add(context_msg)

        db_session.commit()

        # 5. Fetch recent messages for context window
        recent = (
            db_session.query(Message)
            .filter(
                Message.chat_id == chat.id,
                Message.role != "context",
                Message.id != user_message.id  # excluye el que acabas de insertar
            )
            .order_by(Message.created_at.desc())
            .limit(MAX_RAW)
            .all()[::-1]
        )

        # 6. Execute MCP tool if requested
        tool_name = (request.json.get("tool") or "").strip()
        params = request.json.get("params", {})
        mcp_context = None

        if tool_name:
            mcp_context = execute_mcp_tool(
                tool_name=tool_name,
                params=params,
                user_id=g.user_id,
                db_session=db_session,
                chat_id=chat.id,
                mcp_manager=mcp_manager
            )
            if mcp_context is None:
                return jsonify({"error": f"Tool '{tool_name}' requires Google Calendar connection."}), 400

        # 7. Build LLM payload
        payload = build_payload(
            chat=chat,
            recent=recent,
            user_text=user_text,
            hidden_context=hidden_context,
            mcp_context=mcp_context
        )

        # 8. Auto-generate title on first message
        if not chat.title or chat.title == "Sin titulo":
            words = user_text.split()
            chat.title = " ".join(words[:10]) + ("..." if len(words) > 10 else "")
            db_session.add(chat)
            db_session.commit()
            SidebarCache.invalidate_user(g.user_id)

        # 9. Stream response
        def generate():
            gen_session = SessionLocal()
            try:
                full_reply = ""
                for chunk in completion_stream(payload):
                    full_reply += chunk
                    yield chunk

                inner_chat = gen_session.get(Chat, chat_id)
                inner_chat.updated_at = get_now()

                new_msg = Message(chat_id=chat_id, role="assistant", content=full_reply)
                gen_session.add(new_msg)

                summarize_and_trim(inner_chat, gen_session)
                gen_session.commit()

                ChatCache.append_message(chat_id, {
                    "id": new_msg.id,
                    "role": "assistant",
                    "content": full_reply,
                    "created_at": get_now().isoformat()
                })

            except Exception as e:
                gen_session.rollback()
                logger.exception("Error during stream")
                yield "\n[ERROR] " + str(e)
            finally:
                gen_session.close()

        return Response(stream_with_context(generate()), content_type="text/plain")

    except Exception as e:
        db_session.rollback()
        logger.exception("Error in send_message")
        return jsonify({"error": str(e)}), 500
    finally:
        db_session.close()
        
# --------------- POST (extraer texto de archivos) ---------------
@chat_bp.route('/extract_file', methods=['POST'])
@clerk_required
def extract_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Empty filename'}), 400

    original_filename = file.filename
    original_name_base, ext = os.path.splitext(file.filename)
    timestamp = get_now().strftime("%Y%m%d_%H%M%S")
    filename = secure_filename(f"{original_name_base}_{timestamp}{ext}")

    content_type = file.content_type
    file_bytes = file.read()
    final_text = ""

    try:
        if content_type.startswith("image/"):
            try:
                final_text = analyze_image_with_azure(file_bytes)
                logger.info(f"Text extracted from image {original_filename}")
                resp_text = f"Image '{original_filename}':\n\n{final_text}"
            except Exception as e:
                logger.error(f"Azure Vision error: {str(e)}")
                return jsonify({"error": f"Azure Vision error: {str(e)}"}), 500
        else:
            from io import BytesIO
            file_stream = BytesIO(file_bytes)
            final_text = extract_text_from_file(file_stream, original_filename)
            resp_text = f"File content '{original_filename}':\n\n{final_text}"

        @copy_current_request_context
        def background_task(file_bytes, filename_bd, content_type, user_id, text_to_store, filename_ui):
            bg_session = SessionLocal()
            try:
                event_queue.put({"type": "upload_started", "filename": filename_ui, "user_id": user_id})
                logger.info(f"Background upload started: {filename_ui}")

                access_token = get_user_onedrive_token(user_id)
                if not access_token:
                    event_queue.put({"type": "upload_error", "filename": filename_ui, "error": "No OneDrive token"})
                    return

                download_url = upload_to_onedrive(access_token, filename_bd, file_bytes)

                document = Document(
                    user_id=user_id,
                    filename=filename_bd,
                    content=text_to_store,
                    mime_type=content_type,
                    file_size=len(file_bytes),
                    url=download_url,
                    source="onedrive",
                    tag="user_upload_mcp"
                )

                bg_session.add(document)
                bg_session.commit()

                event_queue.put({
                    "type": "upload_completed",
                    "filename": filename_ui,
                    "url": download_url,
                    "user_id": user_id
                })

            except Exception as e:
                bg_session.rollback()
                logger.exception("Background task error")
                event_queue.put({"type": "upload_error", "filename": filename_ui, "error": str(e)})
            finally:
                bg_session.close()
                
        user_uuid = g.user_id

        threading.Thread(
            target=background_task,
            args=(file_bytes, filename, content_type, user_uuid, final_text, original_filename),
            daemon=True
        ).start()

        return jsonify({"text": resp_text})

    except Exception as e:
        logger.exception("Error processing file")
        return jsonify({'error': str(e)}), 500

# --------------- PUT ---------------
@chat_bp.route('/<chat_id>/title', methods=['PUT'])
@clerk_required
def update_chat_title(chat_id):
    db_session = SessionLocal()
    try:
        chat = db_session.query(Chat).filter(Chat.id == chat_id, Chat.user_id == g.user_id).first()
        if not chat or chat.user_id != g.user_id:
            return jsonify({'error': 'Acceso denegado'}), 403
        
        data = request.get_json()
        new_title = data.get('title')

        chat.title = new_title
        db_session.commit()
        
        # === AVISAR A REDIS ===
        SidebarCache.invalidate_user(g.user_id)
        print(f"[Redis] Sidebar invalidado por actualización de título del chat: {chat_id}")

        return jsonify({'message': 'Título actualizado', 'title': new_title})
    except Exception as e:
        db_session.rollback()
        logger.exception("Error actualizando título del chat")
        return jsonify({'error': str(e)}), 500
    finally:
        db_session.close()
