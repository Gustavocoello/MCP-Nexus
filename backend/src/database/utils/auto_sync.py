# src.database.utils.auto_sync.py
"""
Script de sincronización automática entre bases de datos.
Puede ejecutarse como cron job o tarea programada.
"""

"""
Script de sincronizacion automatica entre bases de datos.
Puede ejecutarse como cron job o tarea programada.

GUIA DE USO:
============

1. SINCRONIZACION AUTOMATICA (uso principal):
   python auto_sync.py
   
   Por defecto sincroniza desde Windows a todas las demas
   Respeta la variable ENV (dev/prod)

2. SINCRONIZAR DESDE BASE ESPECIFICA:
   python auto_sync.py --source windows
   python auto_sync.py --source linux
   python auto_sync.py --source azure

3. VER HISTORIAL DE SINCRONIZACIONES:
   python auto_sync.py --history
   
   Muestra ultimas 10 sincronizaciones con:
   - Fecha y hora
   - Origen y destinos
   - Duracion
   - Estado (OK/FAIL)

4. VER ESTADO ACTUAL (sin sincronizar):
   python auto_sync.py --status
   
   Muestra tamaños y estado de todas las BD

PROGRAMAR SINCRONIZACION AUTOMATICA:
=====================================

LINUX/MAC (crontab):
  # Editar crontab
  crontab -e
  
  # Sincronizar cada 6 horas
  0 */6 * * * cd /ruta/proyecto && python src/database/utils/auto_sync.py
  
  # Sincronizar cada dia a las 2 AM
  0 2 * * * cd /ruta/proyecto && python src/database/utils/auto_sync.py
  
  # Ver logs
  0 */6 * * * cd /ruta/proyecto && python src/database/utils/auto_sync.py >> sync.log 2>&1

WINDOWS (Task Scheduler):
  # PowerShell como administrador
  schtasks /create /tn "DB Sync" /tr "python C:\ruta\auto_sync.py" /sc hourly /mo 6
  
  # O usar interfaz grafica:
  1. Abrir "Programador de tareas"
  2. Crear tarea basica
  3. Trigger: Diario/Por horas
  4. Accion: Iniciar programa
  5. Programa: python
  6. Argumentos: C:\ruta\auto_sync.py

INTEGRACION CON FLASK/API:
===========================

# En tu app.py:
from src.database.utils.auto_sync import AutoSync

@app.route('/admin/sync', methods=['POST'])
def trigger_sync():
    auto_sync = AutoSync()
    success = auto_sync.run_sync(source='windows')
    return {'success': success}

@app.route('/admin/sync-history', methods=['GET'])
def sync_history():
    auto_sync = AutoSync()
    history = auto_sync.load_history()
    return {'history': history[-10:]}

FLUJO RECOMENDADO:
==================

1. Crear tablas primero:
   python create_tables.py --all

2. Verificar tablas:
   python create_tables.py --check

3. Sincronizar datos:
   python auto_sync.py --source windows

4. Programar sincronizacion automatica:
   Agregar a crontab o Task Scheduler

5. Monitorear:
   python auto_sync.py --history

NOTAS:
======
- El historial se guarda en sync_history.json
- Mantiene ultimos 50 registros
- Requiere que las tablas ya existan
- No sincroniza estructura, solo datos
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

# Agregar el directorio raíz al path
root_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(root_dir))

from src.database.utils.database_sync import DatabaseSync
from src.config.logging_config import get_logger

logger = get_logger("backend.auto_sync")

class AutoSync:
    """Sincronización automática con registro de historial"""
    
    def __init__(self, log_file='sync_history.json'):
        self.log_file = Path(__file__).parent / log_file
        self.sync_manager = DatabaseSync()
        
    def load_history(self):
        """Carga historial de sincronizaciones"""
        if self.log_file.exists():
            with open(self.log_file, 'r') as f:
                return json.load(f)
        return []
    
    def save_history(self, record):
        """Guarda registro de sincronización"""
        history = self.load_history()
        history.append(record)
        
        # Mantener solo últimos 50 registros
        history = history[-50:]
        
        with open(self.log_file, 'w') as f:
            json.dump(history, f, indent=2)
    
    def run_sync(self, source='windows', targets=None):
        """Ejecuta sincronización y registra resultado"""
        start_time = datetime.now()
        
        logger.info("="*70)
        logger.info(f"Inicio de sincronización automática: {start_time}")
        logger.info("="*70)
        
        # Conectar bases de datos
        available = self.sync_manager.connect_databases()
        
        if available == 0:
            logger.error("No hay bases de datos disponibles")
            return False
        
        # Mostrar estado inicial
        logger.info("Estado inicial:")
        for db in self.sync_manager.available_databases:
            size = self.sync_manager.get_database_size(db)
            logger.info(f"  {db}: {size} MB")
        
        # Determinar targets
        if not targets:
            targets = [db for db in self.sync_manager.available_databases if db != source]
        
        # Ejecutar sincronización
        results = {}
        for target in targets:
            logger.info(f"\nSincronizando {source} -> {target}")
            success = self.sync_manager.sync_database(source, target)
            results[target] = success
        
        # Mostrar estado final
        logger.info("\nEstado final:")
        for db in self.sync_manager.available_databases:
            size = self.sync_manager.get_database_size(db)
            logger.info(f"  {db}: {size} MB")
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Registrar en historial
        record = {
            'timestamp': start_time.isoformat(),
            'source': source,
            'targets': list(results.keys()),
            'success': all(results.values()),
            'duration_seconds': duration,
            'available_databases': self.sync_manager.available_databases
        }
        
        self.save_history(record)
        
        logger.info("="*70)
        logger.info(f"Sincronización completada en {duration:.2f}s")
        logger.info(f"Resultado: {'EXITOSO' if record['success'] else 'FALLIDO'}")
        logger.info("="*70)
        
        return record['success']
    
    def print_history(self, limit=10):
        """Muestra historial de sincronizaciones"""
        history = self.load_history()
        
        print("\n" + "="*70)
        print(f" HISTORIAL DE SINCRONIZACIONES (últimas {limit})")
        print("="*70)
        
        if not history:
            print("\nNo hay registros de sincronización")
            return
        
        for record in history[-limit:]:
            timestamp = datetime.fromisoformat(record['timestamp'])
            status = "OK" if record['success'] else "FAIL"
            
            print(f"\n[{status}] {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"  Source: {record['source']}")
            print(f"  Targets: {', '.join(record['targets'])}")
            print(f"  Duration: {record['duration_seconds']:.2f}s")
            print(f"  Available: {', '.join(record['available_databases'])}")
        
        print("\n" + "="*70)


def main():
    """Función principal para uso en cron/scheduler"""
    auto_sync = AutoSync()
    
    # Obtener configuración del entorno
    env = os.getenv('ENV', 'dev').lower()
    
    if env == 'prod':
        # En producción: sincronizar desde Windows (principal)
        logger.info("Modo PROD: Sincronizando desde Windows")
        source = 'windows'
    else:
        # En desarrollo: sincronizar desde Windows
        logger.info("Modo DEV: Sincronizando desde Windows")
        source = 'windows'
    
    # Ejecutar sincronización
    success = auto_sync.run_sync(source=source)
    
    return 0 if success else 1


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Sincronización automática de bases de datos')
    parser.add_argument('--source', default='windows', help='Base de datos fuente')
    parser.add_argument('--history', action='store_true', help='Mostrar historial')
    parser.add_argument('--status', action='store_true', help='Mostrar solo estado')
    
    args = parser.parse_args()
    
    auto_sync = AutoSync()
    
    if args.history:
        auto_sync.print_history()
    elif args.status:
        auto_sync.sync_manager.connect_databases()
        auto_sync.sync_manager.print_status()
    else:
        success = auto_sync.run_sync(source=args.source)
        sys.exit(0 if success else 1)