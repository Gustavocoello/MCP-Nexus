# src/services/agent/Koda/tools/scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session
from src.database.settings.connection import SessionLocal
from src.database.models.models import AgentSession, AgentStatus
from hitl import check_timeout

def job_check_timeouts():
    """Se ejecuta cada minuto para limpiar sesiones inactivas."""
    print("[SCHEDULER] Verificando timeouts de Koda...")
    with SessionLocal() as db:
        # Solo verificamos las que están corriendo o esperando
        active_sessions = db.query(AgentSession).filter(
            AgentSession.status.in_([AgentStatus.RUNNING, AgentStatus.WAITING])
        ).all()
        
        for session in active_sessions:
            check_timeout(str(session.id)) # Tu función ya hace la lógica y commit

# En tu main.py o lifespan de FastAPI:
scheduler = BackgroundScheduler()
scheduler.add_job(job_check_timeouts, 'interval', minutes=1)
scheduler.start()