import os
import urllib.parse
from dotenv import load_dotenv
from sqlalchemy.pool import NullPool 
from sqlalchemy import create_engine
from sqlalchemy import text, event, exc
from src.config.logging_config import get_logger

logger = get_logger("backend.engine")

load_dotenv()

def get_azure_engine():
    USER_AZURE = os.getenv("USER_BD_AZURE")
    USER_PASS = os.getenv("PASS_BD_AZURE")
    BASE_AZURE = os.getenv("NAME_BD_AZURE")
    ROOT_AZURE = os.getenv("ROOT_BD_AZURE")  # Ej: mcpserver.database.windows.net

    # 💾 Primer intento con el que te sirvió para migraciones
    logger.info("🔌 Intentando conexión a Azure SQL con params_migrations...")

    params_migrations = (
        f"DRIVER={{ODBC Driver 18 for SQL Server}};"
        f"SERVER=tcp:{ROOT_AZURE};"
        f"DATABASE={BASE_AZURE};"
        f"UID={USER_AZURE};"
        f"PWD={USER_PASS};"
        "Encrypt=yes;"
        "TrustServerCertificate=no;"
        "Connection Timeout=30;"
        "Login Timeout=30;"
        # Configuraciones adicionales para estabilidad
        "MultipleActiveResultSets=False;"  # Evita problemas con cursores múltiples
        "Mars_Connection=no;"
        "APP=FlaskBackend;"
        )
    params_migrations = urllib.parse.quote_plus(params_migrations)
        
    engine = create_engine(
        f"mssql+pyodbc:///?odbc_connect={params_migrations}",
       pool_pre_ping=True,           # Verifica conexión antes de usar (CRÍTICO)
        pool_recycle=1800,            # Recicla cada 30 min (Azure timeout ~30-40 min)
        pool_size=5,                  # Conexiones permanentes en el pool
        max_overflow=10,              # Conexiones adicionales si es necesario
        pool_timeout=30,              # Timeout para obtener conexión del pool
        
        # Configuración de echo para debugging (cambiar a False en producción)
        echo=False,                   # Cambia a True solo para debug
        echo_pool=False,              # Logs detallados del pool (solo debug)
        
        # Importante para manejo de transacciones
        isolation_level="READ COMMITTED",  # Nivel de aislamiento estándar
        
        # Configuración adicional para manejar desconexiones
        connect_args={
            'timeout': 30,
            'check_same_thread': False,  # Para multithreading
        }
    )
    
    # Event listener para manejar reconexiones y errores
    @event.listens_for(engine, "connect")
    def receive_connect(dbapi_conn, connection_record):
        """Se ejecuta cuando se crea una nueva conexión"""
        logger.debug(f"🔗 Nueva conexión establecida: {id(dbapi_conn)}")
        
        # Configurar propiedades de la conexión para Azure
        cursor = dbapi_conn.cursor()
        try:
            # Timeout para queries lentas (30 segundos)
            cursor.execute("SET LOCK_TIMEOUT 30000")
            # Configurar formato de fecha estándar
            cursor.execute("SET DATEFORMAT ymd")
            cursor.close()
        except Exception as e:
            logger.warning(f"⚠️ No se pudieron configurar propiedades de conexión: {e}")
    
    @event.listens_for(engine, "checkout")
    def receive_checkout(dbapi_conn, connection_record, connection_proxy):
        """Se ejecuta cuando una conexión sale del pool"""
        logger.debug(f"📤 Conexión obtenida del pool: {id(dbapi_conn)}")
    
    @event.listens_for(engine, "checkin")
    def receive_checkin(dbapi_conn, connection_record):
        """Se ejecuta cuando una conexión regresa al pool"""
        logger.debug(f"📥 Conexión devuelta al pool: {id(dbapi_conn)}")
    
    
    @event.listens_for(engine, "handle_error")
    def handle_error(context):
        """Maneja errores de conexión para logging detallado"""
        if isinstance(context.original_exception, exc.DBAPIError):
            logger.error(f"Error de BD: {context.original_exception}")
            
            # Detectar errores de conexión específicos
            error_msg = str(context.original_exception).lower()
            if any(keyword in error_msg for keyword in [
                'connection', 'timeout', 'broken', 'lost', 
                'closed', 'invalid', 'disconnected'
            ]):
                logger.warning("🔄 Detectada desconexión - pool_pre_ping se encargará de reconectar")
    
    # Test de conexión inicial
    try: 
        logger.info("🧪 Verificando conexión inicial...")
        with engine.connect() as conn:
            result = conn.execute(text("SELECT @@VERSION AS version, DB_NAME() AS database_name"))
            row = result.fetchone()
            logger.info(f"Conexión exitosa a Azure SQL Database")
            logger.info(f"Base de datos: {row.database_name}")
            logger.debug(f"Versión: {row.version[:50]}...")  # Primeros 50 chars
            
        logger.info(f"⚙️  Pool configurado: size={engine.pool.size()}, overflow={engine.pool.overflow()}")
        return engine
        
    except Exception as e1:
        logger.error(f"Error fatal al conectar con Azure SQL Database")
        logger.error(f"Detalles: {str(e1)}")
        logger.error(f"📍 Servidor: {ROOT_AZURE}")
        logger.error(f"📍 Base de datos: {BASE_AZURE}")
        logger.error(f"📍 Usuario: {USER_AZURE}")
        raise
    
def test_connection_health(engine):
    """
    Función auxiliar para verificar la salud de la conexión.
    Úsala en un endpoint /health de tu API.
    """
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT 
                    DB_NAME() AS database_name,
                    GETDATE() AS server_time,
                    @@SPID AS session_id
            """))
            row = result.fetchone()
            return {
                'status': 'healthy',
                'database': row.database_name,
                'server_time': str(row.server_time),
                'session_id': row.session_id
            }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            'status': 'unhealthy',
            'error': str(e)
        }


def get_pool_stats(engine):
    """
    Función auxiliar para monitorear el estado del pool.
    Útil para debugging y monitoreo.
    """
    pool = engine.pool
    return {
        'pool_size': pool.size(),
        'checked_in': pool.checkedin(),
        'checked_out': pool.checkedout(),
        'overflow': pool.overflow(),
        'total_connections': pool.size() + pool.overflow()
    }
