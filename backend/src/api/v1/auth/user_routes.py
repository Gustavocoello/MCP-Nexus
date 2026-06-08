# src/api/v1/user_routes.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

# Importamos las dependencias core de FastAPI
from src.services.auth.auth.auth_middleware import get_current_user
from src.database.settings.connection import get_db
from src.database.models.models import UserToken
from src.core.logging import get_logger

logger = get_logger(__name__)

# Creamos los routers con sus prefijos y "tags" (para que Swagger UI los agrupe bonito)
user_router = APIRouter(prefix="/api/v1/user", tags=["User Profile"])
integrations_router = APIRouter(prefix="/api/v1/integrations", tags=["Integrations"])

# ==========================================
# RUTAS DE USUARIO
# ==========================================

@user_router.get("/sync", status_code=status.HTTP_200_OK)
async def sync_user_profile(user_data: dict = Depends(get_current_user)):
    """
    Ruta diseñada para ser llamada inmediatamente después del login en el frontend.
    Su única función es sincronizar el perfil de Clerk con la DB local.
    """
    # Extraemos el objeto user que el middleware ya fue a buscar a la DB
    user = user_data["user_obj"]
    
    return {
        "status": "success",
        "message": "User profile is active.",
        "user_id": str(user.id),
        "email": user.email
    }
    
@user_router.get("/profile", status_code=status.HTTP_200_OK)
async def get_user_profile(user_data: dict = Depends(get_current_user)):
    """
    Retorna los datos completos del usuario desde la DB local 
    para alimentar el componente Config/GeneralTab del SDK.
    """
    user = user_data["user_obj"]
    
    return {
        "id": str(user.id),
        "email": user.email,
        "fullName": user.name,
        "imageUrl": user.picture,
        "last_login": user.last_login.isoformat() if user.last_login else None,
    }


# ==========================================
# RUTAS DE INTEGRACIONES
# ==========================================

@integrations_router.get("/status", status_code=status.HTTP_200_OK)
async def get_integration_status(
    user_data: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        user_id = user_data["user_id"]

        # Verificar si existe un token de Google Calendar
        stmt = select(UserToken).filter_by(user_id=user_id, provider="google_calendar")
        google_token = db.execute(stmt).scalar_one_or_none()

        return {
            "google_calendar": google_token is not None
        }
        
    except Exception as e:
        logger.exception("Error comprobando el status de integraciones")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=str(e)
        )

@integrations_router.post("/disconnect/{provider}", status_code=status.HTTP_200_OK)
async def disconnect_integration(
    provider: str, # FastAPI lo lee directo de la URL
    user_data: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        user_id = user_data["user_id"]

        stmt = select(UserToken).filter_by(user_id=user_id, provider=provider)
        token = db.execute(stmt).scalar_one_or_none()

        if not token:
            # En API REST modernas, borrar algo que ya no existe se suele responder con un 200 OK 
            # ya que el estado final deseado (que no exista) se cumple.
            return {"message": "Integration already disconnected"}

        db.delete(token)
        db.commit()

        return {"message": f"{provider} disconnected successfully"}
        
    except Exception as e:
        db.rollback()
        logger.exception(f"Error desconectando la integracion: {provider}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=str(e)
        )