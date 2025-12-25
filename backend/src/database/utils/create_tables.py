"""
Script para crear tablas desde models.py en todas las bases de datos disponibles.

GUIA DE USO:
============

1. CREAR TABLAS EN TODAS LAS BASES DE DATOS:
   python create_tables.py --all
   
   Esto creara las tablas definidas en models.py en Windows, Linux y Azure
   (solo en las que esten disponibles)

2. CREAR TABLAS EN UNA BASE ESPECIFICA:
   python create_tables.py --database windows
   python create_tables.py --database linux
   python create_tables.py --database azure

3. VERIFICAR TABLAS EXISTENTES (sin crear):
   python create_tables.py --check

4. RECREAR TABLAS (BORRA TODO):
   python create_tables.py --all --drop
   CUIDADO: Esto eliminara todos los datos existentes

FLUJO RECOMENDADO:
==================

PASO 1: Crear tablas en Windows (desarrollo)
   python create_tables.py --database windows

PASO 2: Verificar que se crearon correctamente
   python create_tables.py --check

PASO 3: Crear tablas en Linux y Azure
   python create_tables.py --database linux
   python create_tables.py --database azure

PASO 4: Sincronizar datos desde Windows a las demas
   cd ../utils
   python auto_sync.py --source windows

NOTAS IMPORTANTES:
==================
- La sincronizacion solo transfiere DATOS, no estructura de tablas
- Primero debes crear las tablas con este script
- Luego puedes sincronizar los datos con auto_sync.py
- Las tablas deben existir en origen Y destino para sincronizar
"""

import os
import sys
from pathlib import Path

# Agregar el directorio raiz al path
root_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(root_dir))

from sqlalchemy import inspect, MetaData
from src.database.config.mysql_config import get_mysql_engine
from src.database.config.azure_config import get_azure_engine
from src.database.config.database_linux_config import get_mysql_linux_engine
from src.config.logging_config import get_logger

logger = get_logger("backend.create_tables")

# Importar db de Flask-SQLAlchemy
try:
    from extensions import db
    USE_FLASK_DB = True
    logger.info("Usando Flask-SQLAlchemy (db.Model)")
except ImportError:
    logger.warning("No se encontro Flask-SQLAlchemy, usando SQLAlchemy puro")
    USE_FLASK_DB = False


class TableCreator:
    """Gestor de creacion de tablas en multiples bases de datos"""
    
    def __init__(self):
        self.databases = {
            'windows': None,
            'linux': None,
            'azure': None
        }
        self.available_databases = []
    
    def connect_databases(self):
        """Conecta a todas las bases de datos disponibles"""
        logger.info("Conectando a bases de datos...")
        
        # Windows
        try:
            self.databases['windows'] = get_mysql_engine()
            self.available_databases.append('windows')
            logger.info("Windows disponible")
        except Exception as e:
            logger.warning(f"Windows no disponible: {str(e)[:100]}")
        
        # Linux
        try:
            self.databases['linux'] = get_mysql_linux_engine()
            self.available_databases.append('linux')
            logger.info("Linux disponible")
        except Exception as e:
            logger.warning(f"Linux no disponible: {str(e)[:100]}")
        
        # Azure
        try:
            self.databases['azure'] = get_azure_engine()
            self.available_databases.append('azure')
            logger.info("Azure disponible")
        except Exception as e:
            logger.warning(f"Azure no disponible: {str(e)[:100]}")
        
        logger.info(f"Bases de datos disponibles: {', '.join(self.available_databases)}")
        return len(self.available_databases)
    
    def get_existing_tables(self, db_name):
        """Obtiene lista de tablas existentes"""
        engine = self.databases.get(db_name)
        if not engine:
            return []
        
        try:
            inspector = inspect(engine)
            return inspector.get_table_names()
        except Exception as e:
            logger.error(f"Error obteniendo tablas de {db_name}: {str(e)[:100]}")
            return []
    
    def get_model_tables(self):
        """Obtiene lista de tablas definidas en models.py"""
        if USE_FLASK_DB:
            # Flask-SQLAlchemy: Importar modelos para registrarlos
            import src.database.models.models  # Esto registra los modelos
            return [table.name for table in db.metadata.sorted_tables]
        else:
            # SQLAlchemy puro
            from src.database.models.models import Base
            return [table.name for table in Base.metadata.sorted_tables]
    
    def create_tables(self, db_name, drop_first=False):
        """Crea tablas en una base de datos especifica"""
        engine = self.databases.get(db_name)
        if not engine:
            logger.error(f"Base de datos {db_name} no disponible")
            return False
        
        try:
            logger.info(f"Creando tablas en {db_name}...")
            
            if USE_FLASK_DB:
                # Flask-SQLAlchemy: Importar modelos para registrarlos
                import src.database.models.models
                metadata = db.metadata
            else:
                # SQLAlchemy puro
                from src.database.models.models import Base
                metadata = Base.metadata
            
            if drop_first:
                logger.warning(f"ELIMINANDO TODAS LAS TABLAS EN {db_name}")
                metadata.drop_all(bind=engine)
            
            # Crear todas las tablas
            metadata.create_all(bind=engine)
            
            # Verificar tablas creadas
            tables = self.get_existing_tables(db_name)
            model_tables = self.get_model_tables()
            
            logger.info(f"Tablas creadas en {db_name}: {', '.join(tables) if tables else 'ninguna'}")
            logger.info(f"Tablas esperadas: {', '.join(model_tables)}")
            
            # Verificar que todas las tablas del modelo existan
            if model_tables:
                missing = set(model_tables) - set(tables)
                if missing:
                    logger.warning(f"Tablas faltantes en {db_name}: {', '.join(missing)}")
                    return False
            
            logger.info(f"Tablas creadas exitosamente en {db_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error creando tablas en {db_name}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def create_all_tables(self, drop_first=False):
        """Crea tablas en todas las bases de datos disponibles"""
        logger.info("Creando tablas en todas las bases de datos disponibles...")
        
        results = {}
        for db_name in self.available_databases:
            success = self.create_tables(db_name, drop_first)
            results[db_name] = success
        
        return results
    
    def check_tables_status(self):
        """Verifica estado de tablas en todas las bases de datos"""
        print("\n" + "="*70)
        print(" ESTADO DE TABLAS EN BASES DE DATOS")
        print("="*70)
        
        model_tables = self.get_model_tables()
        if model_tables:
            print(f"\nTablas definidas en models.py ({len(model_tables)}): {', '.join(model_tables)}")
        else:
            print("\nADVERTENCIA: No se detectaron tablas en models.py")
            print("Verifica que los modelos esten importados correctamente")
        
        for db_name in ['windows', 'linux', 'azure']:
            print(f"\n{db_name.upper()}:")
            
            if db_name not in self.available_databases:
                print("  Estado: NO DISPONIBLE")
                continue
            
            existing_tables = self.get_existing_tables(db_name)
            
            if not existing_tables:
                print("  Estado: CONECTADO PERO SIN TABLAS")
                continue
            
            print(f"  Estado: DISPONIBLE")
            print(f"  Tablas existentes ({len(existing_tables)}): {', '.join(existing_tables)}")
            
            if model_tables:
                print(f"  Comparacion con models.py:")
                for table in model_tables:
                    status = "OK" if table in existing_tables else "FALTA"
                    symbol = "[✓]" if table in existing_tables else "[✗]"
                    print(f"    {symbol} {table}: {status}")
        
        print("\n" + "="*70)


def main():
    """Funcion principal CLI"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Crear tablas desde models.py en bases de datos',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  python create_tables.py --all              # Crear en todas las BD disponibles
  python create_tables.py --database windows # Crear solo en Windows
  python create_tables.py --check            # Verificar estado
  python create_tables.py --all --drop       # CUIDADO: Recrear todo
        """
    )
    
    parser.add_argument('--all', action='store_true', 
                       help='Crear tablas en todas las bases de datos disponibles')
    parser.add_argument('--database', choices=['windows', 'linux', 'azure'],
                       help='Crear tablas en una base de datos especifica')
    parser.add_argument('--check', action='store_true',
                       help='Solo verificar estado de tablas sin crear')
    parser.add_argument('--drop', action='store_true',
                       help='CUIDADO: Eliminar tablas existentes antes de crear')
    
    args = parser.parse_args()
    
    # Crear instancia
    creator = TableCreator()
    
    # Conectar bases de datos
    available = creator.connect_databases()
    
    if available == 0:
        logger.error("No hay bases de datos disponibles")
        return 1
    
    # Solo verificar estado
    if args.check:
        creator.check_tables_status()
        return 0
    
    # Confirmar si se va a eliminar
    if args.drop:
        confirm = input("\n¿SEGURO que deseas ELIMINAR todas las tablas? (escribe 'SI'): ")
        if confirm != 'SI':
            print("Operacion cancelada")
            return 0
    
    # Crear tablas
    if args.all:
        results = creator.create_all_tables(drop_first=args.drop)
        
        print("\n" + "="*70)
        print(" RESULTADO DE CREACION DE TABLAS")
        print("="*70)
        for db_name, success in results.items():
            status = "EXITOSO" if success else "FALLIDO"
            print(f"{db_name}: {status}")
        print("="*70)
        
        # Mostrar estado final
        creator.check_tables_status()
        
        return 0 if all(results.values()) else 1
    
    elif args.database:
        success = creator.create_tables(args.database, drop_first=args.drop)
        
        if success:
            print(f"\nTablas creadas exitosamente en {args.database}")
            creator.check_tables_status()
            return 0
        else:
            print(f"\nError creando tablas en {args.database}")
            return 1
    
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())