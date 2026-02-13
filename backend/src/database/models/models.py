import pytz
import uuid
from enum import Enum
from datetime import datetime, timezone
from sqlalchemy import text, Column, String, Integer, Boolean, DateTime, Text, ForeignKey, BigInteger, UniqueConstraint, Float
from sqlalchemy import Enum as PgEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, declarative_base
from werkzeug.security import generate_password_hash, check_password_hash
from pgvector.sqlalchemy import Vector 

# Configuración de Timezone
TIMEZONE = pytz.timezone('America/Guayaquil')
Base = declarative_base()

# --- ENUMS NATIVOS ---
class AuthProvider(str, Enum):
    LOCAL = "local"
    GOOGLE = "google"
    GITHUB = "github"
    CLERK = "clerk"

class MemoryType(str, Enum):
    SESSION = "session"
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"

# --- MODELOS DE USUARIO Y CHAT ---
class User(Base):
    __tablename__ = 'users'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clerk_id = Column(String(255), unique=True, nullable=False) # Guardamos el ID de Clerk para referencia, pero no lo usamos como PK
    email = Column(String(255), unique=True, index=True)
    name = Column(String(255))
    password_hash = Column(String(255))
    is_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(TIMEZONE))
    last_login = Column(DateTime(timezone=True))
    auth_provider = Column(PgEnum(AuthProvider), nullable=False) # Guardamos como string para evitar conflictos de tipos
    email_verified = Column(Boolean, default=False)
    picture = Column(String(255))
    
    chats = relationship('Chat', backref='user', cascade="all, delete-orphan")
    
    tokens = relationship('UserToken', backref='user', cascade="all, delete-orphan")
    
    # Métodos de seguridad que ya tenías
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Chat(Base):
    __tablename__ = 'chat'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(TIMEZONE))
    summary = Column(Text)
    title = Column(String(255))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(TIMEZONE), onupdate=lambda: datetime.now(TIMEZONE))
    
    messages = relationship('Message', backref='chat', cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = 'message'
    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(UUID(as_uuid=True), ForeignKey('chat.id'), nullable=False)
    role = Column(String(16), nullable=False) # 'user', 'assistant', 'system'
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(TIMEZONE))

# --- MODELO DE MEMORIA VECTORIAL (RAG) ---
class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    filename = Column(String(255))
    content = Column(Text, nullable=False) # El texto del fragmento
    embedding = Column(Vector(384)) # Agregamos la columna Vector (ajusta 1536 si usas OpenAI, 768 para otros) 
    """
    -- Embedding --
    Nombre: all-MiniLM-L6-v2
    Libreria: sentence-transformers
    Dimensiones: 384
    Utilizar: Por medio de API externa o librería local
    """
    mime_type = Column(String(100))
    file_size = Column(Integer)
    url = Column(Text)  # URL del archivo original o almacenado
    source = Column(String(50))
    tag = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))

class UserToken(Base):
    __tablename__ = "user_token"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    provider = Column(String(50), nullable=False)  # ej: 'google', 'notion'
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text)
    expires_at = Column(DateTime)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(TIMEZONE))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(TIMEZONE), onupdate=lambda: datetime.now(TIMEZONE))
    
    __table_args__ = (
        UniqueConstraint('user_id', 'provider', name='uq_user_provider'),
    )
# --- MONITOREO DE IA (Costos y Rendimiento) ---
class LLMLog(Base):
    __tablename__ = "llm_logs"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    chat_id = Column(UUID(as_uuid=True), ForeignKey("chat.id"), index=True)
    model_name = Column(String(100), nullable=False) # ej: "gpt-4o", "claud-3.5"
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    
    response_time_sec = Column(Float) # Tiempo que tardó el LLM en responder
    status = Column(String(20)) # "success", "error"
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(TIMEZONE), index=True)

# --- MONITOREO DE HARDWARE (Salud del Servidor) ---
class SystemStats(Base):
    __tablename__ = "system_stats"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    server_name = Column(String(100), index=True) # ej: "linux-backend-1.5gb", "windows-main"
    ip_address = Column(String(45))
    
    cpu_usage_percent = Column(Float)
    ram_used_gb = Column(Float)
    ram_total_gb = Column(Float)
    uptime_seconds = Column(BigInteger)
    
    # Aquí puedes guardar el link de la API Key o el ID del servidor si usas un servicio externo
    api_reference = Column(Text, nullable=True) 
    
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(TIMEZONE), index=True)
# --- LOGS DE PING (Monitoreo de Latencia) ---    
class PingLog(Base):
    __tablename__ = "ping_logs"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    service = Column(Text, nullable=False, index=True)
    event_type = Column(Text, nullable=False, index=True) # "llm_request", "ping", "pong"
    message = Column(Text)
    response_ms = Column(Integer)
    status_code = Column(Integer)
    client_ip = Column(String(45))
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(TIMEZONE), index=True)