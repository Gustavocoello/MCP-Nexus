import os
import urllib.parse
from dotenv import load_dotenv
from sqlalchemy import create_engine
import urllib

load_dotenv()

AZURE_URL = os.getenv("AZURE_URL")
USER_AZURE = os.getenv("USER_BD_AZURE")
USER_PASS = os.getenv("PASS_BD_AZURE")
BASE_AZURE = os.getenv("NAME_BD_AZURE")
ROOT_AZURE = os.getenv("ROOT_BD_AZURE")




driver = "ODBC Driver 18 for SQL Server"
params = urllib.parse.quote_plus(
    "DRIVER={ODBC Driver 18 for SQL Server};"
    f"SERVER=tcp:{ROOT_AZURE};"
    f"DATABASE={BASE_AZURE};"
    f"UID={USER_AZURE};"
    f"PWD={urllib.parse.quote_plus(USER_PASS)};"
    "Encrypt=yes;"
    "TrustServerCertificate=no;"
    "Connection Timeout=30;"
)

connection_string = f"mssql+pyodbc:///?odbc_connect={params}"
engine = create_engine(connection_string)

def get_azure_engine():
    print("Conexión a Azure SQL establecida correctamente")
    return engine