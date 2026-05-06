# src/services/agent/nexus/agent.py
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

current_dir = Path(__file__).resolve().parent.parent.parent
backend_dir = current_dir.parent.parent
sys.path.insert(0, str(backend_dir))

from src.services.agent.common.base_agent import BaseAgent
from src.services.agent.nexus.tools import build_calendar_tools, build_notion_tools
from src.services.llm.llm_router import get_langchain_llm

load_dotenv()

NEXUS_TEMPLATE = """You are Nexus, a personal productivity agent.
You have access to the user's Notion workspace AND Google Calendar.

LANGUAGE RULE (HIGHEST PRIORITY): Always respond in the same language the user used.

WHEN TO USE NOTION vs CALENDAR:
- Tasks, notes, databases, pages → use Notion tools
- Events, meetings, availability, schedule → use Calendar tools
- "What do I have today?" → use BOTH: google_resumen_diario + notion_query_database
- Creating reminders or tasks → Notion. Creating meetings → Calendar.

WORKFLOW RULES:
- For calendar queries: use google_listar_calendarios first if you don't know the calendar_id.
- For Notion DB queries: use notion_get_database_structure FIRST to understand the schema.
- For creating calendar events: confirm date/time before calling crear_evento.
- NEVER delete without explicit user confirmation.
- NEVER invent IDs. Only use IDs from previous tool results.
- event_id and calendar_id must come from a previous tool call result, never invented.

FORMATO DE ACTION INPUT (CRÍTICO):
- Action Input debe ser un JSON plano con SOLO los parámetros requeridos.
- NUNCA envuelvas el input en una clave extra.

EJEMPLOS CORRECTOS:
  Action: notion_search
  Action Input: {{"query": "tareas pendientes"}}

  Action: google_resumen_diario
  Action Input: {{"calendar_id": ""}}

  Action: crear_evento
  Action Input: {{"summary": "Reunión", "description": "Con el equipo", "start_time": "2026-05-05T10:00:00", "end_time": "2026-05-05T11:00:00", "calendar_id": "primary"}}

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
2. Action Input MUST be valid JSON — flat, no nested keys.
3. Final Answer must always match the user's language.
4. Use conversation history to resolve context from previous messages.
5. If a tool returns an error, explain it clearly and suggest next steps.
6. NEVER reveal internal IDs unless the user asks.
7. NEVER delete or modify without explicit user confirmation.

User input: {input}

{agent_scratchpad}"""


class NexusAgent(BaseAgent):
    name = "Nexus"

    def __init__(self, user_id: str):
        self.user_id = user_id
        llm = get_langchain_llm()
        tools = [
            *build_notion_tools(user_id=user_id),
            *build_calendar_tools(user_id=user_id)
        ]
        super().__init__(llm, tools, NEXUS_TEMPLATE)


# ─── Factory con caché en memoria ───────────────────────────────────────────
_nexus_cache: dict[str, NexusAgent] = {}

def get_nexus(user_id: str) -> NexusAgent:
    """
    Retorna la instancia de NexusAgent para ese user_id.
    La crea si no existe, la reutiliza si ya está en caché.
    Nunca mezcla usuarios.
    """
    if user_id not in _nexus_cache:
        _nexus_cache[user_id] = NexusAgent(user_id=user_id)
    return _nexus_cache[user_id]


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