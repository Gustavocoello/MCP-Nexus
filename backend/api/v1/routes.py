from src.services.ai_providers.utils import generate_prompt
from src.services.ai_providers.context import completion
from database.models.models import Chat, Message
from extensions import db
from flask import Blueprint, jsonify, request
from config.logging_config import get_logger
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
@chat_bp.post('/')
def create_chat():
    chat = Chat(id=request.json.get("id") or datetime.utcnow().isoformat())
    db.session.add(chat)
    db.session.commit()
    return jsonify({"chat_id": chat.id}), 201


@chat_bp.post('/<chat_id>/message')
def send_message(chat_id):
    user_text = request.json["text"]

    chat = Chat.query.get(chat_id) or Chat(id=chat_id)
    db.session.add(chat)
    db.session.add(Message(chat_id=chat.id, role="user", content=user_text))

    recent = (Message.query.filter_by(chat_id=chat.id)
              .order_by(Message.created_at.desc())
              .limit(MAX_RAW).all()[::-1])

    payload = build_payload(chat, recent, user_text)

    # <<< UNA sola línea llama al router >>>
    assistant_reply = completion(payload)

    db.session.add(Message(chat_id=chat.id, role="assistant",
                           content=assistant_reply))
    db.session.commit()

    summarize_and_trim(chat)
    return jsonify({"reply": assistant_reply})