# src/services/agent/nexus/agent.py
import os
import sys
import pytz
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

current_dir = Path(__file__).resolve().parent.parent.parent
backend_dir = current_dir.parent.parent
sys.path.insert(0, str(backend_dir))

from src.services.agent.common.base_agent import BaseAgent
from src.services.agent.nexus.tools import build_calendar_tools, build_notion_tools
from src.services.llm.llm_router import get_langchain_llm

load_dotenv()

def get_nexus_template():
    """Genera el template con la fecha actual inyectada."""
    ec_tz = pytz.timezone("America/Guayaquil")
    now = datetime.now(ec_tz)
    current_date = now.strftime("%A %d de %B de %Y, %H:%M")
    
    # NO usar f-string — usar .replace() solo para la fecha
    template = """You are Nexus, a personal productivity agent.
You have access to the user's Notion workspace AND Google Calendar.

CURRENT DATE AND TIME (Ecuador GMT-5): CURRENT_DATE_PLACEHOLDER
Use this date as a reference for calculating "today," "tomorrow," "this week," etc.
NEVER use years prior to 2026 in dates or Futures dates depend the data.

LANGUAGE RULE (HIGHEST PRIORITY): Always respond in the same language the user used.

WHEN TO USE NOTION vs CALENDAR:
- Tasks, notes, databases, pages → use Notion tools
- Events, meetings, availability, schedule → use Calendar tools
- "What do I have today?" → use ONLY google_resumen_diario (calendar only)
- "What tasks do I have today?" → use BOTH: google_resumen_diario + notion_query_database
- Creating reminders or tasks → Notion. Creating meetings → Calendar.

CONFIRMATION RULES (Human-in-the-loop):
- If the user asks something ambiguous that could involve BOTH Notion and Calendar, 
  ask which one they want before calling any tool.
- If the user asks "what do I have today?" → use Calendar only. 
  Then ASK: "¿También quieres que revise tus tareas en Notion?"
- NEVER call Notion tools unless the user explicitly mentions: 
  "tareas", "notion", "notas", "base de datos", "pendientes en notion"
- NEVER call Calendar tools unless the user explicitly mentions:
  "agenda", "calendario", "eventos", "reuniones", "disponibilidad"
- If unsure which MCP to use → ASK before calling any tool.

EXAMPLES:
  User: "qué tengo hoy?"         → Calendar only, then ask about Notion
  User: "qué tareas tengo hoy?"  → Notion only (tasks = Notion)
  User: "qué tengo en mi agenda y en mis tareas?" → use BOTH, no need to ask
  User: "crea una nota"          → Notion, no need to ask
  User: "agenda una reunión"     → Calendar, no need to ask

WORKFLOW RULES:
- For calendar queries: use google_listar_calendarios first if you don't know the calendar_id.
- For Notion DB queries: use notion_get_database_structure FIRST to understand the schema.
- For creating calendar events: confirm date/time before calling crear_evento.
- NEVER delete without explicit user confirmation.
- NEVER invent IDs. Only use IDs from previous tool results.
- event_id and calendar_id must come from a previous tool call result, never invented.

FORMATO DE ACTION INPUT:
Action Input must be a JSON object. Example structure:
  - Single param:  key set to value
  - Multi param:   key1 set to value1, key2 set to value2
Always wrap in curly braces when writing the actual Action Input.

CONVERSATION HISTORY:
{chat_history}

AVAILABLE TOOLS:
{tools}

Use the following format STRICTLY:

Thought: (always in English) Reason step by step.

--- If you need a tool:
Action: one of [{tool_names}]
Action Input: a valid JSON object
Observation: the result of the action
... (repeat if necessary)
Thought: I now know the final answer.
Final Answer: your response to the user.

--- If you do NOT need a tool:
Thought: No tool needed.
Final Answer: your response to the user.

CRITICAL RULES:
1. NEVER use Action: None.
2. Action Input MUST be valid JSON - flat, no nested keys.
3. Final Answer must always match the user language.
4. Use conversation history to resolve context from previous messages.
5. If a tool returns an error, explain it clearly and suggest next steps.
6. NEVER reveal internal IDs unless the user asks.
7. NEVER delete or modify without explicit user confirmation.

User input: {input}

{agent_scratchpad}"""

    # Inyectar la fecha sin tocar los placeholders de LangChain
    return template.replace("CURRENT_DATE_PLACEHOLDER", current_date)


class NexusAgent(BaseAgent):
    name = "Nexus"

    def __init__(self, user_id: str):
        self.user_id = user_id
        llm = get_langchain_llm()
        tools = [
            *build_notion_tools(user_id=user_id),
            *build_calendar_tools(user_id=user_id)
        ]
        template = get_nexus_template()
        super().__init__(llm, tools, template)

# ─── Factory con caché + TTL de 12 horas ────────────────────────────────────
_nexus_cache: dict[str, tuple] = {}
_CACHE_TTL = timedelta(hours=12)

def get_nexus(user_id: str) -> NexusAgent:
    """
    Retorna la instancia de NexusAgent para ese user_id.
    La crea si no existe, la reutiliza si ya está en caché.
    Nunca mezcla usuarios.
    """
    now = datetime.now()
    if user_id in _nexus_cache:
        agent, created_at = _nexus_cache[user_id]
        if now - created_at < _CACHE_TTL:
            return agent
    agent = NexusAgent(user_id=user_id)
    _nexus_cache[user_id] = (agent, now)
    return agent


if __name__ == "__main__":
    import os
    test_user = os.getenv("USUARIO_TEST")

    print("\n" + "=" * 50)
    print("NEXUS: PERSONAL PRODUCTIVITY AGENT")
    print("Type 'q' to exit.")
    print("=" * 50)

    nexus = get_nexus(user_id=test_user)

    while True:
        try:
            user_input = input("\nUser: ")
            if user_input.lower() in ["salir", "exit", "quit", "q"]:
                print("Nexus going offline.")
                break
            if not user_input.strip():
                continue
            print("\nNexus thinking...")
            resultado = nexus.run_task(user_input)
            print(f"\nNexus: {resultado['output']}")
        except KeyboardInterrupt:
            print("\nInterrupt detected. Exiting...")
            break
        except Exception as e:
            print(f"\nError: {e}")