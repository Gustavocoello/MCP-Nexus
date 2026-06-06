# src/services/agent/jarvis/tools.py
from langchain_core.tools import Tool
from src.core.logging import get_logger

from src.services.agent.nexus.agent import get_nexus
from src.services.agent.ragel.agent import get_ragel
from src.services.agent.Koda.agent import get_koda

logger = get_logger("jarvis_tools")


def build_jarvis_tools(user_id: str) -> list:
    """
    Builds the delegation tools for Jarvis.
    Each tool routes ONLY to the correct sub-agent for the given user_id.
    """

    # ── Sub-agent delegation ──────────────────────────────────────────────────

    def ask_nexus(task_description: str) -> str:
        """Delegates to Nexus: Google Calendar and Notion."""
        logger.info(f"[JARVIS → NEXUS] user={user_id} | task={task_description[:80]}")
        try:
            agent = get_nexus(user_id=user_id)
            result = agent.run_task(instruction=task_description, user_id=user_id)
            return f"Nexus Execution Report:\n{result.get('output', 'Success but no output.')}"
        except Exception as e:
            logger.error(f"[JARVIS → NEXUS] Error: {e}")
            return f"CRITICAL FAILURE: Nexus encountered an error: {str(e)}. Inform the user."

    def ask_ragel(query: str) -> str:
        """Delegates to Ragel: web research and document RAG."""
        logger.info(f"[JARVIS → RAGEL] user={user_id} | query={query[:80]}")
        try:
            agent = get_ragel(user_id=user_id)
            result = agent.run_task(instruction=query, user_id=user_id)
            return f"Ragel Execution Report:\n{result.get('output', 'Success but no output.')}"
        except Exception as e:
            logger.error(f"[JARVIS → RAGEL] Error: {e}")
            return f"CRITICAL FAILURE: Ragel encountered an error: {str(e)}. Inform the user."

    def ask_koda(coding_task: str) -> str:
        """Delegates to Koda: code writing, debugging, and terminal commands."""
        logger.info(f"[JARVIS → KODA] user={user_id} | task={coding_task[:80]}")
        try:
            agent = get_koda(user_id=user_id)
            result = agent.run_task(instruction=coding_task, user_id=user_id)
            return f"Koda Execution Report:\n{result.get('output', 'Success but no output.')}"
        except Exception as e:
            logger.error(f"[JARVIS → KODA] Error: {e}")
            return f"CRITICAL FAILURE: Koda encountered an error: {str(e)}. Inform the user."

    # ── Tool list ─────────────────────────────────────────────────────────────

    return [
        Tool.from_function(
            func=ask_nexus,
            name="ask_nexus",
            description=(
                "Use ONLY for personal productivity: Google Calendar (events, meetings, "
                "availability, scheduling) and Notion (pages, databases, tasks, notes). "
                "Input MUST be a detailed instruction of what to read, create, or update."
            )
        ),
        Tool.from_function(
            func=ask_ragel,
            name="ask_ragel",
            description=(
                "Use ONLY for live internet research or when the user asks about uploaded "
                "documents, files, PDFs, Excel sheets, or personal vector databases. "
                "Input MUST be a precise search query or retrieval instruction."
            )
        ),
        Tool.from_function(
            func=ask_koda,
            name="ask_koda",
            description=(
                "Use ONLY for software engineering: writing code, debugging, executing "
                "terminal commands, running maintenance scripts (Skills), or file system operations. "
                "Input MUST be a clear programming or terminal execution prompt with full context."
            )
        )
    ]