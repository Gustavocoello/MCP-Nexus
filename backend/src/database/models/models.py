import uuid
from enum import Enum
from extensions import db
from datetime import datetime

class Chat(db.Model):
    __tablename__ = 'chat'
    id = db.Column(db.String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    summary = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    title = db.Column(db.String(255))

    messages = db.relationship('Message', backref='chat', cascade="all, delete-orphan")
    memories = db.relationship('UserMemory', backref='chat', cascade="all, delete-orphan")


class Message(db.Model):
    __tablename__ = 'message'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    chat_id = db.Column(db.String(64), db.ForeignKey('chat.id'), nullable=False)
    role = db.Column(db.String(16), nullable=False)  # 'user' o 'assistant'
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Modelo de memoria para el LLM - método avanzado
class MemoryType(Enum):
    SESSION = "session"
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"

class UserMemory(db.Model):
    __tablename__ = "user_memory"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    chat_id = db.Column(db.String(64), db.ForeignKey('chat.id'), nullable=False)
    key = db.Column(db.String(255), nullable=False)
    value = db.Column(db.Text, nullable=False)
    type = db.Column(db.Enum(MemoryType, values_callable=lambda x: [e.value for e in x]), default=MemoryType.LONG_TERM.value)
    priority = db.Column(db.Integer, default=3)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)