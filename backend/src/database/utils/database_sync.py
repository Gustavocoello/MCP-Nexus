import os
import sys
import time
from pathlib import Path
from datetime import datetime
from sqlalchemy import text, inspect, MetaData
from sqlalchemy.exc import OperationalError

# Agregar el directorio raiz al path
root_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(root_dir))

from src.config.logging_config import get_logger
from src.database.config.mysql_config import get_mysql_engine
from src.database.config.azure_config import get_azure_engine
from src.database.config.database_linux_config import get_mysql_linux_engine

logger = get_logger("backend.sync")

# EJEMPLO DE USO EN CODIGO:
# ==========================
#
# from src.database.utils.database_sync import DatabaseSync
#
# # Crear instancia
# sync = DatabaseSync()
# sync.connect_databases()
#
# # Ver estado
# sync.print_status()
#
# # Sincronizar Windows -> Linux
# sync.sync_database('windows', 'linux')
#
# # Sincronizar Windows -> Todas
# sync.sync_all('windows')

class DatabaseSync:
    """Gestor de sincronización entre bases de datos"""
    
    def __init__(self):
        self.databases = {
            'windows': None,
            'linux': None,
            'azure': None
        }
        self.available_databases = []
        
    def connect_databases(self):
        """Conecta a todas las bases de datos disponibles"""
        logger.info("Conectando a bases de datos disponibles...")
        
        # Windows
        try:
            self.databases['windows'] = get_mysql_engine()
            self.available_databases.append('windows')
            logger.info("Windows conectado")
        except Exception as e:
            logger.warning(f"Windows no disponible: {str(e)[:100]}")
        
        # Linux
        try:
            self.databases['linux'] = get_mysql_linux_engine()
            self.available_databases.append('linux')
            logger.info("Linux conectado")
        except Exception as e:
            logger.warning(f"Linux no disponible: {str(e)[:100]}")
        
        # Azure
        try:
            self.databases['azure'] = get_azure_engine()
            self.available_databases.append('azure')
            logger.info("Azure conectado")
        except Exception as e:
            logger.warning(f"Azure no disponible: {str(e)[:100]}")
        
        logger.info(f"Bases de datos disponibles: {', '.join(self.available_databases)}")
        return len(self.available_databases)
    
    def get_database_size(self, db_name):
        """Obtiene el tamaño de la base de datos en MB"""
        engine = self.databases.get(db_name)
        if not engine:
            return None
        
        try:
            with engine.connect() as conn:
                if db_name == 'azure':
                    # Azure SQL Server
                    query = text("""
                        SELECT 
                            SUM(reserved_page_count) * 8.0 / 1024 AS size_mb
                        FROM sys.dm_db_partition_stats
                    """)
                else:
                    # MySQL
                    db_name_env = os.getenv("NAME_BD") if db_name == 'windows' else os.getenv("LINUX_NAME")
                    query = text(f"""
                        SELECT 
                            SUM(data_length + index_length) / 1024 / 1024 AS size_mb
                        FROM information_schema.TABLES
                        WHERE table_schema = '{db_name_env}'
                    """)
                
                result = conn.execute(query)
                row = result.fetchone()
                size_mb = row[0] if row[0] else 0
                return round(size_mb, 2)
                
        except Exception as e:
            logger.error(f"Error obteniendo tamaño de {db_name}: {str(e)[:100]}")
            return None
    
    def get_table_row_count(self, db_name, table_name):
        """Obtiene el conteo de filas de una tabla"""
        engine = self.databases.get(db_name)
        if not engine:
            return None
        
        try:
            with engine.connect() as conn:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                return result.fetchone()[0]
        except Exception as e:
            logger.warning(f"Error contando filas en {table_name} ({db_name}): {str(e)[:50]}")
            return None
    
    def get_tables_info(self, db_name):
        """Obtiene información de todas las tablas"""
        engine = self.databases.get(db_name)
        if not engine:
            return []
        
        try:
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            
            tables_info = []
            for table in tables:
                row_count = self.get_table_row_count(db_name, table)
                tables_info.append({
                    'name': table,
                    'rows': row_count
                })
            
            return tables_info
        except Exception as e:
            logger.error(f"Error obteniendo tablas de {db_name}: {str(e)[:100]}")
            return []
    
    def export_table_data(self, source_db, table_name):
        """Exporta datos de una tabla"""
        engine = self.databases.get(source_db)
        if not engine:
            return None
        
        try:
            with engine.connect() as conn:
                result = conn.execute(text(f"SELECT * FROM {table_name}"))
                columns = result.keys()
                rows = result.fetchall()
                
                return {
                    'columns': list(columns),
                    'rows': [dict(zip(columns, row)) for row in rows]
                }
        except Exception as e:
            logger.error(f"Error exportando {table_name} desde {source_db}: {str(e)[:100]}")
            return None
    
    def import_table_data(self, target_db, table_name, data):
        """Importa datos a una tabla"""
        engine = self.databases.get(target_db)
        if not engine or not data:
            return False
        
        try:
            with engine.connect() as conn:
                # Limpiar tabla destino
                conn.execute(text(f"DELETE FROM {table_name}"))
                conn.commit()
                
                # Insertar datos
                if data['rows']:
                    columns = ', '.join(data['columns'])
                    placeholders = ', '.join([f":{col}" for col in data['columns']])
                    insert_query = text(f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})")
                    
                    for row in data['rows']:
                        conn.execute(insert_query, row)
                    
                    conn.commit()
                
                logger.info(f"Importados {len(data['rows'])} registros a {table_name} en {target_db}")
                return True
                
        except Exception as e:
            logger.error(f"Error importando a {table_name} en {target_db}: {str(e)[:100]}")
            return False
    
    def sync_database(self, source_db, target_db, tables=None):
        """Sincroniza desde source_db hacia target_db"""
        if source_db not in self.available_databases or target_db not in self.available_databases:
            logger.error(f"Base de datos no disponible: {source_db} o {target_db}")
            return False
        
        logger.info(f"Iniciando sincronización: {source_db} -> {target_db}")
        
        # Obtener tablas a sincronizar
        if not tables:
            tables_info = self.get_tables_info(source_db)
            all_tables = [t['name'] for t in tables_info]
            
            # Orden correcto para respetar foreign keys
            # Primero tablas sin dependencias, luego las que dependen
            ordered_tables = []
            
            # Definir orden manualmente basado en foreign keys
            table_order = [
                'users',           # Sin dependencias
                'chat',            # Depende de users
                'user_token',      # Depende de users
                'message',         # Depende de chat
                'user_memory',     # Depende de chat
                'documents'        # Depende de users
            ]
            
            # Agregar tablas en orden
            for table in table_order:
                if table in all_tables:
                    ordered_tables.append(table)
            
            # Agregar cualquier tabla que no este en el orden definido
            for table in all_tables:
                if table not in ordered_tables and table != 'alembic_version':
                    ordered_tables.append(table)
            
            tables = ordered_tables
        
        success_count = 0
        fail_count = 0
        
        for table in tables:
            # Saltar alembic_version (tabla de migraciones)
            if table == 'alembic_version':
                logger.info(f"Saltando tabla de sistema: {table}")
                continue
            
            logger.info(f"Sincronizando tabla: {table}")
            
            # Exportar datos
            data = self.export_table_data(source_db, table)
            if not data:
                fail_count += 1
                continue
            
            # Importar datos
            if self.import_table_data(target_db, table, data):
                success_count += 1
            else:
                fail_count += 1
        
        logger.info(f"Sincronización completada: {success_count} exitosas, {fail_count} fallidas")
        return fail_count == 0
    
    def sync_all(self, source='windows'):
        """Sincroniza desde source a todas las demás bases disponibles"""
        if source not in self.available_databases:
            logger.error(f"Base de datos fuente no disponible: {source}")
            return False
        
        logger.info(f"Sincronización completa desde {source}")
        
        targets = [db for db in self.available_databases if db != source]
        
        for target in targets:
            logger.info(f"Sincronizando a {target}...")
            self.sync_database(source, target)
        
        return True
    
    def print_status(self):
        """Imprime estado de todas las bases de datos"""
        print("\n" + "="*70)
        print(" ESTADO DE BASES DE DATOS")
        print("="*70)
        
        for db_name in ['windows', 'linux', 'azure']:
            if db_name in self.available_databases:
                size = self.get_database_size(db_name)
                size_str = f"{size} MB" if size else "N/A"
                
                print(f"\n{db_name.upper()}: DISPONIBLE")
                print(f"  Tamaño: {size_str}")
                
                tables_info = self.get_tables_info(db_name)
                if tables_info:
                    print(f"  Tablas ({len(tables_info)}):")
                    for table in tables_info:
                        print(f"    - {table['name']}: {table['rows']} registros")
            else:
                print(f"\n{db_name.upper()}: NO DISPONIBLE")
        
        print("\n" + "="*70)


def sync_databases_cli():
    """CLI para sincronización de bases de datos"""
    print("\n" + "="*70)
    print(" SINCRONIZADOR DE BASES DE DATOS")
    print("="*70)
    
    sync_manager = DatabaseSync()
    
    # Conectar bases de datos
    available = sync_manager.connect_databases()
    
    if available == 0:
        print("\nNo hay bases de datos disponibles para sincronizar")
        return
    
    # Mostrar estado actual
    sync_manager.print_status()
    
    # Menú de opciones
    print("\nOpciones:")
    print("1. Sincronizar Windows -> Todas")
    print("2. Sincronizar Linux -> Todas")
    print("3. Sincronizar específica")
    print("4. Solo mostrar estado")
    print("5. Salir")
    
    choice = input("\nSelecciona una opción: ").strip()
    
    if choice == '1':
        sync_manager.sync_all('windows')
        sync_manager.print_status()
    elif choice == '2':
        sync_manager.sync_all('linux')
        sync_manager.print_status()
    elif choice == '3':
        print("\nBases disponibles:", ', '.join(sync_manager.available_databases))
        source = input("Fuente: ").strip().lower()
        target = input("Destino: ").strip().lower()
        sync_manager.sync_database(source, target)
        sync_manager.print_status()
    elif choice == '4':
        print("\nEstado ya mostrado arriba")
    else:
        print("\nSaliendo...")


if __name__ == "__main__":
    sync_databases_cli()