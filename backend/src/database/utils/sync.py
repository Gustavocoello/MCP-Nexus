# database/utils/sync.py
import sys
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta, timezone

# --- Fix Paths ---
current_dir = Path(__file__).resolve().parent
backend_dir = current_dir.parent.parent.parent
sys.path.insert(0, str(backend_dir))

from src.database.config.mysql_config import get_mysql_engine
from src.database.config.azure_config import get_azure_engine
from src.config.logging_config import get_logger

logger = get_logger('sync')

def sync_filtered_data():
    mysql_engine = get_mysql_engine()
    azure_engine = get_azure_engine()

    days_ago = datetime.now(timezone.utc) - timedelta(days=15)
    formatted_date = days_ago.strftime('%Y-%m-%d %H:%M:%S')

    # 1) Sincronizar usuarios nuevos
    user_df = pd.read_sql(f"SELECT * FROM user", mysql_engine)
    existing_user_ids = pd.read_sql("SELECT id FROM [user]", azure_engine)["id"].tolist()
    new_users = user_df[~user_df["id"].isin(existing_user_ids)]
    if not new_users.empty:
        new_users.to_sql("user", azure_engine, if_exists="append", index=False)
        print(f"{len(new_users)} usuarios sincronizados")
        logger.info(f"{len(new_users)} usuarios sincronizados")
    else:
        print("No hay usuarios nuevos para sincronizar")

    # 2) Sincronizar google_auth_token nuevos
    token_df = pd.read_sql(f"SELECT * FROM google_auth_token", mysql_engine)
    existing_token_ids = pd.read_sql("SELECT id FROM google_auth_token", azure_engine)["id"].tolist()
    new_tokens = token_df[~token_df["id"].isin(existing_token_ids)]
    if not new_tokens.empty:
        new_tokens.to_sql("google_auth_token", azure_engine, if_exists="append", index=False)
        print(f"{len(new_tokens)} tokens sincronizados")
        logger.info(f"{len(new_tokens)} tokens sincronizados")
    else:
        print("No hay tokens nuevos para sincronizar")

    # 3) Filtrar chats recientes y sincronizar
    chat_df = pd.read_sql(f"""
        SELECT * FROM chat
        WHERE updated_at >= '{formatted_date}'
    """, mysql_engine)

    if chat_df.empty:
        print("No hay chats actualizados en los últimos 15 días.")
        logger.info("No hay chats actualizados en los últimos 15 días.")
        return

    chat_ids = chat_df['id'].tolist()

    # Mensajes vinculados
    msg_df = pd.read_sql(f"""
        SELECT * FROM message
        WHERE chat_id IN ({','.join(f"'{str(cid)}'" for cid in chat_ids)})
    """, mysql_engine)

    # Memorias vinculadas
    mem_df = pd.read_sql(f"""
        SELECT * FROM user_memory
        WHERE chat_id IN ({','.join(f"'{cid}'" for cid in chat_ids)})
    """, mysql_engine)

    # Sincronizar chats nuevos (no duplicados)
    existing_chat_ids = pd.read_sql("SELECT id FROM chat", azure_engine)["id"].tolist()
    new_chats = chat_df[~chat_df["id"].isin(existing_chat_ids)]

    if not new_chats.empty:
        new_chats.to_sql("chat", azure_engine, if_exists="append", index=False)
        print(f"{len(new_chats)} chats sincronizados")
        logger.info(f"{len(new_chats)} chats sincronizados")
    else:
        print("Todos los chats ya estaban sincronizados")

    # Sincronizar mensajes vinculados
    if not msg_df.empty:
        # Quitar ids duplicados si existen
        if "id" in msg_df.columns:
            msg_df = msg_df.drop_duplicates(subset=["id"])
        msg_df = msg_df.drop(columns=["id"])
        msg_df.to_sql("message", azure_engine, if_exists="append", index=False)
        print(f"{len(msg_df)} mensajes sincronizados")
        logger.info(f"{len(msg_df)} mensajes sincronizados")

    # Sincronizar memorias vinculadas
    if not mem_df.empty:
        mem_df = mem_df.drop(columns=["id"])
        mem_df.to_sql("user_memory", azure_engine, if_exists="append", index=False)
        print(f"{len(mem_df)} memorias sincronizadas")
        logger.info(f"{len(mem_df)} memorias sincronizadas")

if __name__ == "__main__":
    sync_filtered_data()
