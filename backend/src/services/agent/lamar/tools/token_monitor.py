# src/services/agent/lamar/tools/token_monitor.py
from datetime import timedelta
from langchain_core.tools import tool
from src.core.time_helper import get_now
from src.database.models.models import TokenLog
from src.database.settings.connection import get_db

@tool
def get_llm_usage_report() -> str:
    """Consulta los tokens consumidos en las últimas 24 horas."""
    try:
        db = next(get_db())
        hace_24h = get_now() - timedelta(hours=24)
        logs = db.query(TokenLog).filter(TokenLog.timestamp >= hace_24h).all()
        
        if not logs:
            return "Lamar Report: No hay consumo registrado en las últimas 24h."
        
        resumen = {}
        for log in logs:
            resumen[log.model_name] = resumen.get(log.model_name, 0) + (log.total_tokens or 0)
        
        report_str = ", ".join([f"{mod}: {tok} tokens" for mod, tok in resumen.items()])
        return f"Consumo 24h: {report_str}"
    except StopIteration:
        return "Error: Database session unavailable."
    finally:
        if 'db' in locals():
            db.close()

def build_token_monitor_tools(user_id: str, client_type: str = "web") -> list:
    return [get_llm_usage_report]