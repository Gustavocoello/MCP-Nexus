from src.database.config.connection import SessionLocal
def get_user_memory(chat_id, memory_type=None):
    db_session = SessionLocal()
    query = db_session.query(UserMemory).filter_by(chat_id=chat_id)
    if memory_type:
        query = query.filter_by(type=memory_type)
    return query.all()

# Nueva función save_memory con prioridad
def save_memory(chat_id, key, value, memory_type=MemoryType.LONG_TERM, priority=5):
    db_session = SessionLocal()
    record = db_session.query(UserMemory).filter_by(chat_id=chat_id, key=key).first()
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
        db_session.add(record)
        print(f"[SAVE] Guardando memoria: {key} -> {value} (Prioridad: {priority})")
    db_session.commit()