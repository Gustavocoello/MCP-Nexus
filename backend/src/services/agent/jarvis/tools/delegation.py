# src/services/agent/jarvis/tools/delegation.py
from langchain_core.tools import Tool
from sqlalchemy.orm import Session
from src.core.logging import get_logger

from src.services.agent.nexus.agent import get_nexus
from src.services.agent.ragel.agent import get_ragel
from src.services.agent.Koda.agent import get_koda
from src.services.agent.lamar.agent import get_lamar

# Importa tu modelo User y tu generador de sesión de base de datos
from src.database.models.models import User  # Ajusta esta ruta a donde esté tu modelo User
from src.database.settings.connection import get_db

logger = get_logger("jarvis_tools")

HALLUCINATION_SIGNALS = [
    "content from GitHub",
    "SKILL.md content",
    "placeholder",
    "example content",
]

def build_delegation_tools(user_id: str) -> list:

    # Productivity
    def ask_nexus(task_description: str) -> str:
        logger.info(f"[JARVIS → NEXUS] user={user_id} | task={task_description[:80]}")
        try:
            agent = get_nexus(user_id=user_id)
            result = agent.run_task(instruction=task_description, user_id=user_id)
            output = result.get('output', 'Success but no output.')

            if any(s.lower() in output.lower() for s in HALLUCINATION_SIGNALS):
                return (
                    "CRITICAL ERROR IN NEXUS: Possible hallucination detected — "
                    "Nexus returned placeholder/invented content instead of real data. "
                    "The GitHub MCP server may be offline. DO NOT USE this output. "
                    "STOP and inform the user immediately."
                )

            if result.get("status") == "failed" or "CRITICAL" in output or "CRÍTICO" in output:
                return (
                    f"CRITICAL ERROR IN NEXUS: {output}\n\n"
                    "STOP IMMEDIATELY. DO NOT USE ANY OTHER TOOL. "
                    "Report this exact error to the user and wait for their response."
                )
            return f"Nexus Report (STOP — report to user and wait for input):\n{output}"
        except Exception as e:
            logger.error(f"[JARVIS → NEXUS] Error: {e}")
            return f"CRITICAL FAILURE: Nexus error: {str(e)}. DO NOT RETRY. INFORM THE USER."

    # Investigator 
    def ask_ragel(query: str) -> str:
        logger.info(f"[JARVIS → RAGEL] user={user_id} | query={query[:80]}")
        try:
            agent = get_ragel(user_id=user_id)
            result = agent.run_task(instruction=query, user_id=user_id)
            return f"Ragel Execution Report:\n{result.get('output', 'Success but no output.')}"
        except Exception as e:
            logger.error(f"[JARVIS → RAGEL] Error: {e}")
            return f"CRITICAL FAILURE: Ragel error: {str(e)}. Inform the user."

    # Software Engineer
    def ask_koda(coding_task: str) -> str:
        logger.info(f"[JARVIS → KODA] user={user_id} | task={coding_task[:80]}")
        try:
            agent = get_koda(user_id=user_id)
            result = agent.run_task(instruction=coding_task, user_id=user_id)
            return f"Koda Execution Report:\n{result.get('output', 'Success but no output.')}"
        except Exception as e:
            logger.error(f"[JARVIS → KODA] Error: {e}")
            return f"CRITICAL FAILURE: Koda error: {str(e)}. Inform the user."
        
    # Agent DevOps
    def ask_lamar(devops_task: str) -> str:
        logger.info(f"[JARVIS → LAMAR] user={user_id} | task={devops_task[:80]}")
        try:
            agent = get_lamar(user_id=user_id)
            result = agent.run_task(instruction=devops_task, user_id=user_id)
        
            if isinstance(result, dict):
                metadata = result.get("metadata", {})
                tokens = metadata.get("tokens", "No token info")
                output = result.get("output", "Success but no output.")
            else:
                output = str(result)
                tokens = "No token info (Result was not a dict)"

            logger.info(f"[LAMAR TOKENS] {tokens}")
            
            # Lo importante: Jarvis DEBE leer esto.
            return f"Lamar (DevOps) Execution Report:\n{output}"
            
        except Exception as e:
            logger.error(f"[JARVIS → LAMAR] Error: {str(e)}")
            return f"CRITICAL FAILURE: Lamar error: {str(e)}. Inform the admin immediately."


    tools = [
        Tool.from_function(
            func=ask_nexus,
            name="ask_nexus",
            description=(
                "Use for: Google Calendar, Notion, file system READ operations, "
                "and skill downloads from GitHub. "
                "EXCEPTION — skill download: multi-step task allowed as ONE bounded operation. "
                "ALL OTHER TASKS: ONE instruction only. Report result. STOP. "
                "NEVER follow up automatically. Wait for user input after each result. "
                "CRITICAL: Web automation/scraping is DEPRECATED. Do not use Nexus for web tasks."
            )
        ),
        Tool.from_function(
            func=ask_ragel,
            name="ask_ragel",
            description=(
                "Use ONLY for: live internet research, real-time news, uploaded documents "
                "(PDFs, Excel, CSVs), personal vector database queries. "
                "Do NOT use after Nexus/Webwright already extracted web data. "
                "Do NOT use for calendar, notion, files, or coding tasks."
            )
        ),
        Tool.from_function(
            func=ask_koda,
            name="ask_koda",
            description=(
                "Use for: writing/debugging code, patching files, GitHub write operations "
                "(branch, commit, PR), sandbox terminal commands. "
                "Do NOT use for skill downloads, file exploration, or research. "
                "Do NOT delegate failed run_bash commands here to fix or retry."
            )
        ),
    ]
    try:
        db: Session = next(get_db()) # Obtener sesión
        user = db.query(User).filter(User.id == user_id).first()
        
        if user and user.is_admin:
            logger.info(f"[SECURITY] User {user_id} is Admin. Lamar DevOps tool enabled.")
            tools.append(
                Tool.from_function(
                    func=ask_lamar,
                    name="ask_lamar",
                    description=(
                        "RESTRICTED ADMIN TOOL. Use ONLY for DevOps tasks, server management, "
                        "cloud infrastructure, database migrations, and token/cost analysis. "
                        "Do NOT use for general coding (use Koda) or research (use Ragel). "
                        "CRITICAL RULE: The user CANNOT see the output of this tool. "
                        "Once you receive Lamar's DevOps Execution Report, you MUST read it, "
                        "synthesize the data, and present the final answer clearly to the user "
                        "in your next response."
                    )
                )
            )
    except Exception as e:
        logger.error(f"[SECURITY] Failed to verify admin status for {user_id}: {str(e)}")
        # Si falla la DB por seguridad NO agregamos la herramienta.

    return tools
