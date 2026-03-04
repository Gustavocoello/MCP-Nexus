import os
import sys
from pathlib import Path
from .agent import LamarAgent

# --- Fix Paths ---
current_dir = Path(__file__).resolve().parent.parent.parent.parent
backend_dir = current_dir.parent.parent
sys.path.insert(0, str(backend_dir))

#from src.services.agent.lamar.agent import LamarAgent

def test_drive():
    print("--- 🤖 INICIANDO SESIÓN CON LAMAR ---")
    lamar = LamarAgent()
    
    # Prueba 1: Consulta de estado (Debería activar el Sentinel si no hay logs frescos)
    print("\n🔍 TEST 1: Consulta de Salud del Sistema")
    query_1 = "Lamar, check the system status. If logs are old, run a full health check on all 20+ providers."
    response_1 = lamar.run_task(query_1)
    print(f"\nRespuesta de Lamar:\n{response_1['output']}")

    print("\n" + "="*50 + "\n")

    # Prueba 2: Reporte de uso
    print("📊 TEST 2: Consulta de Consumo")
    query_2 = "Lamar, give me a summary of the token usage in the last 24 hours."
    response_2 = lamar.run_task(query_2)
    print(f"\nRespuesta de Lamar:\n{response_2['output']}")

if __name__ == "__main__":
    test_drive()