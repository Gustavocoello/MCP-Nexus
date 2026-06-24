# src/services/agent/lamar/agent.py
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

current_dir = Path(__file__).resolve().parent.parent.parent
backend_dir = current_dir.parent.parent
sys.path.insert(0, str(backend_dir))

from src.core.time_helper import get_now
from src.services.agent.common.base_agent import BaseAgent
from src.services.agent.lamar.tool import build_lamar_tools
from src.services.llm.chat.llm_router import API_PROVIDERS_TO_AGENT, get_langchain_llm

load_dotenv()

# =================================================================
#                        TEMPLATE
# =================================================================
def get_lamar_template() -> str:
    """Genera el template maestro leyendo AGENT.md y agregando sufijos de LangChain."""
    
    now = get_now()
    current_date = now.strftime("%A %d de %B de %Y, %H:%M")
    
    agent_md_path = Path(__file__).resolve().parent / "AGENT.md"
    with open(agent_md_path, "r", encoding="utf-8") as f:
        agent_identity_and_rules = f.read()

    langchain_suffix = f"""
        CURRENT DATE AND TIME (Ecuador GMT-5): {current_date}
        Use this date as reference for "today", "tomorrow", "this week", etc.
        NEVER use years prior to 2026.

        LANGUAGE RULE: Always respond in the exact same language the user used.
        
        You are Lamar, DevOps AI. Keep it technical.
        """

    return agent_identity_and_rules + "\n" + langchain_suffix
# =================================================================
#                        AGENT CLASS
# =================================================================
class LamarAgent(BaseAgent):
    name = "Lamar"

    def __init__(self, user_id: str, client_type: str = "web"):
        self.user_id = user_id
        llm = get_langchain_llm()
        tools = build_lamar_tools(user_id, client_type=client_type)
        template = get_lamar_template()
        super().__init__(llm, tools, template)


# =================================================================
#                    FACTORY + CACHÉ TTL
# =================================================================
_lamar_cache: dict[str, tuple] = {}
_CACHE_TTL = timedelta(hours=12)

def get_lamar(user_id: str, client_type: str = "web") -> LamarAgent:
    """Retorna la instancia de LamarAgent para ese user_id, con caché de 12h."""
    now = datetime.now()
    cache_key = f"{user_id}:{client_type}"
    if cache_key in _lamar_cache:
        agent, created_at = _lamar_cache[cache_key]
        if now - created_at < _CACHE_TTL:
            return agent

    agent = LamarAgent(user_id=user_id, client_type=client_type)
    _lamar_cache[cache_key] = (agent, now)
    return agent


# =================================================================
#                        CONSOLA (DEV)
# =================================================================
if __name__ == "__main__":
    test_user = os.getenv("USUARIO_TEST")
    print("\n" + "=" * 50)
    print("LAMAR: ONLINE RESILIENCE ORCHESTRATOR")
    print("Type 'q' to end the session.")
    print("=" * 50)

    lamar = get_lamar(user_id=test_user)

    while True:
        try:
            user_input = input("\n User: ")
            if user_input.lower() in ["salir", "exit", "quit", "q"]:
                print("Locking systems... Until next time, socio.")
                break
            if not user_input.strip():
                continue
            print("\n Lamar thinking...")
            result = lamar.run_task(instruction=user_input, user_id=test_user)
            print(f"\n Lamar: {result['output']}")
        except KeyboardInterrupt:
            print("\n\nInterrupt detected. Exiting.")
            break
        except Exception as e:
            print(f"\n Error in main loop: {e}")