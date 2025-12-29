import os
import time
from sqlalchemy import text
import mysql.connector.errors
from sqlalchemy.exc import OperationalError
from src.config.logging_config import get_logger
from src.database.config.mysql_config import get_mysql_engine
from src.database.config.azure_config import get_azure_engine
from src.database.config.database_linux_config import get_mysql_linux_engine

logger = get_logger("backend.engine")

MAX_RETRIES = 2
RETRY_DELAY = 3

def try_connection(get_engine_fn, name):
    """Intenta conectar a una base de datos con reintentos."""
    for attempt in range(MAX_RETRIES + 1):
        try:
            logger.info(f"Intentando {name} (intento {attempt + 1}/{MAX_RETRIES + 1})")
            engine = get_engine_fn()
            
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            logger.info(f"Conexion exitosa a {name}")
            return engine.url
            
        except Exception as e:
            logger.warning(f"Fallo {name}: {str(e)[:150]}")
            
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
            else:
                raise

def get_database_url():
    """
    Orquestador de conexiones a bases de datos.
    
    DEV: Solo Windows
    PROD: Windows -> Linux -> Azure
    """
    env = os.getenv("ENV").lower()
    logger.info(f"Entorno: {env.upper()}")
    
    if env == "prod":
        logger.info("Cascada PROD: Windows -> Linux -> Azure")
        
        # Intentar Windows
        try:
            logger.info("Intentando Windows (principal)")
            return try_connection(get_mysql_engine, "Windows MySQL")
        except Exception as e:
            logger.warning("Windows no disponible, intentando Linux")
        
        # Fallback a Linux
        try:
            logger.info("Intentando Linux (fallback)")
            return try_connection(get_mysql_linux_engine, "Linux MySQL")
        except Exception as e:
            logger.warning("Linux no disponible, intentando Azure")
        
        # Ultimo recurso: Azure
        try:
            logger.info("Intentando Azure (ultimo recurso)")
            return try_connection(get_azure_engine, "Azure SQL")
        except Exception as e:
            logger.error("Todas las bases de datos fallaron")
            raise ConnectionError("No se pudo conectar a ninguna base de datos")
    
    else:
        # DEV: Solo Windows
        logger.info("Modo DEV: Usando Windows unicamente")
        try:
            return try_connection(get_mysql_engine, "Windows MySQL")
        except Exception as e:
            logger.error(f"Fallo conexion Windows en DEV: {str(e)}")
            raise ConnectionError("No se pudo conectar a Windows en modo desarrollo")