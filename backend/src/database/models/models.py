import uuid
from enum import Enum
from extensions import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

class AuthProvider(Enum):
    LOCAL = "local"
    GOOGLE = "google"
    GITHUB = "github"

class User(db.Model):
    __tablename__ = 'user'

    id = db.Column(db.String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = db.Column(db.String(255), unique=True, nullable=True)
    name = db.Column(db.String(255))
    password_hash = db.Column(db.String(255), nullable=True)  # 🔐 Solo si LOCAL
    is_admin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    auth_provider = db.Column(db.Enum(AuthProvider, values_callable=lambda x: [e.value for e in x]), default=AuthProvider.LOCAL.value, nullable=False)
    email_verified = db.Column(db.Boolean, default=False)
    google_id = db.Column(db.String(128), unique=True, nullable=True)
    picture = db.Column(db.String(255), nullable=True)
    locale = db.Column(db.String(10), nullable=True)

    # Relaciones existentes
    chats = db.relationship('Chat', backref='user', cascade="all, delete-orphan")
    tokens = db.relationship('UserToken', backref='user', cascade="all, delete-orphan")

    # Métodos auxiliares
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Chat(db.Model):
    __tablename__ = 'chat'
    id = db.Column(db.String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(64), db.ForeignKey('user.id'), nullable=True)  # 🔥 clave foránea
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    summary = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    title = db.Column(db.String(255))

    messages = db.relationship('Message', backref='chat', cascade="all, delete-orphan")
    memories = db.relationship('UserMemory', backref='chat', cascade="all, delete-orphan")


class UserToken(db.Model):
    __tablename__ = "user_token"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.String(64), db.ForeignKey('user.id'), nullable=False)
    provider = db.Column(db.String(50), nullable=False)  # ej: 'google_calendar', 'notion'
    access_token = db.Column(db.Text, nullable=False)
    refresh_token = db.Column(db.Text)
    expires_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'provider', name='uq_user_provider'),
    )

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