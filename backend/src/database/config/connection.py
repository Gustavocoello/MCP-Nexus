import os
import time
from sqlalchemy import text
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.config.logging_config import get_logger
from src.database.config.azure.azure_config import get_azure_engine
from src.database.config.postgres.database_win_config import get_pg_engine as win_pg_engine
from src.database.config.postgres.database_linux_config import get_pg_engine as linux_pg_engine

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
            return try_connection(win_pg_engine, "Windows PostgreSQL")
        except Exception as e:
            logger.warning("Windows no disponible, intentando Linux")
        
        # Fallback a Linux
        try:
            logger.info("Intentando Linux (fallback)")
            return try_connection(linux_pg_engine, "Linux PostgreSQL")
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
            return try_connection(win_pg_engine, "Windows PostgreSQL")
        except Exception as e:
            logger.error(f"Fallo conexion Windows en DEV: {str(e)}")
            raise ConnectionError("No se pudo conectar a Windows en modo desarrollo")
        
try:
    DATABASE_URL = get_database_url()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=create_engine(DATABASE_URL))
    logger.info("SessionLocal creada exitosamente")
except Exception as e:
    logger.critical(f"No se pudo crear SessionLocal: {str(e)}")
    raise