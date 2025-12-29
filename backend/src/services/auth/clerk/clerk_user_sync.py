# src/services/auth/clerk/clerk_user_sync.py

import os
from httpx import Auth
import requests
from extensions import db
from src.database.models import User, AuthProvider
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY")
CLERK_API_URL = "https://api.clerk.com/v1"

def sync_clerk_user(clerk_user_id: str) -> User:
    """
    Verifica si el usuario existe en la DB. 
    Si no existe, lo busca en la API de Clerk y lo crea.
    """
    
    # 1. Buscar usuario en la DB local por Clerk ID
    user = db.session.get(User, clerk_user_id)

    if user:
        # El usuario ya existe, actualizar timestamp de login
        user.last_login = datetime.utcnow()
        db.session.commit()
        return user
    
    # 2. Si no existe, buscar en la API REST de Clerk
    try:
        headers = {
            "Authorization": f"Bearer {CLERK_SECRET_KEY}",
            "Content-Type": "application/json"
        }
        
        response = requests.get(
            f"{CLERK_API_URL}/users/{clerk_user_id}",
            headers=headers
        )
        response.raise_for_status()
        clerk_data = response.json()
        
        # Extracción de datos
        primary_email_id = clerk_data.get('primary_email_address_id')
        primary_email = None
        
        # Buscar el email principal
        for email_obj in clerk_data.get('email_addresses', []):
            if email_obj.get('id') == primary_email_id:
                primary_email = email_obj.get('email_address')
                break
        
        # Construir nombre completo
        first_name = clerk_data.get('first_name', '')
        last_name = clerk_data.get('last_name', '')
        full_name = f"{first_name} {last_name}".strip()

        
        # Crear el nuevo usuario
        new_user = User(
            id=clerk_user_id,
            email=primary_email,
            name=full_name if full_name else primary_email,
            picture=clerk_data.get('image_url'),
            email_verified=True,  # Clerk ya verificó
            is_active=True,
            auth_provider=AuthProvider.CLERK,
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        print(f"✅ Nuevo usuario sincronizado desde Clerk: {clerk_user_id}")
        return new_user
        
    except requests.RequestException as e:
        print(f"Error al obtener datos de Clerk API: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}")
        raise Exception(f"No se pudo sincronizar el usuario {clerk_user_id} desde Clerk.")
    except Exception as e:
        print(f"Error inesperado: {e}")
        raise Exception(f"Error al procesar datos del usuario {clerk_user_id}.")