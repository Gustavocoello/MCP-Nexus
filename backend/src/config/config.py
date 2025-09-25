import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Configuración general de la aplicación."""
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Sesiones Redis
    SESSION_TYPE = "redis"
    SESSION_COOKIE_NAME = "session"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = True  # Debe estar en True para cross-origin HTTPS
    SESSION_COOKIE_SAMESITE = "None"  # Permite enviar cookies desde otro dominio

    # También para recordar sesiones con LoginManager (opcional pero recomendado)
    REMEMBER_COOKIE_SECURE = True
    REMEMBER_COOKIE_SAMESITE = "None"

    # Redis y Secret
    REDIS_URL = os.getenv("REDIS_URL")
    SECRET_KEY = os.getenv("SECRET_KEY")
