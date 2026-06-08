# src/services/agent/nexus/agent.py
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

current_dir = Path(__file__).resolve().parent.parent.parent
backend_dir = current_dir.parent.parent
sys.path.insert(0, str(backend_dir))

from src.services.agent.common.base_agent import BaseAgent
from src.services.agent.nexus.tools import build_calendar_tools, build_notion_tools
from src.services.llm.chat.llm_router import get_langchain_llm
from src.core.time_helper import get_now

load_dotenv()

def get_nexus_template():
    """Genera el template maestro leyendo AGENT.md y agregando sufijos de LangChain."""
    now = get_now()
    current_date = now.strftime("%A %d de %B de %Y, %H:%M")
    
    # 1. Leer dinámicamente el archivo AGENT.md
    agent_md_path = Path(__file__).resolve().parent / "AGENT.md"
    with open(agent_md_path, "r", encoding="utf-8") as f:
        agent_identity_and_rules = f.read()

    # 2. Agregar las variables obligatorias y el formato de LangChain
    langchain_suffix = """
CURRENT DATE AND TIME (Ecuador GMT-5): CURRENT_DATE_PLACEHOLDER
Use this date as a reference for calculating "today," "tomorrow," "this week," etc.
NEVER use years prior to 2026 in dates or Futures dates depend the data.

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

User input: {input}

{agent_scratchpad}"""

    # 3. Unir todo y reemplazar la fecha
    full_template = agent_identity_and_rules + "\n" + langchain_suffix
    return full_template.replace("CURRENT_DATE_PLACEHOLDER", current_date)

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
    now = get_now()
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
            resultado = nexus.run_task(instruction=user_input, user_id=test_user)
            print(f"\nNexus: {resultado['output']}")
        except KeyboardInterrupt:
            print("\nInterrupt detected. Exiting...")
            break
        except Exception as e:
            print(f"\nError: {e}")