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

    # 🔹 Filtrar chats recientes
    chat_df = pd.read_sql(f"""
        SELECT * FROM chat
        WHERE updated_at >= '{formatted_date}'
    """, mysql_engine)

    if chat_df.empty:
        print("No hay chats actualizados en los últimos 15 días.")
        logger.info("No hay chats actualizados en los últimos 15 días.")
        return

    chat_ids = chat_df['id'].tolist()

    # 🔹 Mensajes vinculados
    msg_df = pd.read_sql(f"""
        SELECT * FROM message
        WHERE chat_id IN ({','.join(f"'{str(cid)}'" for cid in chat_ids)})
    """, mysql_engine)

    # 🔹 Memorias vinculadas
    mem_df = pd.read_sql(f"""
        SELECT * FROM user_memory
        WHERE chat_id IN ({','.join(f"'{cid}'" for cid in chat_ids)})
    """, mysql_engine)

    # 🔻 Sincronización a Azure
    existing_ids = pd.read_sql("SELECT id FROM chat", azure_engine)["id"].tolist()
    chat_df = chat_df[~chat_df["id"].isin(existing_ids)]

    if chat_df.empty:
        print("Todos los chats ya estaban sincronizados.")
        return

    chat_df.to_sql("chat", azure_engine, if_exists="append", index=False)
    print(f"{len(chat_df)} chats sincronizados")
    logger.info(f"{len(chat_df)} chats sincronizados")

    if not msg_df.empty:
        if "id" in msg_df.columns:
            msg_df.drop(columns=["id"], inplace=True)
        msg_df.to_sql("message", azure_engine, if_exists="append", index=False)
        print(f"{len(msg_df)} mensajes sincronizados")
        logger.info(f"{len(msg_df)} mensajes sincronizados")

    if not mem_df.empty:
        mem_df.to_sql("user_memory", azure_engine, if_exists="append", index=False)
        print(f"{len(mem_df)} memorias sincronizadas")
        logger.info(f"{len(mem_df)} memorias sincronizadas")

if __name__ == "__main__":
    sync_filtered_data()
