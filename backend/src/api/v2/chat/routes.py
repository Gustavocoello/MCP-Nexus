import os
import json
from uuid import UUID
from pydantic import BaseModel
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import StreamingResponse
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session
from io import BytesIO

# Importaciones de LangChain/LangGraph necesarias para parsear los pensamientos
from langchain_core.messages import AIMessage, ToolMessage

# Tus dependencias internas
from src.core.logging import get_logger
from src.core.time_helper import get_now
from src.database.settings.connection import get_db, SessionLocal
from src.database.models.models import Chat, Message
from src.services.cache.redis_sidebar import SidebarCache
from src.services.cache.redis_cache import ChatCache
from src.services.rag.pipeline import RAGPipeline
from src.services.llm.chat.chat_service import get_langchain_history 
from src.services.integrations.azure.azure_vision import analyze_image_with_azure
from src.services.integrations.microsoft.markitdown_extractor import extract_text_from_file
from src.services.agent.jarvis.agent import get_jarvis
from src.services.auth.auth.auth_middleware import get_current_user

logger = get_logger("chat_service_v2")

chat_v2_router = APIRouter()

# --- MODELOS DE ENTRADA ---
class SendMessageV2Request(BaseModel):
    text: str
    hidden_context: Optional[str] = ""

# =================================================================
# 1. RUTA DE AGENTES
# =================================================================
@chat_v2_router.post("/{chat_id}/message")
async def send_message_v2(
    chat_id: UUID,
    payload: SendMessageV2Request,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    try:
        user_text = payload.text.strip()
        if not user_text:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty message")

        # 1. Buscar o Crear Chat
        chat = db.query(Chat).filter(
            Chat.id == chat_id, Chat.user_id == user["user_id"], Chat.app_id == user["app_id"]
        ).first()

        if not chat:
            chat = Chat(id=chat_id, user_id=user["user_id"], app_id=user["app_id"], title="Sin titulo")
            db.add(chat)
            db.flush()

        # 2. Guardar mensaje
        chat.updated_at = get_now()
        user_message = Message(chat_id=chat.id, role="user", content=user_text)
        db.add(user_message)

        # 3. Contexto Oculto
        hidden_context = payload.hidden_context.strip()
        if hidden_context:
            db.query(Message).filter_by(chat_id=chat.id, role="context").delete()
            context_msg = Message(chat_id=chat.id, role="context", content=hidden_context)
            db.add(context_msg)
            db.commit()

        # 4. Historial (usando límite de 10)
        recent = (
            db.query(Message)
            .filter(Message.chat_id == chat.id, Message.role != "context", Message.id != user_message.id)
            .order_by(Message.created_at.desc())
            .limit(10).all()[::-1]
        )

        langchain_history = get_langchain_history(chat=chat, recent=recent, hidden_context=hidden_context)
        
        # 5. Instanciar Agente Orquestador
        jarvis_agent = get_jarvis(user["user_id"])

        # 6. Autogenerar título
        if not chat.title or chat.title == "Sin titulo":
            words = user_text.split()
            chat.title = " ".join(words[:10]) + ("..." if len(words) > 10 else "")
            db.commit()
            SidebarCache.invalidate_user(user["user_id"])

        # ==========================================================
        # EL GENERADOR DE PENSAMIENTOS (ENTERPRISE GRADE)
        # ==========================================================
        async def generate():
            gen_session = SessionLocal()
            try:
                yield "[THOUGHT] Analizando la solicitud inicial y preparando estrategia de ejecución...\n"
                
                full_reply = ""
                session_uuid = str(chat_id) # Usamos el chat_id o generas un uuid único de sesión
                
                # Ejecutamos LangGraph de manera segura en un hilo asíncrono
                # LangGraph devuelve el estado completo en cada "salto" del grafo
                for state_chunk in jarvis_agent.stream_task(user_text, user["user_id"], session_uuid):
                    
                    messages = state_chunk.get("messages", [])
                    if not messages:
                        continue
                        
                    last_msg = messages[-1]
                    
                    # CASO A: El LLM decidió usar una herramienta
                    if isinstance(last_msg, AIMessage) and last_msg.tool_calls:
                        for tool_call in last_msg.tool_calls:
                            t_name = tool_call.get("name", "UnknownTool")
                            t_args = tool_call.get("args", {})
                            
                            # Formateamos los argumentos de manera legible pero segura
                            args_str = json.dumps(t_args, ensure_ascii=False) if t_args else "{}"
                            
                            yield f"[THOUGHT] Acción requerida: Ejecutando herramienta '{t_name}'.\n"
                            yield f"[THOUGHT] Parámetros inyectados: {args_str}\n"
                            yield f"[THOUGHT] Esperando respuesta del sistema externo...\n"

                    # CASO B: La herramienta terminó y devolvió un resultado
                    elif isinstance(last_msg, ToolMessage):
                        t_name = last_msg.name
                        # No mostramos toda la data (puede ser enorme), solo avisamos que se obtuvo
                        yield f"[THOUGHT] Herramienta '{t_name}' ejecutada con éxito. Extrayendo datos relevantes...\n"
                        yield f"[THOUGHT] Evaluando los resultados obtenidos para formular el siguiente paso...\n"

                    # CASO C: El agente da la respuesta final al usuario (Fin del ciclo)
                    elif isinstance(last_msg, AIMessage) and not last_msg.tool_calls:
                        yield "[THOUGHT] Análisis completado. Generando respuesta final...\n"
                        full_reply = last_msg.content
                        
                        # (Opcional) Si quieres simular un stream de texto del resultado final:
                        # yield full_reply 
                        # Si tu framework de frontend prefiere todo de golpe, lo envías completo:
                        yield full_reply 

                # Guardamos la respuesta final en DB
                if full_reply:
                    inner_chat = gen_session.get(Chat, chat_id)
                    inner_chat.updated_at = get_now()

                    new_msg = Message(chat_id=chat_id, role="assistant", content=full_reply)
                    gen_session.add(new_msg)
                    gen_session.commit()

                    ChatCache.append_message(str(chat_id), {
                        "id": new_msg.id, "role": "assistant",
                        "content": full_reply, "created_at": get_now().isoformat()
                    })

            except Exception as e:
                gen_session.rollback()
                logger.exception("Error during agent stream")
                yield f"\n[THOUGHT] Se produjo un error crítico en la cadena de razonamiento.\n"
                yield f"\n[ERROR] {str(e)}"
            finally:
                gen_session.close()

        return StreamingResponse(generate(), media_type="text/plain")

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception("Error in send_message_v2")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# =================================================================
# 2. RUTA DE EXTRACCIÓN MASIVA (10K+ IMAGES & DOCS + RAG)
# =================================================================
@chat_v2_router.post("/extract_file")
async def extract_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty filename")

    original_filename = file.filename
    content_type = file.content_type
    
    # Leer el archivo en memoria asíncronamente
    file_bytes = await file.read()
    final_text = ""
    user_uuid = user["user_id"]

    try:
        if content_type.startswith("image/"):
            # IMPORTANTE: run_in_threadpool evita que Azure bloquee el servidor entero
            final_text = await run_in_threadpool(analyze_image_with_azure, file_bytes, user_id=user_uuid)
            resp_text = f"Image '{original_filename}':\n\n{final_text}"
        else:
            file_stream = BytesIO(file_bytes)
            # Extracción de PDF/Excel pesada a un hilo secundario
            final_text = await run_in_threadpool(extract_text_from_file, file_stream, original_filename)
            resp_text = f"Document '{original_filename}':\n\n{final_text}"
        
        # Ingesta en la Base de Datos Vectorial (RAG)
        if final_text and final_text.strip():
            # Empaquetamos la lógica de RAG en una función sincrónica
            def ingest_to_rag(db_sess, u_id, txt, f_name, c_type):
                rag_pipeline = RAGPipeline(db_sess)
                rag_pipeline.ingest_document(
                    user_id=u_id,
                    text=txt,
                    metadata={
                        "filename": f_name,
                        "mime_type": c_type,
                        "source": "upload"
                    }
                )
            
            # Ejecutamos el RAG vectorial en un thread pool para no congelar peticiones concurrentes
            await run_in_threadpool(
                ingest_to_rag, db, user_uuid, final_text, original_filename, content_type
            )

        return {
            "text": resp_text,
            "filename": original_filename,
            "status": "extracted_successfully"
        }

    except Exception as e:
        logger.exception("Error processing file in v2")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))