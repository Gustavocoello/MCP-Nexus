from sqlalchemy import select, delete
from src.config.time_helper import get_now
from src.database.models.models import Message
from src.services.llm.llm_router import completion
from src.config.logging_config import get_logger

logger = get_logger("memory_service")

MAX_RAW   = 10
MAX_TOTAL = 40


def summarize_and_trim(chat, db_session):
    stmt = select(Message).filter_by(chat_id=chat.id).order_by(Message.created_at.asc())
    all_msgs = db_session.execute(stmt).scalars().all()

    if len(all_msgs) <= MAX_TOTAL:
        return

    to_summarize = all_msgs[:-MAX_RAW]

    summary_prompt = [
        {"role": "system", "content": "Summarize the following conversation briefly and accurately. Preserve key facts, names, decisions, and context."},
        *[{"role": m.role, "content": m.content} for m in to_summarize]
    ]

    new_summary = completion(summary_prompt)
    logger.info(f"New summary generated for chat {chat.id}")

    chat.summary = ((chat.summary or "") + "\n" + new_summary).strip()

    if hasattr(chat, "updated_at"):
        chat.updated_at = get_now()

    db_session.add(chat)

    ids_to_delete = [m.id for m in to_summarize]
    delete_stmt = delete(Message).where(Message.id.in_(ids_to_delete))
    db_session.execute(delete_stmt)
    db_session.commit()

    logger.info(f"Summarized and deleted {len(ids_to_delete)} messages from chat {chat.id}")
