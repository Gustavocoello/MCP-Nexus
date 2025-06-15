from openai import chat
from src.services.ai_providers.utils import generate_prompt
from src.services.ai_providers.context import completion,completion_stream
from src.database.models.models import Chat, Message
from extensions import db
from flask import Blueprint, jsonify, Response, request, stream_with_context
from src.config.logging_config import get_logger
from datetime import datetime
import requests


logger = get_logger('routes')

## ----------- Mensajes de la IA sin memoria --------------
""" Create a blueprint for search API """
search_bp = Blueprint('search', __name__, url_prefix='/api/search')

@search_bp.route("/prompt", methods=["POST"])
def handle_search_prompt():
    try:
        data = request.json
        if not data or 'prompt' not in data:
            logger.error("No prompt received in request")
            return jsonify({"error": "Prompt is required"}), 400

        logger.debug(f"Search prompt received: {data['prompt']}")
        
        # Process prompt using utils functions
        result = generate_prompt({"description": data['prompt']})
        
        if result == "Todos los servicios de IA no estan disponibles actualmente.":
            return jsonify({"error": result}), 500
            
        return jsonify({"result": result})
    
    except Exception as e:
        error_msg = f"Error processing search prompt: {str(e)}"
        logger.error(error_msg)
        return jsonify({"error": error_msg}), 500


## -------------- Mensajes de la IA con memoria --------------
chat_bp = Blueprint('chat', __name__, url_prefix='/api/chat')

MAX_RAW   = 10
MAX_TOTAL = 40

# helpers (build_payload, summarize_and_trim) …
# --------------- Helpers ----------------
def build_payload(chat, recent, user_text):
    messages = []
    if chat.summary:
        messages.append({
            "role": "system",
            "content": f"Resumen de la conversación hasta ahora:\n{chat.summary}"
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

    # borrar mensajes resumidos
    ids = [m.id for m in to_summarize]
    Message.query.filter(Message.id.in_(ids)).delete(synchronize_session=False)
    db.session.commit()


# ------------- route principal -------------

# ----------------- GET ---------------------
@chat_bp.route('', methods=['GET'], strict_slashes=False)
def get_all_chats():
    chats = Chat.query.order_by(Chat.updated_at.desc()).all()
    return jsonify([{
        "id": chat.id,
        "created_at": chat.created_at.isoformat(),
        "updated_at": chat.updated_at.isoformat() if chat.updated_at else None,
        "summary": chat.summary,
        "title": chat.title if chat.title else "Sin título"
    } for chat in chats])

@chat_bp.route('/<chat_id>/messages', methods=['GET'])
def get_chat_messages(chat_id):
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
def delete_chat(chat_id):
    chat = Chat.query.get(chat_id)
    if not chat:
        return jsonify({"error": "Chat no encontrado"}), 404

    db.session.delete(chat)
    db.session.commit()
    return jsonify({"message": "Chat eliminado correctamente"}), 200


# ----------------- POST ---------------------    
    
@chat_bp.route('', methods=['POST'], strict_slashes=False)
def create_chat():
    try:
        chat = Chat()
        db.session.add(chat)
        db.session.commit()
        
        return jsonify({
            "id": chat.id,
            "created_at": chat.created_at.isoformat()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@chat_bp.route('/<chat_id>/message', methods=['POST'], strict_slashes=False)
def send_message(chat_id):
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
            .filter_by(chat_id=chat.id)
            .order_by(Message.created_at.desc())
            .limit(MAX_RAW)
            .all()[::-1]
        )

        payload = build_payload(chat, recent, user_text)

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

                summarize_and_trim(chat)  

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
        
# --------------- PUT ---------------
@chat_bp.route('/<chat_id>/title', methods=['PUT'])
def update_chat_title(chat_id):
    data = request.get_json()
    new_title = data.get('title')

    chat = Chat.query.get(chat_id)
    if not chat:
        return jsonify({'error': 'Chat no encontrado'}), 404

    chat.title = new_title
    db.session.commit()

    return jsonify({'message': 'Título actualizado', 'title': new_title})
