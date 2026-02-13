"""
backend/src/config.py
Configuración limpia de la aplicación (sin Flask-Login)
"""

import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Configuración general de la aplicación."""
    
    # Database
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    #SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    
    # Redis (para caché de mensajes)
    REDIS_URL = os.getenv("REDIS_URL")
    
    # Security
    SECRET_KEY = os.getenv("SECRET_KEY")
    
    """
    Mejoras en el Futuro:
    -------------------
    # Clerk (autenticación)
    CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY")
    CLERK_PUBLISHABLE_KEY = os.getenv("CLERK_PUBLISHABLE_KEY")
    
    # CORS
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    
    # LLM Providers
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
    """
    # Redis Cache Settings
    REDIS_MESSAGE_TTL = 604800  # 7 días en segundos
    REDIS_MAX_MESSAGES_PER_CHAT = 20  # Últimos 20 mensajes
    
    @staticmethod
    def init_app(app):
        """Inicialización de configuración en la app."""
        pass