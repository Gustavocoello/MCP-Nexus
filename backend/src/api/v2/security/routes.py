from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, Request, Header, HTTPException, status
from sqlalchemy.orm import Session

from src.core.time_helper import get_now
from src.core.logging import get_logger
from src.database.models.models import PingLog
from src.database.settings.connection import get_db, engine
from src.core.ping.log_parser import parse_ping_log_v1, clean_log_message
from src.database.settings.azure.azure_database import test_connection_health, get_pool_stats

logger = get_logger(__name__)

# En FastAPI, en lugar de 3 Blueprints, podemos crear 3 Routers 
# (Luego en tu app principal haces app.include_router(...) con los prefijos que desees)
ping_logs_router = APIRouter()
ping_router = APIRouter()
health_router = APIRouter()

# ==========================================
# MODELOS PYDANTIC
# ==========================================
class PingLogRequest(BaseModel):
    log: str

# ==========================================
# 1. PING LOGS (Monitoreo de latencias)
# ==========================================
@ping_logs_router.post("/ping_log", status_code=status.HTTP_201_CREATED)
async def receive_ping_log(
    request: Request,
    payload: PingLogRequest,
    db: Session = Depends(get_db)
):
    """
    Endpoint centralizado para recibir pings.
    Validado automáticamente por Pydantic (garantiza que 'log' sea un string).
    """
    # FastAPI extrae la IP real de manera segura
    client_host = request.client.host if request.client else "unknown"
    
    try:
        raw_message = payload.log.strip()
        if not raw_message:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No log provided")

        # 1. Limpiar y parsear el mensaje
        cleaned_message = clean_log_message(raw_message)
        parsed = parse_ping_log_v1(cleaned_message)
        
        # Nota: (get_now() - get_now()) casi siempre será 0. Lo dejo como en tu original.
        response_ms = (get_now() - get_now()).total_seconds() * 1000  
        
        # 2. Asignación segura de variables (Corregido el bug de las comas/tuplas de Flask)
        if not parsed:
            service = "General-Log"
            event_type = "info"
            status_code = 200
            message = cleaned_message
            next_ping_sc = None
        else:
            service = parsed.get("service", "Unknown")
            event_type = parsed.get("event_type", "info")
            message = parsed.get("message", cleaned_message)
            status_code = parsed.get("status_code", 200)
            next_ping_sc = parsed.get("next_ping_sc")

        # 3. Crear y guardar el registro
        new_log = PingLog(
            service=service,
            event_type=event_type,
            message=message,
            response_ms=response_ms,
            status_code=status_code,
            client_ip=client_host,
            next_ping_sc=next_ping_sc,
            timestamp=get_now()
        )
        
        db.add(new_log)
        db.commit()
        
        return {
            "status": "ok",
            "service": service,
            "timestamp": get_now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback() 
        logger.exception("Error guardando ping log centralizado")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ==========================================
# 2. PING SIMPLE (Verificador de estado del Server)
# ==========================================
@ping_router.get("/ping")
async def ping(
    request: Request,
    # Inyectamos el User-Agent automáticamente, con "unknown" como fallback
    user_agent: Optional[str] = Header(default="unknown", alias="User-Agent")
):
    client_ip = request.client.host if request.client else "unknown"
    now = get_now().isoformat()
    
    # logging.info(f"[PONG]")
    return {
        "status": "pong",
        "message": "Render server is alive! - Backend",
        "client_ip": client_ip,
        "user_agent": user_agent,
        "timestamp": now
    }


# ==========================================
# 3. HEALTH CHECKS Y POOL STATS (BD)
# ==========================================
@health_router.get("/db-health")
async def db_health_check_route():
    """
    Health Check que utiliza la función auxiliar para despertar Azure.
    """
    try:
        # Usamos el engine global directamente (No es necesario abrir una SessionLocal
        # si test_connection_health utiliza el engine a bajo nivel)
        health_data = test_connection_health(engine)
        
        if health_data.get('status') == 'unhealthy':
            logger.error(f"DB Health Check Falló: {health_data.get('error')}")
            # Retornamos código 503 pero incluimos la data para que el dashboard lo lea
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE, 
                detail=health_data
            )

        logger.info("DB Health Check Exitoso (Azure está despierto)")
        return health_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error crítico en health check")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"status": "unhealthy", "error": str(e)}
        )

@health_router.get('/pool-stats')
async def pool_stats_endpoint():
    """
    Endpoint para monitorear el pool de conexiones y evitar fugas de RAM.
    """
    try:
        stats_data = get_pool_stats(engine) 
        return stats_data
    except Exception as e:
        logger.exception(f"Error obteniendo pool stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=str(e)
        )