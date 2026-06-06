import pytz
import uuid
from enum import Enum
from pgvector.sqlalchemy import Vector 
from datetime import datetime, timezone
from src.core.time_helper import get_now
#from src.database.settings.connection import Base
from sqlalchemy import Enum as PgEnum
from sqlalchemy import PrimaryKeyConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy import text, Column, String, Integer, Boolean, DateTime, Text, ForeignKey, BigInteger, UniqueConstraint, Float

#from werkzeug.security import generate_password_hash, check_password_hash

Base = declarative_base()

# --- ENUMS NATIVOS ---
class AuthProvider(str, Enum):
    LOCAL = "local"
    GOOGLE = "google"
    GITHUB = "github"
    CLERK = "clerk"
    AWS = "aws"
    MANUAL = "manual"

class MemoryType(str, Enum):
    SESSION = "session"
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"

# --- MODELOS DE USUARIO Y CHAT ---
class User(Base):
    __tablename__ = 'users'

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email       = Column(String(255), unique=True, index=True)
    name        = Column(String(255))
    is_admin    = Column(Boolean, default=False)
    is_active   = Column(Boolean, default=True)
    created_at  = Column(DateTime(timezone=True), default=get_now)
    last_login  = Column(DateTime(timezone=True))
    picture     = Column(String(255))
    
    chats      = relationship('Chat', backref='user', cascade="all, delete-orphan")
    identities = relationship('UserIdentity', backref='user', cascade="all, delete-orphan")
    tokens     = relationship('UserToken', backref='user', cascade="all, delete-orphan")
    
# --- MODELO DE IDENTIDADES (LA LLAVE) ---
class UserIdentity(Base):
    __tablename__ = 'user_identities'

    id               = Column(Integer, primary_key=True)
    user_id          = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    app_id           = Column(String(50), nullable=False, index=True, server_default='jarvis-default')
    provider         = Column(PgEnum(AuthProvider), nullable=False)
    provider_user_id = Column(String(255), nullable=False) # Aquí va el 'sub' de Clerk o AWS
    
    # Un usuario no puede tener dos identidades del mismo proveedor
    __table_args__ = (UniqueConstraint('provider', 'provider_user_id', name='_provider_user_uc'),)
    
class Chat(Base):
    __tablename__ = 'chat'
    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id    = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    app_id     = Column(String(50), nullable=False, index=True, server_default='jarvis-default')
    created_at = Column(DateTime(timezone=True), default=get_now)
    summary    = Column(Text)
    title      = Column(String(255))
    updated_at = Column(DateTime(timezone=True), default=get_now, onupdate=get_now)
    
    messages = relationship('Message', backref='chat', cascade="all, delete-orphan")

# --- MODELO DE MENSAJES (HISTORIAL DE CONVERSACIÓN) ---
class Message(Base):
    __tablename__ = 'message'
    id         = Column(Integer, primary_key=True, autoincrement=True)
    chat_id    = Column(UUID(as_uuid=True), ForeignKey('chat.id'), nullable=False)
    role       = Column(String(16), nullable=False) # 'user', 'assistant', 'system'
    content    = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=get_now)

# --- MODELO DE MEMORIA VECTORIAL (RAG) ---
class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id    = Column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    filename   = Column(String(255))
    content    = Column(Text, nullable=False) # El texto del fragmento
    embedding  = Column(Vector(768)) # Agregamos la columna Vector (ajusta 1536 si usas OpenAI, 768 para otros) 
    mime_type  = Column(String(100))
    file_size  = Column(Integer)
    url        = Column(Text)  # URL del archivo original o almacenado
    source     = Column(String(50))
    tag        = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))

# --- MODELO DE TOKENS DE ACCESO (OAuth) ---
class UserToken(Base):
    __tablename__ = "user_token"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    user_id       = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    provider      = Column(String(50), nullable=False)  # ej: 'google', 'notion'
    access_token  = Column(Text, nullable=False)
    refresh_token = Column(Text)
    expires_at    = Column(DateTime(timezone=True))
    created_at    = Column(DateTime(timezone=True), default=get_now)
    updated_at    = Column(DateTime(timezone=True), default=get_now, onupdate=get_now)
    
    __table_args__ = (
        UniqueConstraint('user_id', 'provider', name='uq_user_provider'),
    )

# --- MONITOREO DE IA (Costos y Rendimiento) ---
class LLMLog(Base):
    __tablename__ = "llm_logs"
    
    id                = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id           = Column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    chat_id           = Column(UUID(as_uuid=True), ForeignKey("chat.id"), index=True)
    model_name        = Column(String(100), nullable=False) # ej: "gpt-4o", "claud-3.5"
    prompt_tokens     = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens      = Column(Integer, default=0)
    response_time_sec = Column(Float)               # Tiempo que tardó el LLM en responder
    status            = Column(String(20))                     # "success", "error"
    timestamp         = Column(DateTime(timezone=True), default=get_now, index=True)

# --- MONITOREO DE HARDWARE (Salud del Servidor) ---
class SystemStats(Base):
    __tablename__ = "system_stats"
    
    id                = Column(BigInteger, primary_key=True, autoincrement=True)
    server_name       = Column(String(100), index=True) # ej: "linux-backend-1.5gb", "windows-main"
    ip_address        = Column(String(45))
    cpu_usage_percent = Column(Float)
    ram_used_gb       = Column(Float)
    ram_total_gb      = Column(Float)
    uptime_seconds    = Column(BigInteger)
    api_reference     = Column(Text, nullable=True) # Aquí puedes guardar el link de la API Key o el ID del servidor si usas un servicio externo 
    timestamp         = Column(DateTime(timezone=True), default=get_now, index=True)

# --- LOGS DE PING (Monitoreo de Latencia) ---    
class PingLog(Base):
    __tablename__ = "ping_logs"
    
    id           = Column(BigInteger, primary_key=True, autoincrement=True)
    service      = Column(Text, nullable=False, index=True)
    event_type   = Column(Text, nullable=False, index=True) # "llm_request", "ping", "pong"
    message      = Column(Text)
    response_ms  = Column(Integer)
    status_code  = Column(Integer)
    client_ip    = Column(String(45))
    next_ping_sc = Column(Integer, nullable=True)
    timestamp    = Column(DateTime(timezone=True), default=get_now, index=True)
    
    
# --- POMODORO (Registro de sesiones de trabajo) ---
class SessionType(str, Enum):
    TRABAJO  = "trabajo"
    DESCANSO = "descanso"

class PomodoroSession(Base):
    __tablename__ = "pomodoro_sessions"

    id             = Column(BigInteger, primary_key=True, autoincrement=True)
    session_number = Column(Integer, nullable=False)               # Sesión #1, #2…
    session_type   = Column(PgEnum(SessionType),  nullable=False)  # trabajo | descanso
    status         = Column(Boolean, nullable=False)             # true = completada, false = interrumpida 
    tag            = Column(String(100), nullable=True)          # Etiqueta personalizada para la session
    work_minutes   = Column(Integer, nullable=False, default=25)
    break_minutes  = Column(Integer, nullable=False, default=5)
    server_name    = Column(String(100))                           # de qué máquina viene
    started_at     = Column(DateTime(timezone=True), nullable=False)
    ended_at       = Column(DateTime(timezone=True), default=get_now)
    created_at     = Column(DateTime(timezone=True), default=get_now, index=True)
    
# --- MODELO HITL - Human in the Loop (Preferencias) ---
# ─────────────────────────────────────────────────────────────
#  ENUMS
# ─────────────────────────────────────────────────────────────
 
class HITLRiskLevel(str, Enum):
    SAFE  = "safe"
    WARN  = "warn"    # requirió confirmación
    BLOCK = "block"   # bloqueado directamente
 
 
class HITLVerdict(str, Enum):
    BLOCKED   = "blocked"    # bloqueado automático (BLOCK)
    PENDING   = "pending"    # esperando respuesta del admin (WARN)
    APPROVED  = "approved"   # admin aprobó
    REJECTED  = "rejected"   # admin rechazó
 
 
 
# ─────────────────────────────────────────────────────────────
#  HITL LOG — Un registro por cada intercepción
# ─────────────────────────────────────────────────────────────
 
class HITLLog(Base):
    """
    Registra cada vez que el motor HITL intercepta una acción de Koda.
    - BLOCK  → verdict='blocked',  resuelto automáticamente
    - WARN   → verdict='pending',  espera acción del admin
    """
    __tablename__ = "hitl_logs"
 
    id           = Column(BigInteger, primary_key=True, autoincrement=True)
 
    # Contexto del agente
    user_id      = Column(UUID(as_uuid=True), ForeignKey("users.id"),  nullable=False, index=True)
    chat_id      = Column(UUID(as_uuid=True), ForeignKey("chat.id"),   nullable=True,  index=True)
    session_id   = Column(UUID(as_uuid=True), ForeignKey("agent_sessions.id"), nullable=True, index=True) #  1. Qué interceptó el HITL
    tool_name    = Column(String(100), nullable=False)           # ej: "koda_execute_code"
    raw_input    = Column(Text, nullable=False)                  # el texto que disparó la regla
    matched_rule = Column(String(255), nullable=True)            # el patrón regex que matcheó
    risk_level   = Column(PgEnum(HITLRiskLevel), nullable=False) # 2. Clasificación
    verdict      = Column(PgEnum(HITLVerdict),   nullable=False, default=HITLVerdict.PENDING, index=True)
    resolved_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)  #  # 3.Resolución (si fue WARN) - UUID del admin
    resolved_at  = Column(DateTime(timezone=True), nullable=True)
    admin_note   = Column(Text, nullable=True)                   # nota opcional del admin al aprobar/rechazar
    created_at   = Column(DateTime(timezone=True), default=get_now, index=True) # 4. Timestamps
 
    user         = relationship("User", foreign_keys=[user_id])
    resolver     = relationship("User", foreign_keys=[resolved_by])
 
 
# ─────────────────────────────────────────────────────────────
#  AGENT SESSION — Ciclo de vida de una ejecución larga
# ─────────────────────────────────────────────────────────────

class AgentStatus(str, Enum):
    RUNNING   = "running"
    PAUSED    = "paused"
    WAITING   = "waiting"     # esperando aprobación HITL
    COMPLETED = "completed"
    TIMEOUT   = "timeout"
    FAILED    = "failed"
 
class AgentSession(Base):
    """
    Trackea una ejecución larga de Koda (puede durar horas).
    Soporta: pause/resume, checkpoint, timeout automático.
    """
    __tablename__ = "agent_sessions"
 
    id              = Column(UUID(as_uuid=True), primary_key=True)
    user_id         = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    chat_id         = Column(UUID(as_uuid=True), ForeignKey("chat.id"),  nullable=True)
    status          = Column(PgEnum(AgentStatus), nullable=False, default=AgentStatus.RUNNING, index=True)
    task_description = Column(Text, nullable=True)        # Tarea y progreso - resumen de lo que hace Koda
    current_step     = Column(String(255), nullable=True) # ej: "running tests", "installing deps"
    steps_completed  = Column(Integer, default=0)
    steps_total      = Column(Integer, nullable=True)     # None si no se sabe el total
    checkpoint_data  = Column(Text, nullable=True)        # Checkpoint — estado serializado para poder resumir JSON con el estado actual del agente
    timeout_seconds  = Column(Integer, default=3600)      # Timeout — si no hay actividad en X segundos, se marca como timeout - 1 hora por defecto
    last_heartbeat   = Column(DateTime(timezone=True), default=get_now)
    result_summary   = Column(Text, nullable=True)        # Resultado final
    error_message    = Column(Text, nullable=True)
    started_at       = Column(DateTime(timezone=True), default=get_now) # Timestamps
    paused_at        = Column(DateTime(timezone=True), nullable=True)
    completed_at     = Column(DateTime(timezone=True), nullable=True)
    created_at       = Column(DateTime(timezone=True), default=get_now, index=True)
 
    # Relationships
    user             = relationship("User", foreign_keys=[user_id])
    hitl_logs        = relationship("HITLLog", foreign_keys=[HITLLog.session_id], backref="session")
 