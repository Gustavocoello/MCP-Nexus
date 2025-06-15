from datetime import datetime
from extensions import db
import uuid

class Chat(db.Model):
    __tablename__ = 'chat'
    id = db.Column(db.String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    summary = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    title = db.Column(db.String(255))

    messages = db.relationship('Message', backref='chat', cascade="all, delete-orphan")


class Message(db.Model):
    __tablename__ = 'message'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    chat_id = db.Column(db.String(64), db.ForeignKey('chat.id'), nullable=False)
    role = db.Column(db.String(16), nullable=False)  # 'user' o 'assistant'
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
