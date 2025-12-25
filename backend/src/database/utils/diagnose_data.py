"""
Script para diagnosticar problemas de foreign keys y datos huerfanos.
"""

import os
import sys
from pathlib import Path

root_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(root_dir))

from sqlalchemy import text
from src.database.config.mysql_config import get_mysql_engine
from src.config.logging_config import get_logger

logger = get_logger("backend.diagnose")

def diagnose_orphaned_data():
    """Diagnostica datos huerfanos en Windows"""
    
    print("\n" + "="*70)
    print(" DIAGNOSTICO DE DATOS HUERFANOS EN WINDOWS")
    print("="*70)
    
    engine = get_mysql_engine()
    
    with engine.connect() as conn:
        # 1. Verificar user_ids en chat que no existen en users
        print("\n1. Chats con user_id inexistente:")
        result = conn.execute(text("""
            SELECT c.id, c.user_id, c.title
            FROM chat c
            LEFT JOIN users u ON c.user_id = u.id
            WHERE c.user_id IS NOT NULL AND u.id IS NULL
            LIMIT 10
        """))
        
        orphaned_chats = result.fetchall()
        if orphaned_chats:
            print(f"   Encontrados {len(orphaned_chats)} chats huerfanos:")
            for chat in orphaned_chats:
                print(f"   - Chat ID: {chat.id}, User ID: {chat.user_id}, Title: {chat.title}")
        else:
            print("   No hay chats huerfanos")
        
        # 2. Verificar chats con user_id NULL
        print("\n2. Chats con user_id NULL:")
        result = conn.execute(text("""
            SELECT COUNT(*) as count FROM chat WHERE user_id IS NULL
        """))
        null_chats = result.fetchone().count
        print(f"   Encontrados {null_chats} chats sin user_id")
        
        # 3. Verificar messages huerfanos
        print("\n3. Messages con chat_id inexistente:")
        result = conn.execute(text("""
            SELECT m.id, m.chat_id
            FROM message m
            LEFT JOIN chat c ON m.chat_id = c.id
            WHERE c.id IS NULL
            LIMIT 10
        """))
        
        orphaned_messages = result.fetchall()
        if orphaned_messages:
            print(f"   Encontrados {len(orphaned_messages)} mensajes huerfanos:")
            for msg in orphaned_messages[:5]:
                print(f"   - Message ID: {msg.id}, Chat ID: {msg.chat_id}")
        else:
            print("   No hay mensajes huerfanos")
        
        # 4. Verificar user_memory huerfanos
        print("\n4. User_memory con chat_id inexistente:")
        result = conn.execute(text("""
            SELECT um.id, um.chat_id
            FROM user_memory um
            LEFT JOIN chat c ON um.chat_id = c.id
            WHERE c.id IS NULL
            LIMIT 10
        """))
        
        orphaned_memory = result.fetchall()
        if orphaned_memory:
            print(f"   Encontrados {len(orphaned_memory)} memorias huerfanas")
        else:
            print("   No hay memorias huerfanas")
        
        # 5. Verificar user_tokens huerfanos
        print("\n5. User_tokens con user_id inexistente:")
        result = conn.execute(text("""
            SELECT ut.id, ut.user_id, ut.provider
            FROM user_token ut
            LEFT JOIN users u ON ut.user_id = u.id
            WHERE u.id IS NULL
            LIMIT 10
        """))
        
        orphaned_tokens = result.fetchall()
        if orphaned_tokens:
            print(f"   Encontrados {len(orphaned_tokens)} tokens huerfanos")
        else:
            print("   No hay tokens huerfanos")
        
        # 6. Listar todos los user_ids unicos en chat
        print("\n6. User IDs unicos en chat:")
        result = conn.execute(text("""
            SELECT DISTINCT user_id FROM chat WHERE user_id IS NOT NULL
        """))
        chat_user_ids = [row.user_id for row in result.fetchall()]
        
        # Verificar cuales existen en users
        result = conn.execute(text("""
            SELECT id FROM users
        """))
        existing_user_ids = [row.id for row in result.fetchall()]
        
        missing_user_ids = set(chat_user_ids) - set(existing_user_ids)
        
        print(f"   User IDs en chat: {len(chat_user_ids)}")
        print(f"   User IDs en users: {len(existing_user_ids)}")
        print(f"   User IDs faltantes: {len(missing_user_ids)}")
        
        if missing_user_ids:
            print(f"   IDs faltantes: {list(missing_user_ids)[:10]}")
    
    print("\n" + "="*70)

def clean_orphaned_data():
    """Limpia datos huerfanos - CUIDADO: ELIMINA DATOS"""
    
    print("\n" + "="*70)
    print(" LIMPIEZA DE DATOS HUERFANOS")
    print("="*70)
    
    confirm = input("\nEsto eliminara datos huerfanos. Escribe 'SI' para confirmar: ")
    if confirm != 'SI':
        print("Operacion cancelada")
        return
    
    engine = get_mysql_engine()
    
    with engine.connect() as conn:
        # 1. Eliminar chats huerfanos
        result = conn.execute(text("""
            DELETE c FROM chat c
            LEFT JOIN users u ON c.user_id = u.id
            WHERE c.user_id IS NOT NULL AND u.id IS NULL
        """))
        conn.commit()
        print(f"Chats huerfanos eliminados: {result.rowcount}")
        
        # 2. Eliminar mensajes huerfanos
        result = conn.execute(text("""
            DELETE m FROM message m
            LEFT JOIN chat c ON m.chat_id = c.id
            WHERE c.id IS NULL
        """))
        conn.commit()
        print(f"Mensajes huerfanos eliminados: {result.rowcount}")
        
        # 3. Eliminar memorias huerfanas
        result = conn.execute(text("""
            DELETE um FROM user_memory um
            LEFT JOIN chat c ON um.chat_id = c.id
            WHERE c.id IS NULL
        """))
        conn.commit()
        print(f"Memorias huerfanas eliminadas: {result.rowcount}")
        
        # 4. Eliminar tokens huerfanos
        result = conn.execute(text("""
            DELETE ut FROM user_token ut
            LEFT JOIN users u ON ut.user_id = u.id
            WHERE u.id IS NULL
        """))
        conn.commit()
        print(f"Tokens huerfanos eliminados: {result.rowcount}")
    
    print("\nLimpieza completada")
    print("="*70)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Diagnosticar datos huerfanos')
    parser.add_argument('--clean', action='store_true', help='Limpiar datos huerfanos')
    
    args = parser.parse_args()
    
    if args.clean:
        clean_orphaned_data()
    else:
        diagnose_orphaned_data()