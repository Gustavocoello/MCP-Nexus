import asyncio
import json
# CHAT V1
from sqlalchemy import select, delete
from src.services.auth.mcp.mcp_jwt import generate_mcp_jwt
from src.database.models.models import Message, UserToken
from src.services.auth.utils.token_crypto import encrypt_token
from src.services.llm.prompts.system_prompt import SYSTEM_PROMPT
from src.services.llm.chat.llm_router import completion
from src.core.time_helper import get_now
from src.core.logging import get_logger

# CHAT V2
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

logger = get_logger("chat_service")

# ==================== VERSION #1 - BASIC HISTORY CONVERSION ====================
def build_payload(chat, recent, user_text, memory_context=None, hidden_context=None, mcp_context=None):
    messages = []

    # Base system prompt — always first
    messages.append({"role": "system", "content": SYSTEM_PROMPT})

    # Long-term memory context (Mem0 or similar)
    if memory_context:
        messages.append({
            "role": "system",
            "content": f"Relevant information about the user:\n{memory_context}"
        })

    # Image / file context from Azure Vision or OCR
    if hidden_context:
        messages.append({
            "role": "system",
            "content": (
                "The following is content extracted from an image or uploaded file "
                "(via OCR or vision analysis). Treat it as real factual input. "
                "Answer the user's question using this information. "
                "Never say you cannot see images."
            )
        })
        messages.append({"role": "system", "content": hidden_context})

    # MCP tool result
    if mcp_context:
        messages.append({
            "role": "system",
            "content": (
                "The following is structured data returned by an external tool. "
                "Use it to answer the user accurately. Do not reference the tool."
            )
        })
        messages.append({"role": "system", "content": mcp_context})

    # Conversation summary (memory trim)
    if chat.summary:
        messages.append({
            "role": "system",
            "content": f"Summary of previous conversation:\n{chat.summary}"
        })

    # Recent raw messages
    for m in recent:
        messages.append({"role": m.role, "content": m.content})

    # Current user message
    messages.append({"role": "user", "content": user_text})

    return messages


# ---------------------------------------------------------------------------
# MCP tool execution
# ---------------------------------------------------------------------------

def execute_mcp_tool(tool_name, params, user_id, db_session, chat_id, mcp_manager):
    """
    Runs an MCP tool, handles token refresh, persists result.
    Returns mcp_context string or None on failure.
    """
    try:
        mcp_auth_token = generate_mcp_jwt(user_id, "google_calendar")

        if not mcp_auth_token:
            logger.warning(f"Could not generate JWT for user_id={user_id}")
            return None

        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                mcp_manager.call_tool_with_auth(
                    tool_name=tool_name,
                    user_id=user_id,
                    auth_token=mcp_auth_token,
                    **params
                )
            )
        finally:
            loop.close()

        logger.info(f"MCP result for tool '{tool_name}': {result}")

        # Handle token refresh
        response_context = getattr(result, "context", {})
        if "google_new_access_token" in response_context:
            _persist_refreshed_token(
                user_id=user_id,
                new_access=response_context["google_new_access_token"],
                new_refresh=response_context.get("google_new_refresh_token"),
                db_session=db_session
            )

        result_dict = safe_serialize_call_result(result)
        mcp_context = json.dumps({
            "response": result_dict,
            "tool_used": tool_name,
            "token_refreshed": "google_new_access_token" in response_context
        })

        mcp_msg = Message(chat_id=chat_id, role="mcp-tool", content=mcp_context)
        db_session.add(mcp_msg)
        db_session.commit()

        return mcp_context

    except Exception as e:
        logger.exception(f"MCP tool execution failed for tool '{tool_name}'")
        return None
    
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
    
# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _persist_refreshed_token(user_id, new_access, new_refresh, db_session):
    token_entry = db_session.query(UserToken).filter(
        UserToken.user_id == user_id,
        UserToken.provider == "google_calendar"
    ).first()

    if token_entry:
        token_entry.access_token = encrypt_token(new_access)
        if new_refresh:
            token_entry.refresh_token = encrypt_token(new_refresh)
        db_session.add(token_entry)
        logger.info("Google token refreshed and persisted.")
    else:
        new_token = UserToken(
            user_id=user_id,
            provider="google_calendar",
            access_token=encrypt_token(new_access),
            refresh_token=encrypt_token(new_refresh) if new_refresh else None
        )
        db_session.add(new_token)
        logger.info("Google token created and persisted.")

    db_session.commit()


def safe_serialize_call_result(result):
    """Safely converts MCP result to a serializable dict."""
    try:
        if hasattr(result, "__dict__"):
            return {k: v for k, v in result.__dict__.items() if not k.startswith("_")}
        return str(result)
    except Exception:
        return str(result)
    
    
# ==================== VERSION #2 - LANGCHAIN MESSAGES NEW ====================

def get_langchain_history(chat, recent, memory_context=None, hidden_context=None):
    """
    Convierte tu historial de BD a objetos de LangChain.
    """
    messages = []
    
    # 1. Additional contexts (RAG, Long-term memory, Vision/Files)
    if memory_context:
        messages.append(SystemMessage(content=f"Relevant long-term memory about the user:\n{memory_context}"))
        
    if hidden_context:
        messages.append(SystemMessage(content=(
            "The following is content extracted from an image or uploaded file "
            "(via OCR or vision analysis). Treat it as real factual input. "
            "Answer the user's question using this information. "
            "Never say you cannot see images.\n\n"
            f"Extracted Content:\n{hidden_context}"
        )))
        
    if getattr(chat, "summary", None): # Mantenemos por si hay chats viejos en la BD
        messages.append(SystemMessage(content=f"Summary of previous conversation:\n{chat.summary}"))

    # 2. Recent Messages
    for m in recent:
        if m.role == "user":
            messages.append(HumanMessage(content=m.content))
        elif m.role == "assistant":
            messages.append(AIMessage(content=m.content))
        elif m.role == "mcp-tool":
            # Skip sending audit logs to the LLM. 
            # LangChain handles tool context dynamically in memory.
            continue

    return messages