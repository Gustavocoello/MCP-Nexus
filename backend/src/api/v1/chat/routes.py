import json
import asyncio
import os
import threading
from httpx import get
from extensions import db
from datetime import datetime
from werkzeug.utils import secure_filename
from src.services.providers.utils import generate_prompt, extract_text_from_file, analyze_image_with_azure, can_upload_image
from src.services.core.llm_router import completion,completion_stream
from src.database.models.models import Chat, Message, MemoryType, UserMemory, Document, User
from src.services.integrations.extensions.onedrive_service import upload_to_onedrive, get_user_onedrive_token
from src.config.logging_config import get_logger
from src.services.memory.service import get_user_memory, save_memory
from src.services.memory.utils import build_memory_context, extract_memory_from_text, calculate_priority, classify_memory
from flask_login import login_required, current_user
from flask import Blueprint, jsonify, Response, request, stream_with_context, session, copy_current_request_context
from src.mcps.client.calendar.client_google_calendar import MCPToolsClient
from src.mcps.client.utils.utils import safe_serialize_call_result

logger = get_logger('routes')

mcp_client = MCPToolsClient()

## ----------- Mensajes de la IA sin memoria --------------
""" Create a blueprint for search API """
search_bp = Blueprint('search', __name__, url_prefix='/api/search')

@search_bp.route("/prompt", methods=["POST"])
def handle_search_prompt():
    # Si el usuario está logueado, lo redirigimos al endpoint de memoria
    if current_user.is_authenticated:
        return jsonify({
            "error": "Este endpoint es solo para usuarios no registrados.",
            "use": "/api/chat/<chat_id>/message"
        }), 403

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

def summarize_and_trim(chat):
    all_msgs = (Message.query
                .filter_by(chat_id=chat.id)
                .order_by(Message.created_at)
                .all())
    if len(all_msgs) <= MAX_TOTAL:
        return

    to_summarize = all_msgs[:-MAX_RAW]         # todo menos los 10 últimos
    summary_prompt = [
        {"role": "system",
         "content": "Resume brevemente la siguiente conversación:"},
        *[{"role": m.role, "content": m.content} for m in to_summarize]
    ]
    new_summary = completion(summary_prompt) # se cambio a completion
    logger.info(f"Nuevo resumen: {new_summary}")

    chat.summary = ((chat.summary or "") + "\n" + new_summary).strip()
    db.session.add(chat)
    # borrar mensajes resumidos
    ids = [m.id for m in to_summarize]
    Message.query.filter(Message.id.in_(ids)).delete(synchronize_session=False)
    db.session.commit()


# ------------- route principal -------------

# ----------------- GET ---------------------
@chat_bp.route('', methods=['GET'], strict_slashes=False)
@login_required
def get_all_chats():
    chats = Chat.query.filter_by(user_id=current_user.id).order_by(Chat.updated_at.desc()).all()
    return jsonify([{
        "id": chat.id,
        "created_at": chat.created_at.isoformat(),
        "updated_at": chat.updated_at.isoformat() if chat.updated_at else None,
        "summary": chat.summary,
        "title": chat.title if chat.title else "Sin título"
    } for chat in chats])

@chat_bp.route('/<chat_id>/messages', methods=['GET'])
@login_required
def get_chat_messages(chat_id):
    chat = Chat.query.get(chat_id)
    if not chat or chat.user_id != current_user.id:
        return jsonify({'error': 'Acceso denegado'}), 403
    messages = (Message.query
                .filter_by(chat_id=chat_id)
                .order_by(Message.created_at.asc())
                .all())
    return jsonify([{
        "id": msg.id,
        "role": msg.role,
        "content": msg.content,
        "created_at": msg.created_at.isoformat()
    } for msg in messages])
    
# ----------------- DELETE -------------------
    
@chat_bp.route('/<chat_id>', methods=['DELETE'])
@login_required
def delete_chat(chat_id):
    chat = Chat.query.get(chat_id)
    if not chat or chat.user_id != current_user.id:
        return jsonify({"error": "Acceso denegado"}), 403

    db.session.delete(chat)
    db.session.commit()
    return jsonify({"message": "Chat eliminado correctamente"}), 200


# ----------------- POST ---------------------    
    
@chat_bp.route('', methods=['POST'], strict_slashes=False)
@login_required
def create_chat():
    if not current_user.is_authenticated or not current_user.get_id():
        return jsonify({"error": "Usuario no autenticado o ID inválido"}), 401

    try:
        chat = Chat(user_id=current_user.get_id())
        db.session.add(chat)
        db.session.commit()
        
        print(f"[DEBUG] current_user: {current_user}, ID: {current_user.get_id()}")
        return jsonify({
            "id": chat.id,
            "created_at": chat.created_at.isoformat()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@chat_bp.route('/<chat_id>/message', methods=['POST'], strict_slashes=False)
@login_required
def send_message(chat_id):
    chat = Chat.query.get(chat_id)

    if not chat:
        # Si no existe, crearlo y asignarlo al usuario actual
        chat = Chat(id=chat_id, user_id=current_user.id)
        db.session.add(chat)
    elif chat.user_id != current_user.id:
        return jsonify({"error": "Acceso denegado"}), 403
    
    user_text = (request.json.get("text") or "").strip()
    if not user_text:
        return jsonify({"error": "Texto vacío"}), 400

    print("BODY RECIBIDO:", request.json)

    try:
        chat = Chat.query.get(chat_id)
        if chat is None:
            chat = Chat(id=chat_id)
            db.session.add(chat)

        chat.updated_at = datetime.utcnow()
        

        user_message = Message(chat_id=chat.id, role="user", content=user_text)
        db.session.add(user_message)

        if not chat.title:
            palabras = user_text.split()
            resumen = " ".join(palabras[:10]) + ("..." if len(palabras) > 10 else "")
            chat.title = resumen

        db.session.commit()  # 🔑

        recent = (
            Message.query
            .filter(Message.chat_id == chat.id, Message.role != "context")
            .order_by(Message.created_at.desc())
            .limit(MAX_RAW)
            .all()[::-1]
        )
        
        memories = get_user_memory(chat_id, memory_type=MemoryType.LONG_TERM)
        memory_context = build_memory_context(memories)
        
        hidden_context = request.json.get("hidden_context", "").strip()

        if hidden_context:
            Message.query.filter_by(chat_id=chat.id, role="context").delete()
            # Guardar como mensaje oculto (contexto), no será mostrado en frontend
            context_msg = Message(chat_id=chat.id, role="context", content=hidden_context)
            db.session.add(context_msg)
            
        # MCP - Model Context Protocol
        tool_name = request.json.get("tool", "").strip()
        params = request.json.get("params", {})
        mcp_client.user_id = current_user.id
        mcp_context = None
        if tool_name:
            try:
                #Creamos un nuevo loop
                loop = asyncio.new_event_loop() # Creamos un nuevo event loop
                try:
                    result = loop.run_until_complete(mcp_client._call_tool(tool_name, **params))
                finally:
                    loop.close()  # Cerramos el event loop
                    print(f"MCP Results: ({tool_name}):", result)
                
                # Convertir a JSON serializable manualmente
                result_dict = safe_serialize_call_result(result)
                # construir mcp_context como JSON plano
                mcp_context = json.dumps({
                    "response": result_dict,
                    "tool_used": tool_name
                })

                # guardar en DB como oculto (no se renderiza en frontend)
                mcp_msg = Message(
                    chat_id=chat.id,
                    role="mcp-tool",
                    content=mcp_context
                )
                db.session.add(mcp_msg)

            except Exception as e:
                print("Error MCP:", e)


        payload = build_payload(chat, recent, user_text, memory_context=memory_context, hidden_context=hidden_context, mcp_context=mcp_context)
        print("🔍 PAYLOAD ANTES DEL MODELO:", payload)


        # Usar stream para respuesta parcial
        def generate():
            try:
                full_reply = ""
                                       
                # Llama a tu modelo pero ahora espera que `completion()` sea un generador
                for chunk in completion_stream(payload):  
                    full_reply += chunk
                    yield chunk  # Streaming real al cliente

                # Guardar respuesta completa al final
                chat.updated_at = datetime.utcnow()
                db.session.add(Message(chat_id=chat.id, role="assistant", content=full_reply))
                db.session.commit()
                
                # EXTRAER Y GUARDAR MEMORIAS DESDE EL TEXTO DEL 
                extracted_memories = extract_memory_from_text(user_text)
                print("[DEBUG] Memorias extraídas:", extracted_memories)

                notificaciones = []
                
                for mem_text in extracted_memories:
                    priority = calculate_priority(mem_text)
                    classification = classify_memory(mem_text)  # Ej: "hecho", "preferencia", etc.
                    key = f"{classification}:{mem_text[:30]}"  # clave compuesta
                    save_memory(chat.id, key, mem_text, memory_type=MemoryType.LONG_TERM, priority=priority)
                    
                    # Notificacion para enviar al frontend
                    if priority >= 6:
                        notificaciones.append({
                            "type": "memory_saved",
                            "message": f"He recordado algo importante: \"{mem_text}\""
                        })      

                summarize_and_trim(chat)  
                                
                if notificaciones:
                    for nota in notificaciones:
                        logger.info(f"Enviando notificación: [NOTIFICATION] {nota['message']}")
                        yield "\n\n[NOTIFICATION] 💾 Memoria actualizada\n"

            except Exception as e:
                db.session.rollback()
                logger.exception("Error durante el stream")
                yield "\n[ERROR] " + str(e)  # ⬅️ devolvé algo al cliente
            finally:
                db.session.close()

        return Response(stream_with_context(generate()), content_type="text/plain")  # 🔄 cambiamos jsonify

    except Exception as e:
        db.session.rollback()
        logger.exception("Error en send_message")
        return jsonify({"error": str(e)}), 500
    finally:
        db.session.close()

# --------------- POST (extraer texto de archivos) ---------------
@chat_bp.route('/extract_file', methods=['POST'])
@login_required
def extract_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No se proporcionó ningún archivo'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Nombre de archivo vacío'}), 400

    original_name, ext = os.path.splitext(file.filename)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = secure_filename(f"{original_name}_{timestamp}{ext}")
    content_type = file.content_type
    file_bytes = file.read()

    try:
        if content_type.startswith("image/"):
            try:                
                extracted_text = analyze_image_with_azure(file_bytes)
                logger.info(f"Texto extraído de la imagen {filename} (longitud: {len(extracted_text)} caracteres)")
                resp = jsonify({"text": f"🖼️ Imagen `{filename}`:\n\n{extracted_text}"})
            except Exception as e:
                logger.error(f"Error al analizar imagen con Azure Vision: {str(e)}")
                return jsonify({"error": f"Error en Azure Vision: {str(e)}"}), 500
        else:
            file_stream = file.stream
            text = extract_text_from_file(file_stream, filename)
            full_text = f"### Contenido del archivo `{filename}`\n\n{text}"
            resp = jsonify({'text': full_text})

        # --- background upload ---
        @copy_current_request_context
        def background_task(file_bytes=file_bytes, filename=filename, content_type=content_type, user_id=current_user.id):
            try:
                """
                # Traer el usuario completo
                user = User.query.get(user_id)
                if not user or not can_upload_image(user.name):
                    logger.warning(f"Usuario {user.name if user else 'desconocido'} no permitido para subir imágenes")
                    return
                """

                logger.info("🚀 Iniciando background_task...")  # log de prueba
                access_token = get_user_onedrive_token(user_id)  # <- usar token delegado
                if not access_token:
                    logger.error("No hay token de OneDrive en sesión")
                    return
                download_url = upload_to_onedrive(access_token, filename, file_bytes)
                document = Document(
                    mime_type=content_type,
                    size_bytes=len(file_bytes),
                    url=download_url,
                    source="onedrive",
                    tag="user_upload_mcp",
                    user_id=user_id,
                )
                db.session.add(document)
                db.session.commit()
                logger.info(f"Archivo {filename} guardado en OneDrive y DB")
            except Exception as e:
                logger.exception(f"Error en background upload OneDrive: {e}")

        threading.Thread(target=background_task, daemon=True).start()
        return resp

    except Exception as e:
        logger.exception("Error procesando archivo:")
        return jsonify({'error': str(e)}), 500

# --------------- PUT ---------------
@chat_bp.route('/<chat_id>/title', methods=['PUT'])
@login_required
def update_chat_title(chat_id):
    chat = Chat.query.get(chat_id)
    if not chat or chat.user_id != current_user.id:
        return jsonify({'error': 'Acceso denegado'}), 403
    
    data = request.get_json()
    new_title = data.get('title')

    chat.title = new_title
    db.session.commit()

    return jsonify({'message': 'Título actualizado', 'title': new_title})
