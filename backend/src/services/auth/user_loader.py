# src/services/auth/user_loader.py
from src.database.models import User

def load_user(user_id):
    return User.query.get(user_id)
