from ast import stmt
import os
import json
import asyncio
import threading
from extensions import db
from queue import Queue, Empty
from sqlalchemy import select, delete
from datetime import datetime, timezone
from werkzeug.utils import secure_filename
from src.database.models.models import TIMEZONE, Chat, Message, Document, UserToken
from src.database.config.connection import SessionLocal
from src.services.cache.redis_sidebar import SidebarCache
from src.services.cache.redis_cache import ChatCache
from src.config.logging_config import get_logger
from src.services.integrations.onedrive_service import upload_to_onedrive, get_user_onedrive_token
from src.services.llm.providers.utils import generate_prompt, extract_text_from_file, analyze_image_with_azure, can_upload_image
from src.services.llm.llm_router import completion,completion_stream
from src.services.auth.clerk.clerk_middleware import clerk_required
from src.services.auth.mcp.mcp_jwt import generate_mcp_jwt
#from src.services.llm.memory.service import get_user_memory, save_memory
#from src.services.llm.memory.utils import build_memory_context, extract_memory_from_text, calculate_priority, classify_memory
from flask import Blueprint, jsonify, Response, request, stream_with_context, session, copy_current_request_context, g
from src.mcps.client.client_manager import mcp_manager
from src.mcps.client.utils.utils import safe_serialize_call_result
from src.services.auth.utils.token_crypto import encrypt_token

# -- Logger --
logger = get_logger('routes')
# -- Event Queue --
event_queue = Queue()
# -- MCP Client --
mcp_client = mcp_manager

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


## -------------- Mensajes de la IA con memoria --------------
chat_bp = Blueprint('chat', __name__, url_prefix='/api/chat')

MAX_RAW   = 10
MAX_TOTAL = 40

# helpers (build_payload, summarize_and_trim) …
# --------------- Helpers ----------------
def build_payload(chat, recent, user_text, memory_context=None, hidden_context=None, mcp_context=None):
    messages = [] 
    if memory_context:
        messages.append({
            "role": "system",
            "content": f"Here is helpful user information:\n{memory_context}"
        })

    if hidden_context:
        messages.append({
            "role": "system",
            "content": (
                "You will now receive text extracted via OCR from an image or "
                "content from an uploaded file. This is *textual* information only, "
                "not a visual. Use this information to respond to the user's question. "
                "Do not mention inability to see images."
            )
        })
        messages.append({
            "role": "system",
            "content": hidden_context
        })
    
    if mcp_context:
        messages.append({
            "role": "system",
            "content": (
                "You have received structured data from a tool (MCP). "
                "Use this information to provide an accurate answer to the user. "
                "Do not mention the tool explicitly."
            )
        })
        messages.append({"role": "system", "content": mcp_context})

    if chat.summary:
        messages.append({
            "role": "system",
            "content": f"Conversation summary so far:\n{chat.summary}"
        })

    for m in recent:
        messages.append({"role": m.role, "content": m.content})

    messages.append({"role": "user", "content": user_text})
    return messages

def summarize_and_trim(chat, db_session):
    # 1. Obtener todos los mensajes usando la sintaxis de Session.execute
    stmt = select(Message).filter_by(chat_id=chat.id).order_by(Message.created_at.asc())
    all_msgs = db_session.execute(stmt).scalars().all()
    
    if len(all_msgs) <= MAX_TOTAL:
        return

    # 2. Dividir mensajes (los que se resumen y los que se quedan)
    to_summarize = all_msgs[:-MAX_RAW] 
    
    summary_prompt = [
        {"role": "system", "content": "Resume brevemente la siguiente conversación:"},
        *[{"role": m.role, "content": m.content} for m in to_summarize]
    ]
    
    # 3. Generar el resumen
    new_summary = completion(summary_prompt)
    logger.info(f"Nuevo resumen: {new_summary}")

    # 4. Actualizar el chat
    chat.summary = ((chat.summary or "") + "\n" + new_summary).strip()
    
    # 🚀 PASO CLAVE: Si agregamos updated_at, actualízalo aquí también
    if hasattr(chat, 'updated_at'):
        chat.updated_at = datetime.now(timezone.utc)
        
    db_session.add(chat)

    # 5. Borrar mensajes antiguos de forma eficiente (SQLAlchemy 2.0 style)
    ids_to_delete = [m.id for m in to_summarize]
    delete_stmt = delete(Message).where(Message.id.in_(ids_to_delete))
    
    db_session.execute(delete_stmt)
    db_session.commit()
    print(f"Se resumieron y eliminaron {len(ids_to_delete)} mensajes.")


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


@chat_bp.route('/<chat_id>/message', methods=['POST'], strict_slashes=False)
@clerk_required
def send_message(chat_id):
    db_session = SessionLocal()
    try:
        # Sintaxis correcta de query
        chat = db_session.query(Chat).filter(Chat.id == chat_id, Chat.user_id == g.user_id).first()
        # 1. Buscar o crear el chat
        if not chat:
            chat = Chat(id=chat_id, user_id=g.user_id, title="Sin título")
            db_session.add(chat)
            db_session.flush()
        elif chat.user_id != g.user_id:
            return jsonify({"error": "Acceso denegado"}), 403
        
        # 2. Validar texto del usuario
        user_text = (request.json.get("text") or "").strip()
        if not user_text:
            return jsonify({"error": "Texto vacío"}), 400

        print("BODY RECIBIDO:", request.json)

        # 3. Guardar el mensaje del usuario y actualizar timestamp
        chat.updated_at = datetime.now(TIMEZONE)        
        user_message = Message(chat_id=chat.id, role="user", content=user_text)
        db_session.add(user_message)

        hidden_context = request.json.get("hidden_context", "").strip()

        # 4. Manejo de Contexto Oculto (si existe)
        if hidden_context:
            # Usar db_session siempre
            db_session.query(Message).filter_by(chat_id=chat.id, role="context").delete()
            context_msg = Message(chat_id=chat.id, role="context", content=hidden_context)
            db_session.add(context_msg)
        
        db_session.commit()

        recent = (db_session.query(Message)
                  .filter(Message.chat_id == chat.id, Message.role != "context")
                  .order_by(Message.created_at.desc())
                  .limit(MAX_RAW).all()[::-1])
            
        # 5. Lógica de Herramientas (MCP)
        tool_name = request.json.get("tool", "").strip()
        params = request.json.get("params", {})
        mcp_context = None            

        if tool_name:    
            try:
                mcp_auth_token = generate_mcp_jwt(g.user_id, "google_calendar")
                    
                if not mcp_auth_token:
                    print(f"[Jarvis] No se pudo generar JWT para user_id={g.user_id}")
                    return jsonify({"error": f"La herramienta '{tool_name}' requiere conexión con Google Calendar."}), 400
                        
                loop = asyncio.new_event_loop() 
                try:
                    result = loop.run_until_complete(
                        mcp_manager.call_tool_with_auth(
                            tool_name=tool_name, 
                            user_id=g.user_id, 
                            auth_token=mcp_auth_token,
                            **params
                        )
                    )
                finally:
                    loop.close()
                    print(f"MCP Results: ({tool_name}):", result)
                        
                response_context = getattr(result, 'context', {})    
                if "google_new_access_token" in response_context:
                    new_access = response_context["google_new_access_token"]
                    new_refresh = response_context.get("google_new_refresh_token")
                        
                    token_entry = db_session.query(UserToken).filter(
                        UserToken.user_id ==g.user_id, 
                        UserToken.provider == "google_calendar"
                    ).first()
                    
                    if token_entry:
                        token_entry.access_token = encrypt_token(new_access)
                        if new_refresh:
                            token_entry.refresh_token = encrypt_token(new_refresh)
                        db_session.add(token_entry)
                        db_session.commit()
                        print("[Jarvis] Google Token refrescado y persistido.")
                    else:
                        # Si la tabla está vacía, debemos crear el registro inicial
                        print(f"[Jarvis] No se encontró registro para {g.user_id}, creando uno nuevo...")
                        new_token = UserToken(
                            user_id=g.user_id,
                            provider="google_calendar",
                            access_token=encrypt_token(new_access),
                            refresh_token=encrypt_token(new_refresh) if new_refresh else None
                        )
                        
                        db_session.add(new_token)
                        db_session.commit()
                        print("[Jarvis] Google Token creado y persistido.")
                    
                result_dict = safe_serialize_call_result(result)
                mcp_context = json.dumps({
                    "response": result_dict,
                    "tool_used": tool_name,
                    "token_refreshed": "google_new_access_token" in response_context
                })

                # Message es la clase, no atributo de sesión
                mcp_msg = Message(
                    chat_id=chat.id,
                    role="mcp-tool",
                    content=mcp_context
                )
                db_session.add(mcp_msg)
                db_session.commit()

            except Exception as e:
                print("Error MCP:", e)
                
        # 6. Preparar historial para el modelo
        payload = build_payload(chat, recent, user_text, hidden_context=hidden_context, mcp_context=mcp_context)
        print("🔍 PAYLOAD ANTES DEL MODELO:", payload)
        
        # ======= STREAMING RESPONSE ========
        # 7. Logica del titulo (Pre-streaming)
        # Pre-streaming: Crear título si no existe
        if not chat.title or chat.title == "Sin título":
            palabras = user_text.split()
            chat.title = " ".join(palabras[:10]) + ("..." if len(palabras) > 10 else "")
            db_session.add(chat)
            db_session.commit()
            # Invalidación del Sidebar (para orden y título nuevo)
            SidebarCache.invalidate_user(g.user_id)
            print(f"DEBUG: Cache invalidado PRE-STREAM para {chat.title}")
            
        # 8. Función Generadora para Streaming
        def generate():
            # Creamos una sesión dedicada para el streaming
            gen_session = SessionLocal()
            try:
                full_reply = ""
                for chunk in completion_stream(payload):  
                    full_reply += chunk
                    yield chunk

                # Guardar respuesta final
                inner_chat = gen_session.get(Chat, chat_id)
                inner_chat.updated_at = datetime.now(TIMEZONE)
                        
                new_msg = Message(chat_id=chat_id, role="assistant", content=full_reply)
                gen_session.add(new_msg)
                
                # Ejecutar resumen (debe aceptar la sesión para funcionar)
                summarize_and_trim(inner_chat, gen_session)
                gen_session.commit()
                
                # === REDIS ===
                # Cache mensajes en Redis
                ChatCache.append_message(chat_id, {
                    "id": new_msg.id,
                    "role": "assistant",
                    "content": full_reply,
                    "created_at": datetime.now(TIMEZONE).isoformat()
                })                

            except Exception as e:
                gen_session.rollback()
                logger.exception("Error durante el stream")
                yield "\n[ERROR] " + str(e)
            finally:
                gen_session.close()

        return Response(stream_with_context(generate()), content_type="text/plain")

    except Exception as e:
        db_session.rollback()
        logger.exception("Error en send_message")
        return jsonify({"error": str(e)}), 500
    finally:
        db_session.close()
# --------------- POST (extraer texto de archivos) ---------------
@chat_bp.route('/extract_file', methods=['POST'])
@clerk_required
def extract_file():
    # En el hilo principal no necesitamos db_session a menos que consultemos algo
    if 'file' not in request.files:
        return jsonify({'error': 'No se proporcionó ningún archivo'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Nombre de archivo vacío'}), 400
    # Nombre orginal para el frontend
    original_filename = file.filename
    
    original_name_base, ext = os.path.splitext(file.filename)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = secure_filename(f"{original_name_base}_{timestamp}{ext}")
    
    content_type = file.content_type
    file_bytes = file.read()
    final_text = "" # Variable unificada

    try:
        # 1. EXTRACCIÓN DE TEXTO (Lógica principal)
        if content_type.startswith("image/"):
            try:                
                final_text = analyze_image_with_azure(file_bytes)
                logger.info(f"Texto extraído de imagen {original_filename}")
                resp_text = f"🖼️ Imagen `{original_filename}`:\n\n{final_text}"
            except Exception as e:
                logger.error(f"Error en Azure Vision: {str(e)}")
                return jsonify({"error": f"Error en Azure Vision: {str(e)}"}), 500
        else:
            # Importante: usar BytesIO para archivos no-imagen porque ya hicimos file.read()
            from io import BytesIO
            file_stream = BytesIO(file_bytes)
            final_text = extract_text_from_file(file_stream, original_filename)
            resp_text = f"### Contenido del archivo `{original_filename}`\n\n{final_text}"

        # 2. TAREA EN SEGUNDO PLANO (OneDrive + DB)
        @copy_current_request_context
        def background_task(file_bytes, filename_bd, content_type, user_id, text_to_store, filename_ui):
            bg_session = SessionLocal()
            try:
                # EVENTO: Inicio
                event_queue.put({"type": "upload_started", "filename": filename_ui, "user_id": user_id})
                
                logger.info(f"🚀 Background upload: {filename_ui}")
                access_token = get_user_onedrive_token(user_id)
                
                if not access_token:
                    event_queue.put({"type": "upload_error", "filename": filename_ui, "error": "No hay token de OneDrive"})
                    return

                download_url = upload_to_onedrive(access_token, filename_bd, file_bytes)
                
                document = Document(
                    user_id=user_id,
                    filename=filename_bd,          # Ahora sí existe en el modelo
                    content=text_to_store,     # El texto que sacaste con OCR/PDF
                    mime_type=content_type,     # Coincide con el modelo
                    file_size=len(file_bytes),  # Ahora sí existe en el modelo
                    url=download_url,
                    source="onedrive",
                    tag="user_upload_mcp"
                )
                
                bg_session.add(document)
                bg_session.commit()

                # EVENTO: Éxito
                event_queue.put({
                    "type": "upload_completed", 
                    "filename": filename_ui, 
                    "url": download_url,
                    "user_id": user_id
                })
                
            except Exception as e:
                bg_session.rollback()
                logger.exception("Error en background task")
                # EVENTO: Error
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
        logger.exception("Error procesando archivo:")
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
