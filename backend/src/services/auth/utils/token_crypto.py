# src/utils/token_crypto.py
import os
from dotenv import load_dotenv
from cryptography.fernet import Fernet

load_dotenv()
   
FERNET_KEY = os.getenv("FERNET_SECRET_KEY")
fernet = Fernet(FERNET_KEY)

def encrypt_token(token: str) -> str:
    return fernet.encrypt(token.encode()).decode()

def decrypt_token(token: str) -> str:
    return fernet.decrypt(token.encode()).decode()
