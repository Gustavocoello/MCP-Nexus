import os
from sqlalchemy.exc import OperationalError
import mysql.connector.errors
from sqlalchemy import text
from src.database.config.mysql_config import get_mysql_engine
from src.database.config.azure_config import get_azure_engine
from src.config.logging_config import get_logger

logger = get_logger("backend.engine")

def get_engine():
    env = os.getenv("ENV", "prod").lower()

    if env == "prod":
        logger.info("Entorno: PRODUCCIÓN → usando Azure SQL directamente.")
        try:
            engine = get_azure_engine()
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("✅ Conexión a Azure SQL exitosa.")
            return engine
        except OperationalError as e:
            logger.error("❌ Error conectando a Azure SQL en producción.")
            logger.debug(f"Error Azure: {e}")
            raise e

    # DESARROLLO
    logger.info("Entorno: DESARROLLO → intentando conexión con MySQL...")

    try:
        engine = get_mysql_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("✅ Conexión a MySQL exitosa.")
        return engine

    except (OperationalError, mysql.connector.Error, Exception) as e:
        logger.warning("Falló conexión a MySQL, intentando fallback a Azure...")
        logger.debug(f"MySQL error: {e}")

        try:
            engine = get_azure_engine()
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("✅ Conexión a Azure SQL exitosa como fallback.")
            return engine
        except Exception as e2:
            logger.exception("Falló también conexión a Azure SQL.")
            logger.debug(f"Error Azure fallback: {e2}")
            raise e2

