from ast import stmt
import re
import os
import json
import asyncio
import threading
from typing import Optional, Dict, Any
from uuid import UUID
from queue import Queue, Empty
from sqlalchemy import select, delete
# FastAPI
from fastapi import APIRouter, Depends, Request, Response, BackgroundTasks, UploadFile, File, HTTPException, status
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session
from pydantic import BaseModel

from src.core.logging import get_logger
from src.core.time_helper import get_now
from src.services.cache.redis_cache import ChatCache
from src.database.settings.connection import SessionLocal, get_db
from src.services.cache.redis_sidebar import SidebarCache
from src.services.llm.chat.free_tier import generate_prompt
from src.database.models.models import Chat, Message, Document
from src.services.mcps.client.client_manager import MCPClientManager
from src.services.llm.chat.llm_router import completion, completion_stream
from src.services.llm.chat.chat_service import build_payload, execute_mcp_tool, summarize_and_trim
from src.services.auth.auth.auth_middleware import get_current_user
from src.services.integrations.onedrive.onedrive_service import upload_to_onedrive, get_user_onedrive_token
from src.services.integrations.azure.azure_vision import analyze_image_with_azure

# -- Logger --
logger = get_logger('routes')
# -- Event Queue --
event_queue = Queue()
# -- MCP Client --
mcp_client = MCPClientManager(user_id=None)  # user_id se asignará dinámicamente en cada llamada

## -------------- Mensajes de la IA con memoria -----------
search_router = APIRouter()

class SearchPromptRequest(BaseModel):
    prompt: str

class CreateChatRequest(BaseModel):
    title: Optional[str] = "Sin título"
    
class SendMessageRequest(BaseModel):
    text: str
    hidden_context: Optional[str] = ""
    tool: Optional[str] = ""
    params: Optional[Dict[str, Any]] = {}

class UpdateTitleRequest(BaseModel):
    title: str

# Función utilitaria para reemplazar a werkzeug.utils.secure_filename
def secure_filename(filename: str) -> str:
    # Remueve caracteres peligrosos del nombre del archivo
    return re.sub(r'[^a-zA-Z0-9_\.-]', '_', os.path.basename(filename))

## ----------- Mensajes de la IA sin memoria --------------
@search_router.post("/prompt")
async def handle_search_prompt(request: Request, response: Response, payload: SearchPromptRequest):
    # En FastAPI manejamos las sesiones anónimas con Cookies
    counter = int(request.cookies.get('anon_prompt_count', 0))

    if counter >= 5:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "Has alcanzado el límite de 5 mensajes de prueba.", "login_required": True}
        )

    logger.debug(f'print:{counter}')
    print("BODY RECIBIDO:", payload.dict())
    
    try:
        result = generate_prompt({"description": payload.prompt})

        if result == "Todos los servicios de IA no estan disponibles actualmente.":
            raise HTTPException(status_code=503, detail="Error: IA no disponible")
        
        # Aumentar contador y guardarlo en la cookie
        new_counter = counter + 1
        response.set_cookie(key="anon_prompt_count", value=str(new_counter), httponly=True)

        return {
            "result": result,
            "remaining": max(0, 5 - new_counter)
        }
    except Exception as e:
        logger.exception(f"Error al procesar prompt: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ------------- route principal -------------
chat_router = APIRouter()

#--------------- EVENTS QUEUE ---------------
@chat_router.get("/events")
async def events():
    async def stream():
        while True:
            try:
                # Usamos run_in_threadpool porque Queue.get() de Python bloquea el hilo
                event = await run_in_threadpool(event_queue.get, timeout=20)
                yield f"data: {json.dumps(event)}\n\n"
            except Empty:
                yield f"data: {json.dumps({'type': 'ping'})}\n\n"
            except Exception as e:
                logger.error(f"Error en stream SSE: {e}")
                break

    return StreamingResponse(stream(), media_type="text/event-stream")
# ----------------- GET ---------------------
# ---- Obtiene todos los chats ----
@chat_router.get("")
async def get_all_chats(
    db: Session = Depends(get_db), 
    user: dict = Depends(get_current_user)
):
    try:
        chats = SidebarCache.get_chats(
            user_id=user["user_id"], 
            app_id=user["app_id"], 
            db_session=db
        )
        return chats
    except Exception as e:
        logger.exception("Error al obtener chats")
        raise HTTPException(status_code=500, detail=str(e))
        
# ---- Obtiene mensajes recientes de un chat específico ----
@chat_router.get("/{chat_id}/messages/recent")
async def get_recent_messages(chat_id: UUID, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    try:
        messages = ChatCache.get_messages(str(chat_id), db_session=db)
        return messages
    except Exception as e:
        logger.exception(f"Error en mensajes recientes de {chat_id}")
        raise HTTPException(status_code=500, detail=str(e))

# ---- Obtiene todos los mensajes de un chat específico ----
@chat_router.get("/{chat_id}/messages")
async def get_chat_messages(chat_id: UUID, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    try:
        chat = db.query(Chat).filter(
            Chat.id == chat_id, 
            Chat.user_id == user["user_id"],
            Chat.app_id == user["app_id"]
        ).first()
        
        if not chat:
            raise HTTPException(status_code=404, detail='Chat no encontrado o acceso denegado')
        
        stmt = select(Message).where(Message.chat_id == chat_id).order_by(Message.created_at.asc())
        messages = db.execute(stmt).scalars().all()
        
        return [{
            "id": msg.id,
            "role": msg.role,
            "content": msg.content,
            "created_at": msg.created_at.isoformat()
        } for msg in messages]
    except Exception as e:
        logger.exception(f"Error al obtener mensajes del chat {chat_id}")
        raise HTTPException(status_code=500, detail=str(e))

    
# ----------------- DELETE -------------------
    
@chat_router.delete("/{chat_id}")
async def delete_chat(chat_id: UUID, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    try:
        # 1. BUSCAMOS EL CHAT
        chat = db.query(Chat).filter(
            Chat.id == chat_id, 
            Chat.user_id == user["user_id"],
            Chat.app_id == user["app_id"]
        ).first()
        
        # 2. VALIDACIÓN
        if not chat:
            # HTTPException es el equivalente a jsonify() + status code en FastAPI
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Chat no encontrado o acceso denegado"
            )

        # 3. ACCIÓN
        db.delete(chat)
        db.commit()
        
        # === AVISAR A REDIS ===
        SidebarCache.invalidate_user(user["user_id"], user["app_id"])
        logger.info(f"[Redis] Sidebar invalidado por eliminación de chat: {chat_id}")
        
        return {"message": "Chat eliminado correctamente"}

    except HTTPException:
        raise
    except Exception as e:
        # Si es un error inesperado (DB caída, error de sintaxis, etc.)
        db.rollback()
        logger.exception("Error al eliminar chat")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=str(e)
        )


# ----------------- POST ---------------------  
  
# ------------ POST (crear chat) ------------- 
       
@chat_router.post("", status_code=status.HTTP_201_CREATED)
async def create_chat(
    payload: CreateChatRequest, 
    db: Session = Depends(get_db), 
    user: dict = Depends(get_current_user)
):
    try:
        # Validación de seguridad defensiva
        if not user or not user.get("user_id"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuario no autenticado"
            )

        # 3. CREACIÓN DEL CHAT
        new_chat = Chat(
            user_id=user["user_id"], 
            app_id=user["app_id"],
            title=payload.title
        )
        
        db.add(new_chat)
        db.commit()
        db.refresh(new_chat)
        
        logger.debug(f"[DEBUG] Nuevo chat creado para: {user['user_id']}; ID del chat: {new_chat.id}; Título: {new_chat.title}")
        
        # 4. AVISAR A REDIS
        SidebarCache.invalidate_user(user["user_id"], user["app_id"])
        logger.info(f"CREATE: Chat {new_chat.id} vinculado a App: {user['app_id']}")
        
        # 5. RETORNAR DATA
        return {
            "id": new_chat.id,
            "title": new_chat.title,
            "created_at": new_chat.created_at.isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback() 
        logger.exception("Error al crear chat")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# --------------- POST (enviar mensaje) ---------------
@chat_router.post("/{chat_id}/message")
async def send_message(
    chat_id: UUID, 
    payload: SendMessageRequest, 
    db: Session = Depends(get_db), 
    user: dict = Depends(get_current_user)
):
    try:
        user_text = payload.text.strip()
        if not user_text:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty message")

        # 1. Buscar o crear el chat
        chat = db.query(Chat).filter(
            Chat.id == chat_id, Chat.user_id == user["user_id"], Chat.app_id == user["app_id"]
        ).first()

        if not chat:
            chat = Chat(id=chat_id, user_id=user["user_id"], app_id=user["app_id"], title="Sin titulo")
            db.add(chat)
            db.flush() # flush() asigna un ID pero sin hacer commit final todavía

        # 2. Guardar mensaje del usuario
        chat.updated_at = get_now()
        user_message = Message(chat_id=chat.id, role="user", content=user_text)
        db.add(user_message)

        # 3. Manejar contexto oculto (para RAG o imágenes)
        hidden_context = payload.hidden_context.strip()
        if hidden_context:
            db.query(Message).filter_by(chat_id=chat.id, role="context").delete()
            context_msg = Message(chat_id=chat.id, role="context", content=hidden_context)
            db.add(context_msg)

        db.commit()

        # 4. Obtener mensajes recientes
        recent = db.query(Message).filter(
            Message.chat_id == chat.id,
            Message.role != "context",
            Message.id != user_message.id
        ).order_by(Message.created_at.desc()).all()[::-1]

        # 5. Ejecutar herramienta MCP (si existe)
        mcp_context = None
        if payload.tool:
            mcp_context = execute_mcp_tool(
                tool_name=payload.tool, params=payload.params, user_id=user["user_id"],
                db_session=db, chat_id=chat.id, mcp_manager=mcp_client
            )
            if mcp_context is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, 
                    detail=f"Tool '{payload.tool}' requires connection."
                )

        # 6. Construir payload para el LLM
        llm_payload = build_payload(
            chat=chat, recent=recent, user_text=user_text, 
            hidden_context=hidden_context, mcp_context=mcp_context
        )

        # 7. Autogenerar título si es el primer mensaje
        if not chat.title or chat.title == "Sin titulo":
            words = user_text.split()
            chat.title = " ".join(words[:10]) + ("..." if len(words) > 10 else "")
            db.commit()
            SidebarCache.invalidate_user(user["user_id"])

        # 8. Generador para Streaming (Mantiene su propia DB Session por ser un proceso largo)
        async def generate():
            gen_session = SessionLocal()
            try:
                full_reply = ""
                # FastAPI permite iterar asincronamente sin bloquear hilos
                for chunk in completion_stream(llm_payload):
                    full_reply += chunk
                    yield chunk

                # Guardar en base de datos al finalizar el stream
                inner_chat = gen_session.get(Chat, chat_id)
                inner_chat.updated_at = get_now()

                new_msg = Message(chat_id=chat_id, role="assistant", content=full_reply)
                gen_session.add(new_msg)

                summarize_and_trim(inner_chat, gen_session)
                gen_session.commit()

                # Guardar en Redis Cache
                ChatCache.append_message(str(chat_id), {
                    "id": new_msg.id, "role": "assistant",
                    "content": full_reply, "created_at": get_now().isoformat()
                })
            except Exception as e:
                gen_session.rollback()
                logger.exception("Error during stream")
                yield f"\n[ERROR] {str(e)}"
            finally:
                gen_session.close()

        # Retornamos el Streaming nativo de FastAPI
        return StreamingResponse(generate(), media_type="text/plain")

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception("Error in send_message")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
        
# --------------- POST (extraer texto de archivos) ---------------
# Función normal (fuera de la ruta) para la tarea en 2do plano
def background_task(file_bytes: bytes, filename_bd: str, content_type: str, user_id: str, text_to_store: str, filename_ui: str):
    bg_session = SessionLocal() # La tarea de fondo maneja su propia sesión
    try:
        event_queue.put({"type": "upload_started", "filename": filename_ui, "user_id": str(user_id)})
        logger.info(f"Background upload started: {filename_ui}")

        access_token = get_user_onedrive_token(user_id)
        if not access_token:
            event_queue.put({"type": "upload_error", "filename": filename_ui, "error": "No OneDrive token", "user_id": str(user_id)})
            return

        download_url = upload_to_onedrive(access_token, filename_bd, file_bytes)

        document = Document(
            user_id=user_id, filename=filename_bd, content=text_to_store,
            mime_type=content_type, file_size=len(file_bytes),
            url=download_url, source="onedrive", tag="user_upload_mcp"
        )

        bg_session.add(document)
        bg_session.commit()

        event_queue.put({"type": "upload_completed", "filename": filename_ui, "url": download_url, "user_id": str(user_id)})
    except Exception as e:
        bg_session.rollback()
        logger.exception("Background task error")
        event_queue.put({"type": "upload_error", "filename": filename_ui, "error": str(e), "user_id": str(user_id)})
    finally:
        bg_session.close()


@chat_router.post("/extract_file")
async def extract_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user)
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Empty filename")

    original_filename = file.filename
    original_name_base, ext = os.path.splitext(file.filename)
    timestamp = get_now().strftime("%Y%m%d_%H%M%S")
    filename = secure_filename(f"{original_name_base}_{timestamp}{ext}")

    content_type = file.content_type
    file_bytes = await file.read() # Asincrónico y eficiente
    final_text = ""

    try:
        if content_type.startswith("image/"):
            final_text = analyze_image_with_azure(file_bytes)
            logger.info(f"Text extracted from image {original_filename}")
            resp_text = f"Image '{original_filename}':\n\n{final_text}"
        else:
            # Aquí pondrías tu lógica para PDF, Word, etc.
            resp_text = f"File content '{original_filename}':\n\n{final_text}"

        # Mandar la tarea a segundo plano. FastAPI se encarga de ejecutarla
        background_tasks.add_task(
            background_task,
            file_bytes, filename, content_type, user["user_id"], final_text, original_filename
        )

        return {
            "text": resp_text,
            "filename": original_filename,
            "status": "processing_bg"
        }

    except Exception as e:
        logger.exception("Error processing file")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

# --------------- PUT ---------------
@chat_router.put("/{chat_id}/title")
async def update_chat_title(
    chat_id: UUID, 
    payload: UpdateTitleRequest, 
    db: Session = Depends(get_db), 
    user: dict = Depends(get_current_user)
):
    try:
        chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == user["user_id"]).first()
        
        if not chat:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")
        
        chat.title = payload.title
        db.commit()
        
        # === AVISAR A REDIS ===
        SidebarCache.invalidate_user(user["user_id"])
        logger.info(f"[Redis] Sidebar invalidado por actualización de título del chat: {chat_id}")

        return {'message': 'Título actualizado', 'title': payload.title}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception("Error actualizando título del chat")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
