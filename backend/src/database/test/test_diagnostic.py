import os 
import sys
from pathlib import Path
from sqlalchemy import text

# Ajustar el path
current_dir = Path(__file__).resolve().parent
backend_dir = current_dir.parent.parent.parent.parent
sys.path.insert(0, str(backend_dir))


from src.database.config.mysql_config import get_mysql_engine as engine_windows
from src.database.config.database_linux_config import get_mysql_linux_engine as engine_linux
from src.database.config.azure_config import get_azure_engine

def probar_conexion(nombre, engine_func):
    print(f"🔍 Probando: {nombre}...")
    try:
        # Intentamos obtener el engine
        engine = engine_func()
        # Intentamos una consulta real
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            print(f"✅ {nombre}: CONECTADO EXITOSAMENTE")
            return True
    except Exception as e:
        print(f"❌ {nombre}: FALLÓ (Error: {str(e)[:100]}...)")
        return False

def ejecutar_diagnostico_total():
    print("\n" + "="*60)
    print("📊 REPORTE DE ESTADO DE TUS BASES DE DATOS")
    print("="*60)

    resultados = {}

    # 1. Probar Windows
    resultados["WINDOWS (Local)"] = probar_conexion("WINDOWS", engine_windows)
    
    print("-" * 30)

    # 2. Probar Linux
    resultados["LINUX (Servidor HP)"] = probar_conexion("LINUX", engine_linux)
    
    print("-" * 30)

    # 3. Probar Azure
    # Nota: Si aún no tienes Azure configurado, dará error esperado
    try:
        resultados["AZURE (Nube)"] = probar_conexion("AZURE", get_azure_engine)
    except:
        print("❌ AZURE: No configurado o error crítico en config.")
        resultados["AZURE (Nube)"] = False

    print("\n" + "="*60)
    print("RESUMEN FINAL:")
    for db, estado in resultados.items():
        status = "ONLINE 🟢" if estado else "OFFLINE 🔴"
        print(f"{db}: {status}")
    print("="*60 + "\n")

if __name__ == "__main__":
    ejecutar_diagnostico_total()