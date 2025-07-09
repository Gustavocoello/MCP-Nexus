import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Configuración general de la aplicación."""
    #SQLALCHEMY_DATABASE_URI = f"mysql+mysqlconnector://{os.getenv('USER_BD')}:{os.getenv('PASS_BD')}@{os.getenv('ROOT_BD')}/{os.getenv('NAME_BD')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_TYPE = "redis"
    SESSION_COOKIE_NAME = "session"
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    REDIS_URL = os.getenv("REDIS_URL")
    SECRET_KEY = os.getenv("SECRET_KEY")

