# src/services/agent/jarvis/tools/delegation.py
from langchain_core.tools import StructuredTool
from langgraph.types import interrupt
from pydantic import BaseModel, Field
from typing import Optional
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

# ==========================================
# INPUT SCHEMAS FOR SUB-AGENTS
# ==========================================

class NexusTaskInput(BaseModel):
    task_description: str = Field(description="The specific productivity task for Nexus (Calendar, Notion, etc.).")
    relevant_context: str = Field(
        default="",
        description=(
            "ALL the relevant context that Nexus needs and that you (Jarvis) already have: "
            "what the user originally asked for, dates, names, or previous steps. "
            "If you omit this, Nexus will work blind."
        )
    )

class RagelTaskInput(BaseModel):
    query: str = Field(description="The specific research query or question for Ragel.")
    relevant_context: str = Field(
        default="",
        description=(
            "ALL the relevant context that Ragel needs and that you (Jarvis) already have: "
            "what the user originally asked for, previous findings, or specific constraints. "
            "If you omit this, Ragel will work blind."
        )
    )

class KodaTaskInput(BaseModel):
    coding_task: str = Field(description="The specific and actionable coding task for Koda.")
    relevant_context: str = Field(
        default="",
        description=(
            "ALL the relevant context that Koda needs and that you (Jarvis) already have: "
            "what the user originally asked for, decisions made, involved files, "
            "specs or agreed design. If you omit this, Koda will work blind."
        )
    )

class LamarTaskInput(BaseModel):
    devops_task: str = Field(description="The specific DevOps or admin task for Lamar.")
    relevant_context: str = Field(
        default="",
        description=(
            "ALL the relevant context that Lamar needs and that you (Jarvis) already have: "
            "what the user originally asked for, server state, or previous errors. "
            "If you omit this, Lamar will work blind."
        )
    )

# ==========================================
# DELEGATION TOOLS BUILDER
# ==========================================

def build_delegation_tools(user_id: str, client_type: str = "web") -> list:

    # Productivity (Nexus)
    def ask_nexus(task_description: str, relevant_context: str = "") -> str:
        logger.info(f"[JARVIS → NEXUS] user={user_id} | task={task_description[:80]}")
        try:
            full_instruction = (
                f"{task_description}\n\nPREVIOUS CONTEXT:\n{relevant_context}" 
                if relevant_context else task_description
            )
            agent = get_nexus(user_id=user_id)
            result = agent.run_task(instruction=full_instruction, user_id=user_id)
            output = result.get('output', 'Success but no output.')

            if any(s.lower() in output.lower() for s in HALLUCINATION_SIGNALS):
                return (
                    "CRITICAL ERROR IN NEXUS: Possible hallucination detected — "
                    "Nexus returned placeholder/invented content instead of real data. "
                    "The GitHub MCP server may be offline. DO NOT USE this output. "
                    "STOP and inform the user immediately."
                )

            # Kept "CRÍTICO" just in case the agent itself replies in Spanish
            if result.get("status") == "failed" or "CRITICAL" in output or "CRÍTICO" in output:
                return (
                    f"CRITICAL ERROR IN NEXUS: \n{output}\n\n"
                    "STOP IMMEDIATELY. DO NOT USE ANY OTHER TOOL. "
                    "Report this exact error to the user and wait for their response."
                )
            return f"Nexus Report (STOP — report to user and wait for input):\n{output}"
        except Exception as e:
            logger.error(f"[JARVIS → NEXUS] Error: {str(e)}")
            return f"CRITICAL FAILURE: Nexus error: {str(e)}. DO NOT RETRY. INFORM THE USER."

    # Investigator (Ragel)
    def ask_ragel(query: str, relevant_context: str = "") -> str:
        logger.info(f"[JARVIS → RAGEL] user={user_id} | query={query[:80]}")
        try:
            full_instruction = (
                f"{query}\n\nPREVIOUS CONTEXT:\n{relevant_context}" 
                if relevant_context else query
            )
            agent = get_ragel(user_id=user_id)
            result = agent.run_task(instruction=full_instruction, user_id=user_id)
            output = result.get('output', 'Success but no output.')
            return f"Ragel Execution Report:\n{output}"
        except Exception as e:
            logger.error(f"[JARVIS → RAGEL] Error: {str(e)}")
            return f"CRITICAL FAILURE: Ragel error: {str(e)}. Inform the user."

    # Software Engineer (Koda)
    def ask_koda(coding_task: str, relevant_context: str = "") -> str:
        logger.info(f"[JARVIS → KODA] user={user_id} | task={coding_task[:80]}")
        try:
            full_instruction = (
                f"{coding_task}\n\nPREVIOUS CONTEXT:\n{relevant_context}" 
                if relevant_context else coding_task
            )
            agent = get_koda(user_id=user_id, client_type=client_type)
            result = agent.run_task(instruction=full_instruction, user_id=user_id)
            
            # 1. ¡Extraer el output PRIMERO! (Antes intentabas leer 'output' antes de definirlo)
            output = result.get('output', 'Success but no output.')
            
            # 2. Si Koda fue interceptado por el HITL, congelamos a Jarvis
            if result.get("status") == "waiting_approval":
                # Al levantar la excepción el código se detiene, NO pongas un 'return' después.
                raise interrupt(output) 
                
            # 3. Cortocircuito Anti-Loop (Permisos)
            if "Entorno local no detectado" in output or "Permisos insuficientes" in output:
                return f"CRITICAL ERROR: {output}. DO NOT RETRY. Tell the user you lack administrative permissions immediately."
                        
            # 4. Cortocircuito Anti-Loop (Errores críticos / Red)
            if "offline" in output.lower() or "connection" in output.lower() or "CRITICAL" in output:
                return (
                    f"CRITICAL FAILURE IN KODA: \n{output}\n\n"
                    "STOP. DO NOT call ask_lamar or any other agent to diagnose this. "
                    "Report the exact error to the user and wait for instructions."
                )
                
            return f"Koda Execution Report:\n{output}"            
        except interrupt:
            raise  # Lo lanzamos para que LangGraph lo intercepte y congele a Jarvis
            
        except Exception as e:
            logger.error(f"[JARVIS → KODA] Error: {str(e)}")
            return f"CRITICAL FAILURE: Koda error: {str(e)}. Inform the user."
        
    # DevOps (Lamar)
    def ask_lamar(devops_task: str, relevant_context: str = "") -> str:
        logger.info(f"[JARVIS → LAMAR] user={user_id} | task={devops_task[:80]}")
        try:
            full_instruction = (
                f"{devops_task}\n\nPREVIOUS CONTEXT:\n{relevant_context}" 
                if relevant_context else devops_task
            )
            agent = get_lamar(user_id=user_id)
            result = agent.run_task(instruction=full_instruction, user_id=user_id)
        
            if isinstance(result, dict):
                metadata = result.get("metadata", {})
                tokens = metadata.get("tokens", "No token info")
                output = result.get("output", "Success but no output.")
            else:
                output = str(result)
                tokens = "No token info (Result was not a dict)"

            logger.info(f"[LAMAR TOKENS] {tokens}")
            
            return f"Lamar (DevOps) Execution Report:\n{output}"
            
        except Exception as e:
            logger.error(f"[JARVIS → LAMAR] Error: {str(e)}")
            return f"CRITICAL FAILURE: Lamar error: {str(e)}. Inform the admin immediately."

    # ==========================================
    # TOOLS REGISTRATION
    # ==========================================

    tools = [
        StructuredTool.from_function(
            func=ask_nexus,
            name="ask_nexus",
            args_schema=NexusTaskInput,
            description=(
                "Use for: Google Calendar, Notion and productivity. "
                "IMPORTANT: Always fill relevant_context with what you already know — "
                "Nexus has NO memory of this conversation."
            )
        ),
        StructuredTool.from_function(
            func=ask_ragel,
            name="ask_ragel",
            args_schema=RagelTaskInput,
            description=(
                "Use ONLY for: live internet research, real-time news, uploaded documents "
                "(PDFs, Excel, CSVs), personal vector database queries. "
                "Do NOT use after Nexus/Webwright already extracted web data. "
                "Do NOT use for calendar, notion, files, or coding tasks. "
                "IMPORTANT: Always fill relevant_context with what you already know — "
                "Ragel has NO memory of this conversation."
            )
        ),
        StructuredTool.from_function(
            func=ask_koda,
            name="ask_koda",
            args_schema=KodaTaskInput,
            description=(
                "Use for: writing/debugging code, patching files, GitHub write operations, "
                "creating/modifying/renaming/deleting skills, and sandbox terminal commands. "
                "CRITICAL RULE: If the user asks an INFORMATIONAL question (like 'where is X folder?' "
                "or 'does X file exist?'), use Koda ONCE to find it, and then STOP IMMEDIATELY. "
                "Do NOT chain tools, do NOT create files, and do NOT run bash scripts unless "
                "the user explicitly asked you to create or modify something. "
                "IMPORTANT: Always fill relevant_context with what you already know — "
                "Koda has NO memory of this conversation."
            )
        ),
    ]
    
    try:
        db: Session = next(get_db()) # Obtener sesión
        user = db.query(User).filter(User.id == user_id).first()
        
        if user and user.is_admin:
            logger.info(f"[SECURITY] User {user_id} is Admin. Lamar DevOps tool enabled.")
            tools.append(
                StructuredTool.from_function(
                    func=ask_lamar,
                    name="ask_lamar",
                    args_schema=LamarTaskInput,
                    description=(
                        "RESTRICTED ADMIN TOOL. Use ONLY for DevOps tasks, server management, "
                        "cloud infrastructure, database migrations, and token/cost analysis. "
                        "Do NOT use for general coding (use Koda) or research (use Ragel). "
                        "CRITICAL RULE: The user CANNOT see the output of this tool. "
                        "Once you receive Lamar's DevOps Execution Report, you MUST read it, "
                        "synthesize the data, and present the final answer clearly to the user "
                        "in your next response. "
                        "IMPORTANT: Always fill relevant_context with what you already know — "
                        "Lamar has NO memory of this conversation."
                    )
                )
            )
    except Exception as e:
        logger.error(f"[SECURITY] Failed to verify admin status for {user_id}: {str(e)}")
        # Si falla la DB por seguridad NO agregamos la herramienta.

    return tools