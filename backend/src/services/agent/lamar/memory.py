# src/services/llm/lamar/memory.py
from datetime import datetime, timedelta
from src.config.time_helper import get_now, TIMEZONE
from src.database.models.models import PingLog 
from src.database.config.connection import SessionLocal

def set_provider_cooldown(provider_name, minutes=60):
    """Marca un proveedor como 'No Disponible' por N minutos."""
    session = SessionLocal()
    try:
        unlock_time = get_now() + timedelta(minutes=minutes)
        # Usamos PingLog porque SI tiene status_code
        stat = PingLog(
            service=provider_name,
            event_type="PROVIDER_COOLDOWN",
            message=f"COOLDOWN_UNTIL:{unlock_time.isoformat()}",
            status_code=429 # Ahora esto NO fallará
        )
        session.add(stat)
        session.commit()
    finally:
        session.close()

def is_provider_blocked(provider_name):
    session = SessionLocal()
    try:
        last_status = session.query(PingLog)\
            .filter(PingLog.service == provider_name)\
            .filter(PingLog.event_type == "PROVIDER_COOLDOWN")\
            .order_by(PingLog.timestamp.desc()).first()
        
        if last_status and "COOLDOWN_UNTIL:" in (last_status.message or ""):
            # Bug 1 fix: split on the full prefix, not just ":"
            unlock_str = last_status.message.split("COOLDOWN_UNTIL:")[1]
            from datetime import datetime
            unlock_time = datetime.fromisoformat(unlock_str)
            
            # Bug 2 fix: force timezone if naive
            if unlock_time.tzinfo is None:
                unlock_time = TIMEZONE.localize(unlock_time)
            else:
                unlock_time = unlock_time.astimezone(TIMEZONE)
            
            return get_now() < unlock_time
        
        return False
    finally:
        session.close()