import asyncio
import json
from src.services.auth.mcp.mcp_jwt import generate_mcp_jwt
from src.database.models.models import Message, UserToken
from src.services.auth.utils.token_crypto import encrypt_token
from src.services.llm.prompts.system_prompt import SYSTEM_PROMPT
from src.config.time_helper import get_now
from src.config.logging_config import get_logger

logger = get_logger("chat_service")


# ---------------------------------------------------------------------------
# Payload builder
# ---------------------------------------------------------------------------

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