import os
import urllib.parse
from sqlalchemy import text
from sqlalchemy import create_engine
from src.config.logging_config import get_logger

logger = get_logger("backend.engine")

def get_azure_engine():
    USER_AZURE = os.getenv("USER_BD_AZURE")
    USER_PASS = os.getenv("PASS_BD_AZURE")
    BASE_AZURE = os.getenv("NAME_BD_AZURE")
    ROOT_AZURE = os.getenv("ROOT_BD_AZURE")  # Ej: mcpserver.database.windows.net

    # 💾 Primer intento con el que te sirvió para migraciones
    logger.info("🔌 Intentando conexión a Azure SQL con params_migrations...")

    try:
        params_migrations = urllib.parse.quote_plus(
            f"DRIVER={{ODBC Driver 18 for SQL Server}};"
            f"SERVER=tcp:{ROOT_AZURE};"
            f"DATABASE={BASE_AZURE};"
            f"UID={USER_AZURE};"
            f"PWD={urllib.parse.quote_plus(USER_PASS)};"
            "Encrypt=yes;"
            "TrustServerCertificate=no;"
            "Connection Timeout=30;"
        )
        engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params_migrations}")
        # test connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("✅ Conexión a Azure SQL exitosa con params_migrations.")
        return engine

    except Exception as e1:
        logger.warning("Falló conexión con params_migrations. Probando alternativa estándar...")
        logger.debug(f"Error migración Azure: {e1}")

    # 🛠 Segundo intento con cadena estándar
    try:
        params_standard = urllib.parse.quote_plus(
            f"DRIVER={{ODBC Driver 18 for SQL Server}};"
            f"SERVER={ROOT_AZURE};"
            f"DATABASE={BASE_AZURE};"
            f"UID={USER_AZURE};"
            f"PWD={urllib.parse.quote_plus(USER_PASS)};"
            "Encrypt=yes;"
            "TrustServerCertificate=no;"
            "Connection Timeout=30;"
        )
        engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params_standard}")
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("✅ Conexión a Azure SQL exitosa con cadena estándar.")
        return engine

    except Exception as e2:
        logger.error("Falló conexión a Azure SQL con ambos métodos.")
        logger.exception(e2)
        raise e2
