# src/services/agent/jarvis/tools.py
from langchain_core.tools import Tool
from src.core.logging import get_logger

from src.services.agent.nexus.agent import get_nexus
from src.services.agent.ragel.agent import get_ragel
from src.services.agent.Koda.agent import get_koda
from src.services.agent.jarvis.tools.run_skills import run_bash, list_skills, read_skill

logger = get_logger("jarvis_tools")


def build_jarvis_tools(user_id: str) -> list:
    """
    Builds the delegation tools for Jarvis.
    Each tool routes ONLY to the correct sub-agent for the given user_id.
    """

    # ── Sub-agent delegation ──────────────────────────────────────────────────

    def ask_nexus(task_description: str) -> str:
        logger.info(f"[JARVIS → NEXUS] user={user_id} | task={task_description[:80]}")
        try:
            agent = get_nexus(user_id=user_id)
            result = agent.run_task(instruction=task_description, user_id=user_id)
            output = result.get('output', 'Success but no output.')
            
            # Detectar señales de alucinación o fallo silencioso
            hallucination_signals = [
                "content from GitHub",
                "SKILL.md content",
                "placeholder",
                "example content",
            ]
            if any(signal.lower() in output.lower() for signal in hallucination_signals):
                return (
                    "CRITICAL ERROR IN NEXUS: Possible hallucination detected — "
                    "Nexus returned placeholder/invented content instead of real data. "
                    "The GitHub MCP server may be offline. DO NOT USE this output. "
                    "STOP and inform the user immediately."
                )
            
            if result.get("status") == "failed" or "Recursion limit" in output or "CRITICAL FAILURE" in output:
                return f"CRITICAL ERROR IN NEXUS: {output}. DO NOT RETRY. INFORM THE USER IMMEDIATELY."

            return f"Nexus Report (STOP — report this to user and wait for their input):\n{output}"
        except Exception as e:
            logger.error(f"[JARVIS → NEXUS] Error: {e}")
            return f"CRITICAL FAILURE: Nexus encountered an error: {str(e)}. DO NOT RETRY. INFORM THE USER."

    def ask_ragel(query: str) -> str:
        logger.info(f"[JARVIS → RAGEL] user={user_id} | query={query[:80]}")
        try:
            agent = get_ragel(user_id=user_id)
            result = agent.run_task(instruction=query, user_id=user_id)
            return f"Ragel Execution Report:\n{result.get('output', 'Success but no output.')}"
        except Exception as e:
            logger.error(f"[JARVIS → RAGEL] Error: {e}")
            return f"CRITICAL FAILURE: Ragel encountered an error: {str(e)}. Inform the user."

    def ask_koda(coding_task: str) -> str:
        logger.info(f"[JARVIS → KODA] user={user_id} | task={coding_task[:80]}")
        try:
            agent = get_koda(user_id=user_id)
            result = agent.run_task(instruction=coding_task, user_id=user_id)
            return f"Koda Execution Report:\n{result.get('output', 'Success but no output.')}"
        except Exception as e:
            logger.error(f"[JARVIS → KODA] Error: {e}")
            return f"CRITICAL FAILURE: Koda encountered an error: {str(e)}. Inform the user."

    # ── Skills (descubrimiento + ejecución sandboxed) ───────────────────────────

    def _list_skills(_: str = "") -> str:
        logger.info(f"[JARVIS → SKILLS] user={user_id} | list_skills")
        return list_skills()

    def _read_skill(skill_name: str) -> str:
        logger.info(f"[JARVIS → SKILLS] user={user_id} | read_skill={skill_name}")
        return read_skill(skill_name.strip())

    def _run_bash(command: str) -> str:
        logger.info(f"[JARVIS → SKILLS] user={user_id} | run_bash={command[:80]}")
        return run_bash(command.strip())

    # ── Tool list ─────────────────────────────────────────────────────────────

    return [
        Tool.from_function(
            func=ask_nexus,
            name="ask_nexus",
            description=(
                "Use for: Google Calendar (events, meetings), Notion (pages, tasks, databases), "
                "file system READ operations (list, find, explore files). "
                "EXCEPTION — skill download: when downloading a skill from GitHub, this is a "
                "multi-step task (read each file from GitHub + write to skills/) that completes "
                "as ONE bounded operation. Nexus will report all files created when done. "
                "FILE RULE (all other tasks): Send ONE specific instruction. Report result. STOP. "
                "NEVER send follow-up file calls automatically — wait for user input after each result. "
                "NEVER explore subfolders or read files unless explicitly asked. "
                "Input: a single, specific natural-language instruction."
            )
        ),
        Tool.from_function(
            func=ask_ragel,
            name="ask_ragel",
            description=(
                "Use ONLY for: live internet research, real-time news, uploaded documents "
                "(PDFs, Excel, CSVs), personal vector database queries. "
                "Do NOT use for calendar, notion, file system, or coding tasks. "
                "Input: a precise search query or document retrieval instruction."
            )
        ),
        Tool.from_function(
            func=ask_koda,
            name="ask_koda",
            description=(
                "Use for: writing NEW code, debugging existing code, patching files, "
                "GitHub operations (create branch, commit, PR), running terminal commands "
                "in the Sandbox, executing scripts. "
                "Do NOT use for: skill downloads (that's ask_nexus), file exploration "
                "(that's ask_nexus), research (that's ask_ragel). "
                "Do NOT delegate failed run_bash commands to Koda to 'fix' or 'retry'. "
                "Input: a clear programming or execution prompt with full context."
            )
        ),
        Tool.from_function(
            func=_list_skills,
            name="list_skills",
            description=(
                """"
                Returns a lightweight index (name, description, scope) of all available skills.
                Use when the user asks "what skills do you have", "what can you do", or similar.
                AFTER calling list_skills for an informational question: respond directly to the
                user with the list. DO NOT call read_skill or run_bash unless the user explicitly
                asks to USE or RUN a specific skill.
                """
            )
        ),
        Tool.from_function(
            func=_read_skill,
            name="read_skill",
            description=(
                """
                Reads the full SKILL.md of one skill. Only call this when the user explicitly
                asks to run, execute, or use a specific skill (e.g. "run skill-sync", "execute
                the sync in dry-run mode").
                """
                
            )
        ),
        Tool.from_function(
            func=_run_bash,
            name="run_bash",
            description=(
                """
                Executes a command from the skill's "## Commands" section.
                Restricted to ./skills/* paths. Only call AFTER read_skill, and ONLY if the
                user asked to RUN something — not just to learn about it.
                """
            )
        ),
    ]