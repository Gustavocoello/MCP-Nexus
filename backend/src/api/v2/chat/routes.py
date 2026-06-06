from flask import Blueprint, jsonify, Response, request, stream_with_context, g
from src.services.auth.auth.auth_middleware import auth_required

# Importa tus funciones existentes
from src.core.logging import get_logger
from src.database.settings.connection import SessionLocal
from src.database.models import Chat, Message
from src.core.time_helper import get_now
from src.services.cache import SidebarCache, ChatCache
from src.services.rag.pipeline import RAGPipeline
from src.database.settings.connection import SessionLocal
from src.services.llm.chat.chat_service import get_langchain_history 
from src.services.integrations.azure.azure_vision import analyze_image_with_azure
from src.services.integrations.microsoft.markitdown_extractor import extract_text_from_file

# IMPORTANTE: Aquí debes importar la lista de tools que creaste con @tool en tu tools_registry.py
from src.services.agent.jarvis.agent import get_jarvis

logger = get_logger("chat_service")

## -------------- Mensajes de la IA con memoria - v2 -----------
chat_bp = Blueprint('chat_v2', __name__)

@chat_bp.route('/<chat_id>/message/', methods=['POST'], strict_slashes=False)
@auth_required
def send_message_v2(chat_id):
    db_session = SessionLocal()
    try:
        # 1. Buscar o crear chat (Igual que antes)
        chat = db_session.query(Chat).filter(
            Chat.id == chat_id, 
            Chat.user_id == g.user_id, 
            Chat.app_id == g.app_id
            ).first()

        if not chat:
            chat = Chat(
                id=chat_id, 
                user_id=g.user_id, 
                app_id=g.app_id, 
                title="Sin titulo"
            )
            db_session.add(chat)
            db_session.flush()
        elif chat.user_id != g.user_id:
            return jsonify({"error": "Access denied"}), 403

        # 2. Validar input
        user_text = (request.json.get("text") or "").strip()
        if not user_text:
            return jsonify({"error": "Empty message"}), 400

        # 3. Guardar mensaje del usuario
        chat.updated_at = get_now()
        user_message = Message(
            chat_id=chat.id, 
            role="user", 
            content=user_text
        )
        db_session.add(user_message)

        # 4. Manejar hidden_context (imágenes/archivos)
        hidden_context = request.json.get("hidden_context", "").strip()
        if hidden_context:
            db_session.query(Message).filter_by(
                chat_id=chat.id, 
                role="context"
            ).delete()
            context_msg = Message(
                chat_id=chat.id, 
                role="context", 
                content=hidden_context
            )
            db_session.add(context_msg)
            db_session.commit()

        # 5. Obtener mensajes recientes (Igual que antes)
        recent = (
            db_session.query(Message)
            .filter(
                Message.chat_id == chat.id,
                Message.role != "context",
                Message.id != user_message.id # excluye el que acabas de insertar
            )
            .order_by(Message.created_at.desc())
            .limit(10) # Tu MAX_RAW
            .all()[::-1]
        )

        # 6. NUEVO: Construir historial de LangChain usando tu función
        langchain_history = get_langchain_history(
            chat=chat, 
            recent=recent, 
            hidden_context=hidden_context
        )

        # 7. Agent
        jarvis_agent = get_jarvis(g.user_id) # Jarvis el Agente Orquestaddor

        # 8. Auto-generar título
        if not chat.title or chat.title == "Sin titulo":
            words = user_text.split()
            chat.title = " ".join(words[:10]) + ("..." if len(words) > 10 else "")
            db_session.add(chat)
            db_session.commit()
            SidebarCache.invalidate_user(g.user_id)

        # 9. streaming response del agente
        def generate():
            gen_session = SessionLocal()
            try:
                full_reply = ""
                
                # 1. Apenas empieza, le decimos al usuario que está pensando
                yield "[THOUGHT] Thinking...\n"
                
                # AgentExecutor.stream arroja diccionarios con el estado paso a paso
                for chunk in jarvis_agent.stream_task({
                    "input": user_text,
                    "chat_history": langchain_history
                }):
                    # A. El agente decidió usar una herramienta
                    if "actions" in chunk:
                        for action in chunk["actions"]:
                            yield f"[THOUGHT] Preparing action...\n"
                            yield f"[THOUGHT] Calling tool: {action.tool}...\n"
                    
                    # B. La herramienta terminó de ejecutarse y devolvió resultados
                    elif "steps" in chunk:
                        for step in chunk["steps"]:
                            yield f"[THOUGHT] Tool {step.action.tool} execution completed.\n"
                            yield "[THOUGHT] Analyzing tool results...\n"
                    
                    # C. El agente terminó de razonar y empieza a dar la respuesta final al usuario
                    elif "output" in chunk:
                        # Si es el primer fragmento de la respuesta final, cerramos el pensamiento
                        if not full_reply:
                            yield "[THOUGHT] Thought process completed.\n"
                        
                        text = chunk["output"]
                        full_reply += text
                        yield text # Texto final de Jarvis (sin etiqueta)

                # Guardar respuesta final en BD
                inner_chat = gen_session.get(Chat, chat_id)
                inner_chat.updated_at = get_now()

                new_msg = Message(
                    chat_id=chat_id, 
                    role="assistant", 
                    content=full_reply
                )
                gen_session.add(new_msg)
                gen_session.commit()

                ChatCache.append_message(chat_id, {
                    "id": new_msg.id,
                    "role": "assistant",
                    "content": full_reply,
                    "created_at": get_now().isoformat()
                })

            except Exception as e:
                gen_session.rollback()
                logger.exception("Error during agent stream")
                yield f"\n[THOUGHT] Process interrupted due to error.\n"
                yield f"\n[ERROR] {str(e)}"
            finally:
                gen_session.close()

        # El frontend recibe text/plain con los [THOUGHT] en inglés y literales
        return Response(stream_with_context(generate()), content_type="text/plain")

    except Exception as e:
        db_session.rollback()
        logger.exception("Error in send_message")
        return jsonify({"error": str(e)}), 500
    finally:
        db_session.close()
        
        
# -------- AZURE IMAGES 10k IMAGES + RAG ----------------
@chat_bp.route('/extract_file', methods=['POST'])
@auth_required
def extract_file():
    db_session = SessionLocal()
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Empty filename'}), 400

    original_filename = file.filename
    content_type = file.content_type
    file_bytes = file.read()
    final_text = ""
    user_uuid = g.user_id # Extraemos el user_id de la sesión

    try:
        if content_type.startswith("image/"):
            # Llama a nuestro nuevo servicio limpio
            final_text = analyze_image_with_azure(file_bytes, user_id=user_uuid)
            resp_text = f"Image '{original_filename}':\n\n{final_text}"
        else:
             # Usa MarkItDown para TODO lo demás (PDF, Word, Excel...)
            from io import BytesIO
            file_stream = BytesIO(file_bytes)
            final_text = extract_text_from_file(file_stream, original_filename)
            resp_text = f"Document '{original_filename}':\n\n{final_text}"
        
        if final_text and final_text.strip():
            rag_pipeline = RAGPipeline(db_session)
            rag_pipeline.ingest_document(
                user_id=user_uuid,
                text=final_text,
                metadata={
                    "filename": original_filename,
                    "mime_type": content_type,
                    "source": "upload"
                }
            )

        # Retornamos inmediatamente el texto extraído al Frontend
        return jsonify({
            "text": resp_text,
            "filename": original_filename,
            "status": "extracted_successfully"
        })

    except Exception as e:
        logger.exception("Error processing file")
        return jsonify({'error': str(e)}), 500