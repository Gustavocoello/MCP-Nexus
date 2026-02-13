# src/services/auth/clerk/clerk_user_sync.py

import os
import requests
from extensions import db
from sqlalchemy import select
from src.database.models import User, AuthProvider
from datetime import datetime, timezone
from dotenv import load_dotenv
from src.database.config.connection import SessionLocal

load_dotenv()

CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY")
CLERK_API_URL = "https://api.clerk.com/v1"

def sync_clerk_user(clerk_user_id: str) -> User:
    """
    Sincroniza el usuario de Clerk con la DB local buscando por Email para evitar
    duplicados si el ID de Clerk cambia (ej. entre Dev y Producción).
    """
    try:
        db_session = SessionLocal()
        # 1. Intentar buscar primero por el ID que nos llega (caso más rápido)
        safe_clerk_id = str(clerk_user_id)
        user = db_session.query(User).filter(User.clerk_id == safe_clerk_id).first()

        if user:
            user.last_login = datetime.now(timezone.utc)
            db_session.commit()
            db_session.refresh(user)
            return user
        
        # 2. Si no existe por ID, necesitamos sus datos de Clerk para buscar por EMAIL
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
            
            # Extraer el email principal de la respuesta de Clerk
            primary_email_id = clerk_data.get('primary_email_address_id')
            primary_email = None
            for email_obj in clerk_data.get('email_addresses', []):
                if email_obj.get('id') == primary_email_id:
                    primary_email = email_obj.get('email_address')
                    break
            
            if not primary_email:
                raise Exception("Clerk user has no primary email address.")

            # 🚀 PASO CLAVE: Buscar en nuestra DB por EMAIL antes de crear uno nuevo
            user_by_email = db_session.query(User).filter(User.email == primary_email).first()

            if user_by_email:
                # Si el email ya existe, actualizamos el ID viejo con el nuevo de Clerk
                print(f"🔄 Vinculando usuario existente {primary_email} con nuevo ID de Clerk: {clerk_user_id}")
                
                # Si tu tabla User usa el ID como Primary Key, SQLAlchemy no permite cambiarlo fácilmente.
                # En ese caso, lo más limpio es actualizar los datos y el ID si tu modelo lo permite,
                # o podrías tener una columna 'clerk_id' separada. 
                # Si el ID ES la primary key, lo borramos y recreamos o simplemente lo tratamos aquí:
                
                user_by_email.clerk_id = clerk_user_id 
                user_by_email.last_login = datetime.now(timezone.utc)
                user_by_email.picture = clerk_data.get('image_url')
                db_session.commit()
                db_session.refresh(user_by_email)
                return user_by_email

            # 3. Si no existe ni por ID ni por EMAIL, crear el nuevo usuario
            first_name = clerk_data.get('first_name', '')
            last_name = clerk_data.get('last_name', '')
            full_name = f"{first_name} {last_name}".strip()

            new_user = User(
            # El ID (UUID) se genera automáticamente por el modelo
            clerk_id=clerk_user_id,
            email=primary_email,
            name=full_name if full_name else primary_email,
            picture=clerk_data.get('image_url'),
            email_verified=True,
            is_active=True,
            auth_provider=AuthProvider.CLERK,
            created_at=datetime.now(timezone.utc),
            last_login=datetime.now(timezone.utc)
        )
            
            db_session.add(new_user)
            db_session.commit()
            db_session.refresh(new_user)
            
            print(f"Nuevo usuario creado y sincronizado: {primary_email}")
            return new_user
            
        except requests.RequestException as e:
            print(f"Error al obtener datos de Clerk API: {e}")
            raise Exception(f"No se pudo sincronizar desde Clerk.")
    except Exception as e:
        db_session.rollback() # Importante hacer rollback si falla el insert/update
        print(f"Error inesperado en sync: {e}")
        raise e
    finally:
        db_session.close()