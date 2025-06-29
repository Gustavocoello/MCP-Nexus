import os
import time
from sqlalchemy import text
import mysql.connector.errors
from sqlalchemy.exc import OperationalError
from src.config.logging_config import get_logger
from src.database.config.mysql_config import get_mysql_engine
from src.database.config.azure_config import get_azure_engine

logger = get_logger("backend.engine")

MAX_RETRIES = 2  # Número de reintentos adicionales
RETRY_DELAY = 5  # Segundos de espera entre reintentos

def get_engine():
    env = os.getenv("ENV", "dev").lower()
    logger.info(f"Valor real de ENV: {os.getenv('ENV')}")

    
    def try_connection(get_engine_fn, name):
        for attempt in range(MAX_RETRIES + 1):
            try:
                engine = get_engine_fn()
                with engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                logger.info(f"✅ Conexión a {name} exitosa.")
                return (engine)
            except Exception as e:
                logger.warning(f"Falló conexión a {name}. Intento {attempt + 1} de {MAX_RETRIES + 1}")
                logger.debug(f"{name} error: {e}")
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY)
                else:
                    raise

    if env == "prod":
        logger.info("Entorno: PRODUCCIÓN → usando Azure SQL directamente.")
        return try_connection(get_azure_engine, "Azure SQL")
    
    # DESARROLLO
    logger.info("Entorno: DESARROLLO → Intentando conexión con MySQL...(fallback a Azure si falla)")

    try:
        engine = get_mysql_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("✅ Conexión a MySQL exitosa.")
        return (engine)

    except (OperationalError, mysql.connector.Error, Exception) as e:
        logger.warning("Falló conexión a MySQL, intentando fallback a Azure...")
        logger.debug(f"MySQL error: {e}")

        try:
            return try_connection(get_azure_engine, "Azure SQL (fallback)")
        except Exception as e2:
            logger.exception("Falló también conexión a Azure SQL.")
            logger.debug(f"Error Azure fallback: {e2}")
            raise e2


