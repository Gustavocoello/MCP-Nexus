import os
import sys
import pytz
from pathlib import Path
from datetime import datetime, timedelta

current_dir = Path(__file__).resolve().parent.parent.parent
backend_dir = current_dir.parent.parent
sys.path.insert(0, str(backend_dir))

from src.core.time_helper import get_now
from src.services.agent.common.base_agent import BaseAgent
from src.services.llm.chat.llm_router import get_langchain_llm

# Asumimos que aquí importarás las herramientas que delegan a los otros agentes
# (Te dejaré un ejemplo de cómo se verán estas herramientas en el siguiente paso)
from src.services.agent.jarvis.tools import build_jarvis_tools

def get_jarvis_template():
    """Genera el template maestro leyendo AGENT.md y agregando sufijos de LangChain."""
    now = get_now()
    current_date = now.strftime("%A %d de %B de %Y, %H:%M")
    
    # 1. Leer dinámicamente el archivo AGENT.md
    agent_md_path = Path(__file__).resolve().parent / "AGENT.md"
    with open(agent_md_path, "r", encoding="utf-8") as f:
        agent_identity_and_rules = f.read()

    # 2. Agregar las variables obligatorias que LangChain necesita para funcionar
    langchain_suffix = """
CURRENT SYSTEM DATE AND TIME (Ecuador GMT-5): CURRENT_DATE_PLACEHOLDER
Use this as your absolute ground truth for any time-based reasoning.

CONVERSATION HISTORY:
{chat_history}

AVAILABLE TOOLS (Your Sub-Agents & Skills):
{tools}

Follow this execution format STRICTLY:

Thought: (always in English) Analyze the user's request with extreme precision. State if a tool is needed or not.

--- If you NEED to delegate to a sub-agent or run a skill:
Action: the tool name (one of [{tool_names}])
Action Input: a valid JSON object with the exact parameters needed.
Observation: the intelligence returned by the sub-agent.
... (repeat Thought/Action/Observation if further delegation is required)
Thought: I have gathered all necessary intelligence. I am ready to respond.
Final Answer: Your perfectly crafted response to the user.

--- If you DO NOT need a tool (Direct Answer):
Thought: No tool needed. I have the knowledge required in my memory. I will now explain this in detail.
Final Answer: [Your expansive, friendly, and highly detailed response, using markdown and ending with an engaging question].

CRITICAL CONSTRAINTS:
- NEVER expose internal tool names, JSON payloads, or raw agent mechanics to the user.
- Action Input MUST be valid JSON.
- If a sub-agent reports an error, gracefully inform the user of the system failure and propose a secondary plan.

User input: {input}

{agent_scratchpad}"""

    # 3. Unir todo y reemplazar la fecha
    full_template = agent_identity_and_rules + "\n" + langchain_suffix
    return full_template.replace("CURRENT_DATE_PLACEHOLDER", current_date)


class JarvisAgent(BaseAgent):
    name = "Jarvis"

    def __init__(self, user_id: str):
        self.user_id = user_id
        llm = get_langchain_llm() 
        tools = build_jarvis_tools(user_id=user_id)
        template = get_jarvis_template()
        super().__init__(llm, tools, template)


# ─── Factory con caché + TTL de 12 horas ────────────────────────────────────
_jarvis_cache: dict[str, tuple] = {}
_CACHE_TTL = timedelta(hours=12)

def get_jarvis(user_id: str) -> JarvisAgent:
    """
    Retorna la instancia de JarvisAgent (El Orquestador) para ese user_id.
    La crea si no existe, la reutiliza si ya está en caché.
    """
    now = get_now()
    if user_id in _jarvis_cache:
        agent, created_at = _jarvis_cache[user_id]
        if now - created_at < _CACHE_TTL:
            return agent
    
    agent = JarvisAgent(user_id=user_id)
    _jarvis_cache[user_id] = (agent, now)
    return agent

if __name__ == "__main__":
    import os
    test_user = os.getenv("USUARIO_TEST")

    print("\n" + "=" * 50)
    print("JARVIS: PERSONAL ASSISTANT")
    print("Type 'q' to exit.")
    print("=" * 50)

    jarvis = get_jarvis(user_id=test_user)

    while True:
        try:
            user_input = input("\nUser: ")
            if user_input.lower() in ["salir", "exit", "quit", "q"]:
                print("Jarvis going offline.")
                break
            if not user_input.strip():
                continue
            print("\nJarvis thinking...")
            result = jarvis.run_task(
                instruction=user_input, 
                user_id=test_user,
                #chat_id=test_chat_id
            )
            print(f"\nJarvis: {result['output']}")
        except KeyboardInterrupt:
            print("\nInterrupt detected. Exiting...")
            break
        except Exception as e:
            print(f"\nError: {e}")