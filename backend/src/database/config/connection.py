# src/database/config/engine_selector.py

import os
from src.config.logging_config import get_logger
from sqlalchemy.exc import OperationalError
from sqlalchemy import text

from .mysql_config import get_mysql_engine
from .azure_config import get_azure_engine

logger = get_logger("backend.engine")

def get_engine():
    env = os.getenv("ENV", "dev")

    if env == "prod":
        logger.info("Entorno: PRODUCCIÓN → usando Azure SQL")
        return get_azure_engine()
    
    # Entorno dev: intenta primero MySQL, si falla, usa Azure SQL
    try:
        logger.info("Entorno: DESARROLLO → intentando conexión con MySQL...")
        engine = get_mysql_engine()

        # Verifica si la conexión realmente funciona
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("✅ Conexión a MySQL exitosa.")
        return engine

    except OperationalError as e:
        logger.warning(f"⚠️ Conexión a MySQL fallida: {e}")
        logger.info("🔁 Usando fallback: Azure SQL")
        return get_azure_engine()
