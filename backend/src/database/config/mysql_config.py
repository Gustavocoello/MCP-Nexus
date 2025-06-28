# src/database/config/mysql_config.py

import os
import mysql.connector
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from extensions import db  # Flask SQLAlchemy instance

load_dotenv()

# Configuración desde .env
HOST_DB = os.getenv("ROOT_BD")
USER_DB = os.getenv("USER_BD")
PASS_DB = os.getenv("PASS_BD")
NAME_DB = os.getenv("NAME_BD")

# Esta URL sirve para SQLAlchemy
MYSQL_URL = f"mysql+mysqlconnector://{USER_DB}:{PASS_DB}@{HOST_DB}:3306/{NAME_DB}"

# Esta URL sirve para conectarse sin especificar base para crearla si no existe
MYSQL_ROOT_URL = f"mysql+mysqlconnector://{USER_DB}:{PASS_DB}@{HOST_DB}:3306"

def create_database_if_not_exists():
    """Crea la base de datos si no existe."""
    try:
        conn = mysql.connector.connect(
            host=HOST_DB,
            user=USER_DB,
            passwd=PASS_DB
        )
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {NAME_DB}")
        print(f"Base de datos '{NAME_DB}' verificada o creada")
        conn.close()
    except mysql.connector.Error as err:
        print(f"Error al verificar/crear la base de datos: {err}")

def get_mysql_engine():
    """Devuelve el engine SQLAlchemy apuntando a la base específica"""
    return create_engine(MYSQL_URL)

def init_mysql():
    """Inicializa la base de datos y las tablas con Alembic ya listo"""
    create_database_if_not_exists()
    engine = get_mysql_engine()
    try:
        with engine.connect() as connection:
            print("✅ Conexión establecida con SQLAlchemy")
    except OperationalError as e:
        print(f"Error al conectar con SQLAlchemy: {e}")
    return engine
