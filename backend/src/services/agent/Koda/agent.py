# src/services/agent/Koda/agent.py
import os
import sys
import pytz
import uuid
from pathlib import Path
from datetime import datetime, timedelta
import logging
from dotenv import load_dotenv

from apscheduler.schedulers.background import BackgroundScheduler

current_dir = Path(__file__).resolve().parent.parent.parent
backend_dir = current_dir.parent.parent
sys.path.insert(0, str(backend_dir))

from src.core.time_helper import get_now
from src.database.models.models import AgentSession, AgentStatus
from src.services.agent.Koda.tools.hitl import check_timeout
logging.getLogger('apscheduler').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('tzlocal').setLevel(logging.WARNING)
logging.getLogger('mcp.client.streamable_http').setLevel(logging.WARNING)
from src.database.settings.connection import SessionLocal
from src.services.agent.common.base_agent import BaseAgent
from src.services.agent.Koda.tools import build_koda_tools
from src.services.llm.chat.llm_router import get_langchain_llm

load_dotenv()

# =================================================================
#                 SCHEDULER (RECOLECTOR DE BASURA)
# =================================================================
def job_check_timeouts():
    """Se ejecuta cada minuto para limpiar sesiones inactivas."""
    #print("🧹 [SCHEDULER] Verificando timeouts de Koda...")
    with SessionLocal() as db:
        # Solo verificamos las que están corriendo o esperando aprobación
        active_sessions = db.query(AgentSession).filter(
            AgentSession.status.in_([AgentStatus.RUNNING, AgentStatus.WAITING])
        ).all()
        
        for session in active_sessions:
            check_timeout(str(session.id)) # Tu función evalúa si ya pasó el tiempo y la cancela

# Singleton para evitar múltiples schedulers si se importa varias veces
_scheduler = BackgroundScheduler()
_scheduler_started = False

def start_koda_scheduler():
    global _scheduler_started
    if not _scheduler_started:
        _scheduler.add_job(job_check_timeouts, 'interval', minutes=10)
        _scheduler.start()
        _scheduler_started = True
        print("⏰ [KODA] Scheduler de timeouts iniciado (Ciclo de 10 min).")

# Iniciar el scheduler automáticamente al importar este módulo
start_koda_scheduler()

def get_koda_template() -> str:
    """Genera el template maestro leyendo AGENT.md y agregando sufijos de LangChain."""
    
    now = get_now()
    current_date = now.strftime("%A, %B %d, %Y - %H:%M")
    
    # 1. Leer dinámicamente el archivo AGENT.md
    agent_md_path = Path(__file__).resolve().parent / "AGENT.md"
    with open(agent_md_path, "r", encoding="utf-8") as f:
        agent_identity_and_rules = f.read()

    # 2. Agregar las variables obligatorias y el formato de LangChain
    langchain_suffix = f"""
CURRENT DATE AND TIME (Ecuador GMT-5): {current_date}
Use this date as reference for "today", "tomorrow", "this week", etc.
NEVER use years prior to 2026.

LANGUAGE RULE: Always respond in the exact same language the user used.
"""

    # 3. Unir todo y reemplazar la fecha
    full_template = agent_identity_and_rules + "\n" + langchain_suffix
    return full_template.replace("CURRENT_DATE_PLACEHOLDER", current_date)


class KodaAgent(BaseAgent):
    name = "Koda"

    def __init__(self, user_id: str):
        self.user_id = user_id
        llm = get_langchain_llm() 
        tools = build_koda_tools(user_id=user_id)
        template = get_koda_template()
        super().__init__(llm, tools, template)

# ─── Factory con caché + TTL de 12 horas ────────────────────────────────────
_koda_cache: dict[str, tuple] = {}
_CACHE_TTL = timedelta(hours=12)

def get_koda(user_id: str) -> KodaAgent:
    """
    Retorna la instancia de KodaAgent para ese user_id.
    """
    now = datetime.now()
    if user_id in _koda_cache:
        agent, created_at = _koda_cache[user_id]
        if now - created_at < _CACHE_TTL:
            return agent
    
    agent = KodaAgent(user_id=user_id)
    _koda_cache[user_id] = (agent, now)
    return agent


if __name__ == "__main__":
    #test_session = SessionLocal()
    test_chat_id = str(uuid.uuid4())
    test_user = os.getenv("USUARIO_TEST")
    test_session = str(uuid.uuid4()) # Creamos una sesión para la consola

    print("\n" + "=" * 50)
    print("💻 KODA: AUTONOMOUS AI SOFTWARE ENGINEER")
    print("Type 'q' to exit.")
    print("=" * 50)

    koda = get_koda(user_id=test_user)

    while True:
        try:
            user_input = input("\nUser: ")
            if user_input.lower() in ["salir", "exit", "quit", "q"]:
                print("Koda going offline.")
                break
            if not user_input.strip():
                continue
            
            print("\n[KODA is thinking and coding...]")
            
            # Pasamos los parámetros necesarios para el Grafo
            result = koda.run_task(
                instruction=user_input, 
                user_id=test_user,
                #chat_id=test_chat_id
            )
            
            if result["status"] == "waiting_approval":
                print(f"\n [HITL] Koda necesita aprobación: {result['output']}")
                print("En producción, aquí esperarías el click del Admin. En consola, puedes forzar el update.")
            else:
                print(f"\nKoda: {result['output']}")
            
        except Exception as e:
            print(f"\nFatal error: {e}")