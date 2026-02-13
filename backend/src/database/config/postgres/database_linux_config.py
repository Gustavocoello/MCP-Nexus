import os
import psycopg2
from sqlalchemy import text, create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError
from dotenv import load_dotenv

load_dotenv()

# Variables globales para reuso
DB_USER = os.getenv("POSTGRES_LINUX_USER")
DB_PASS = os.getenv("POSTGRES_LINUX_PASS")
DB_HOST = os.getenv("POSTGRES_LINUX_HOST")
DB_NAME = os.getenv("POSTGRES_LINUX_NAME")
DB_PORT = "5432"

def get_pg_engine():
    # URL para PostgreSQL
    PG_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    
    engine = create_engine(
        PG_URL,
        pool_size=5,           # Pequeño para no saturar tus 1GB de RAM
        max_overflow=10,        # Límite de conexiones extra
        pool_timeout=30,       # Tiempo máximo para esperar una conexión del pool antes de lanzar error
        pool_recycle=3600,     # Reinicia conexiones cada 60 min (ideal para Always On)
        pool_pre_ping=True,    # Verifica si la conexión sigue viva antes de usarla
        connect_args={
            "connect_timeout": 10
        }
    )
    
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print(f"🛠 Conexión a Postgres con linux({DB_NAME}) validada")
    except Exception as e:
        print(f"Error en get_pg_engine: {e}")
        raise e

    return engine

def create_database_if_not_exists():
    """En Postgres no existe 'IF NOT EXISTS' para DB, usamos lógica de conexión manual"""
    try:
        # Conectamos a la DB por defecto 'postgres' para poder crear la otra
        conn = psycopg2.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASS,
            dbname="postgres"
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Verificar si existe
        cursor.execute(f"SELECT 1 FROM pg_database WHERE datname = '{DB_NAME}'")
        exists = cursor.fetchone()
        
        if not exists:
            cursor.execute(f"CREATE DATABASE \"{DB_NAME}\"")
            print(f"Base de datos '{DB_NAME}' creada con éxito")
        else:
            print(f"Base de datos '{DB_NAME}' ya existe")
            
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error al verificar/crear DB: {e}")

def init_pg():
    create_database_if_not_exists()
    return get_pg_engine()

if __name__ == "__main__":
    print("🚀 Iniciando validación de base de datos...")
    try:
        # Esto dispara todo el proceso
        engine = init_pg()
        print("Todo listo: La base de datos está configurada y lista para Jarvis.")
    except Exception as e:
        print(f"Error fatal al iniciar: {e}")