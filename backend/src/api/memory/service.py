from src.database.models.models import UserMemory, MemoryType
from extensions import db

def get_user_memory(chat_id, memory_type=None):
    query = UserMemory.query.filter_by(chat_id=chat_id)
    if memory_type:
        query = query.filter_by(type=memory_type)
    return query.all()

# Nueva función save_memory con prioridad
def save_memory(chat_id, key, value, memory_type=MemoryType.LONG_TERM, priority=5):
    record = UserMemory.query.filter_by(chat_id=chat_id, key=key).first()
    if record:
        record.value = value
        record.type = memory_type
        record.priority = priority
    else:
        record = UserMemory(
            chat_id=chat_id,
            key=key,
            value=value,
            type=memory_type,
            priority=priority
        )
        db.session.add(record)
        print(f"[SAVE] Guardando memoria: {key} -> {value} (Prioridad: {priority})")
    db.session.commit()