# src/services/agent/ragel/agent.py
import os
import sys
import pytz
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

current_dir = Path(__file__).resolve().parent.parent.parent
backend_dir = current_dir.parent.parent
sys.path.insert(0, str(backend_dir))

from src.core.time_helper import get_now
from src.services.agent.common.base_agent import BaseAgent
from src.services.llm.chat.llm_router import get_langchain_llm
from src.services.agent.ragel.tools import build_ragel_tools

load_dotenv()

def get_ragel_template():
    """Generates the template by reading AGENT.md and appending LangChain formats."""
    now = get_now()
    current_date = now.strftime("%A %d de %B de %Y, %H:%M")
    
    # 1. Leer dinámicamente el archivo AGENT.md
    agent_md_path = Path(__file__).resolve().parent / "AGENT.md"
    with open(agent_md_path, "r", encoding="utf-8") as f:
        agent_identity_and_rules = f.read()

    # 2. Agregar las variables obligatorias y el formato de LangChain
    langchain_suffix = """
CURRENT DATE AND TIME (Ecuador GMT-5): CURRENT_DATE_PLACEHOLDER
Use this date as a reference for recent news, events, and temporal queries (e.g., "today", "yesterday", "last week").

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


class RagelAgent(BaseAgent):
    name = "Ragel"

    def __init__(self, user_id: str):
        self.user_id = user_id
        llm = get_langchain_llm()
        # Se asume que build_ragel_tools devuelve la lista de herramientas (Tavily, Brave, DDG)
        tools = build_ragel_tools(user_id=user_id)
        template = get_ragel_template()
        super().__init__(llm, tools, template)

# ─── Factory con caché + TTL de 12 horas ────────────────────────────────────
_ragel_cache: dict[str, tuple] = {}
_CACHE_TTL = timedelta(hours=12)

def get_ragel(user_id: str) -> RagelAgent:
    """
    Returns the RagelAgent instance for the given user_id.
    Creates it if it does not exist, reuses it if in cache.
    """
    now = datetime.now()
    if user_id in _ragel_cache:
        agent, created_at = _ragel_cache[user_id]
        if now - created_at < _CACHE_TTL:
            return agent
    agent = RagelAgent(user_id=user_id)
    _ragel_cache[user_id] = (agent, now)
    return agent


if __name__ == "__main__":
    import os
    test_user = os.getenv("USUARIO_TEST")

    print("\n" + "=" * 50)
    print("RAGEL: SENIOR WEB RESEARCHER AGENT")
    print("Type 'q' to exit.")
    print("=" * 50)

    ragel = get_ragel(user_id=test_user)

    while True:
        try:
            user_input = input("\nUser: ")
            if user_input.lower() in ["salir", "exit", "quit", "q"]:
                print("Ragel going offline.")
                break
            if not user_input.strip():
                continue
            print("\nRagel thinking...")
            resultado = ragel.run_task(user_input)
            print(f"\nRagel:\n{resultado['output']}")
        except KeyboardInterrupt:
            print("\nInterrupt detected. Exiting...")
            break
        except Exception as e:
            print(f"\nError: {e}")