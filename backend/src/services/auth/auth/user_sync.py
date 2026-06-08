# src/services/auth/clerk/clerk_user_sync.py

import os
import requests
from sqlalchemy import select
from datetime import datetime, timezone
from dotenv import load_dotenv

from src.core.time_helper import get_now
from src.core.logging import get_logger
from src.database.models.models import User, AuthProvider, UserIdentity
from src.database.settings.connection import SessionLocal

# Inicializamos el logger
logger = get_logger(__name__)
load_dotenv()

CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY")
CLERK_API_URL = "https://api.clerk.com/v1"

def sync_user_universal(provider_user_id: str, app_id: str, provider: str, extra_data: dict = None):
    """
    Sincroniza o crea el usuario en la base de datos local.
    Maneja su propia sesión de BD (SessionLocal) ya que es invocada desde un Middleware.
    """
    db_session = SessionLocal()
    logger.info(f"--- [SYNC START] App: {app_id} | Provider: {provider} | ID: {provider_user_id} ---")
    
    try:
        # 1. BUSCAR IDENTIDAD
        identity = db_session.query(UserIdentity).filter(
            UserIdentity.app_id == app_id,
            UserIdentity.provider == provider,
            UserIdentity.provider_user_id == str(provider_user_id)
        ).first()

        if identity:
            user = identity.user
            user.last_login = get_now()
            db_session.commit()
            logger.info(f"[EXISTING IDENTITY] User: {user.email}")
            return user

        # 2. OBTENER DATOS SEGÚN PROVEEDOR
        email = None
        user_info = {}

        if provider == AuthProvider.CLERK:
            logger.info(f"[FETCHING CLERK API] for ID: {provider_user_id}")
            headers = {"Authorization": f"Bearer {CLERK_SECRET_KEY}"}
            response = requests.get(f"{CLERK_API_URL}/users/{provider_user_id}", headers=headers)
            response.raise_for_status()
            data = response.json()
            
            # Lógica de email de Clerk
            primary_id = data.get('primary_email_address_id')
            email = next((e['email_address'] for e in data.get('email_addresses', []) if e['id'] == primary_id), None)
            
            user_info = {
                "name": f"{data.get('first_name', '')} {data.get('last_name', '')}".strip(),
                "picture": data.get('image_url')
            }
        else:
            # PARA MANUAL / OTROS: Los datos DEBEN venir del Middleware
            logger.info(f"[MANUAL DATA] Using extra_data provided by Middleware")
            email = extra_data.get('email') if extra_data else None
            user_info = {
                "name": extra_data.get('name') if extra_data else None,
                "picture": extra_data.get('picture') if extra_data else "https://ui-avatars.com/api/?name=User"
            }

        if not email:
            logger.error(f"No email found for provider {provider}")
            raise Exception(f"Identidad incompleta: Falta email.")

        # 3. UNIFICACIÓN GLOBAL POR EMAIL
        user = db_session.query(User).filter(User.email == email).first()

        if not user:
            logger.info(f"[NEW GLOBAL USER] Creating record for: {email}")
            user = User(
                email=email,
                name=user_info.get('name') or email,
                picture=user_info.get('picture'),
                created_at=get_now(),
                last_login=get_now()
            )
            db_session.add(user)
            db_session.flush() # flush para obtener user.id antes del commit final
        else:
            logger.info(f"[LINKING] Email {email} found. Attaching new identity...")

        # 4. CREAR LA NUEVA IDENTIDAD (LA LLAVE PARA ESTA APP)
        new_identity = UserIdentity(
            user_id=user.id,
            app_id=app_id,
            provider=provider,
            provider_user_id=str(provider_user_id)
        )
        db_session.add(new_identity)
        db_session.commit()
        db_session.refresh(user)
        
        logger.info(f"[SYNC COMPLETE] User {user.email} is now ready for {app_id}")
        return user

    except Exception as e:
        db_session.rollback()
        logger.error(f"[SYNC FATAL ERROR]: {str(e)}")
        raise e
    finally:
        db_session.close()