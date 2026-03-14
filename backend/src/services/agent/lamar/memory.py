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
        # short message: until|timestamp
        message = f"cooldown|until:{unlock_time.strftime('%H:%M')}"
        # Usamos PingLog porque SI tiene status_code
        stat = PingLog(
            service=provider_name[:18],
            event_type="provider_cooldown",
            message=message,
            status_code=429, # Ahora esto NO fallará
            response_ms=0,
            client_ip="lamar",
            next_ping_sc=minutes * 60,
            timestamp=get_now()
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
            .filter(PingLog.event_type == "provider_cooldown")\
            .order_by(PingLog.timestamp.desc()).first()

        if last_status and last_status.next_ping_sc:
            # Use timestamp + next_ping_sc instead of parsing message
            from datetime import timedelta
            unlock_time = last_status.timestamp + timedelta(seconds=last_status.next_ping_sc)
            if unlock_time.tzinfo is None:
                unlock_time = TIMEZONE.localize(unlock_time)
            else:
                unlock_time = unlock_time.astimezone(TIMEZONE)
            return get_now() < unlock_time

        return False
    finally:
        session.close()