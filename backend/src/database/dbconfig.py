# Importamos librerias 
from sqlalchemy import create_engine
from mysql.connector import Error 
from dotenv import load_dotenv
import mysql.connector
from json import load
import os 

load_dotenv()
# Credenciales
HOST_DB = os.getenv("ROOT_BD")
USER_DB = os.getenv("USER_BD")
PASS_DB = os.getenv("PASS_BD")
NAME_DB = os.getenv("NAME_BD")

def BD_connection(host, user_db, user_pass, name_db):
    connection = None
    try:
        connection = mysql.connector.connect(
            host=host,
            user=user_db,
            passwd=user_pass,
            database=name_db,
            port=3306,
            connection_timeout=300
        )
        print("MYSQL DATABASE connection succesful")
    except Error as err:
        print(f"Error: '{err}'")
    return connection

connection = BD_connection(HOST_DB, USER_DB, PASS_DB, NAME_DB)

# verifiquemos la conexion realizando una consulta simple
if connection:
    cursor = connection.cursor()
    cursor.execute("SELECT DATABASE()")
    db = cursor.fetchone()
    print(f"Conectado a la base de datos: {db[0]}")
    
    
def crear_tablas(connection):
    cursor = connection.cursor()

    # Crear tabla `chat`
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat (
            id VARCHAR(64) PRIMARY KEY,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            summary TEXT
        )
    """)

    # Crear tabla `message`
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS message (
            id INT AUTO_INCREMENT PRIMARY KEY,
            chat_id VARCHAR(64),
            role VARCHAR(16) NOT NULL,
            content TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (chat_id) REFERENCES chat(id) ON DELETE CASCADE
        )
    """)

    connection.commit()
    print("Tablas creadas (si no existían ya)")

# Llama la función para crearlas
crear_tablas(connection)


# Funcion para obtener las tablas disponibles
def show_tables(connection):
    cursor = connection.cursor()
    cursor.execute("SHOW TABLES")
    tables = cursor.fetchall()
    for table in tables:
        print(table)

connection = BD_connection(HOST_DB, USER_DB, PASS_DB, NAME_DB)
show_tables(connection)


# Funcion para describir la estructura de una tabla
def describe_table(connection, table_name):
    cursor = connection.cursor()
    query = f"DESCRIBE {table_name}"
    cursor.execute(query)
    columns = cursor.fetchall()
    for column in columns:
        print(column)
        
describe_table(connection, 'chat')

#describe_table(connection, 'message')