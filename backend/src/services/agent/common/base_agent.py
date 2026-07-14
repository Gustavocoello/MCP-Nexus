# src/services/agent/common/base_agent.py

import logging
import warnings

# Ignora específicamente esta advertencia de LangGraph/LangChain
warnings.filterwarnings("ignore", message=".*allowed_objects.*")
warnings.filterwarnings("ignore", category=UserWarning, module="langgraph.checkpoint.base")
logging.getLogger('langgraph').setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

import os 
import gc
import time
from pathlib import Path
from langchain_openai import ChatOpenAI
from langgraph.types import interrupt
from langgraph.errors import GraphInterrupt
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver 
from langchain_community.callbacks import get_openai_callback
from langchain_core.messages import SystemMessage, trim_messages, HumanMessage
from langchain_core.runnables import RunnableConfig
from psycopg_pool import ConnectionPool
from langgraph.checkpoint.postgres import PostgresSaver
from src.database.settings.connection import DATABASE_URL  # Importamos TU URL ya resuelta

from .helpers import _generate_feature_name
from .tools.system_tools import invoke_skill
from src.core.logging import get_logger 
from src.database.models.models import TokenLog 
from src.database.settings.connection import get_db
from src.services.agent.jarvis.spec.sdd_orchestrator import SDDOrchestrator
from .utils.session_manager import create_agent_session, complete_session, fail_session 


logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = get_logger("Base_agent")

# ==========================================
# CONFIGURACIÓN DEL POOL DE POSTGRES (GLOBAL)
# ==========================================
def _get_clean_pg_url(url_obj) -> str:
    """
    Limpia la URL de SQLAlchemy para que sea compatible con psycopg_pool.
    Evita que SQLAlchemy censure el password (***).
    """
    if hasattr(url_obj, "render_as_string"):
        url_str = url_obj.render_as_string(hide_password=False)
    else:
        url_str = str(url_obj)
                
    if url_str.startswith("postgresql+"):
        return "postgresql://" + url_str.split("://", 1)[1]
            
    return url_str

    # Creamos la piscina de conexiones UNA SOLA VEZ para toda la aplicación
_clean_db_url = _get_clean_pg_url(DATABASE_URL)

_postgres_pool = ConnectionPool(
        conninfo=_clean_db_url, 
        min_size=1, 
        max_size=5, 
        timeout=10.0,
        kwargs={"autocommit": True}
    )

class BaseAgent:
    """
    Base class for all agents (LangGraph Version).
    Handles the ReAct engine, state checkpointing, and tool injection.
    """
    name: str = "BaseAgent"

    def __init__(self, llm: ChatOpenAI, tools: list, template: str):
        self.llm = llm.bind(parallel_tool_calls=False)
        global_tools = [invoke_skill]
        self.tools =  tools + global_tools
        self.system_prompt = template
        self.memory = PostgresSaver(_postgres_pool)
        self.memory.setup()
        self.sdd = SDDOrchestrator(jarvis_agent=self)
        self.app = create_react_agent(          # Construimos el Grafo del Agente
            model=self.llm,
            tools=self.tools,
            checkpointer=self.memory,            
            prompt=self._dynamic_state_modifier,  # Reemplaza el PromptTemplate
        )

    
    # --- Save Logs ---
    def _save_tokens(self, user_id: str, chat_id: str, input_tokens: int, output_tokens: int, response_time: float, status: str = "success"):
        """Función auxiliar para guardar el log en la base de datos"""
        try:
            db = next(get_db())
            
            # LangChain a veces guarda el modelo en llm.model_name o llm.model
            model_name = getattr(self.llm, "model_name", getattr(self.llm, "model", "unknown-model"))
                
            log = TokenLog(
                user_id=user_id,
                chat_id=chat_id,
                model_name=model_name,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
                response_time_sec=round(response_time, 2),
                status=status
            )
            db.add(log)
            db.commit()
        except Exception as e:
            logger.error(f"Error guardando TokensLog en BD: {str(e)}")
    
    # --- Inject Rules --- 
    def _dynamic_state_modifier(self, state: dict, config: RunnableConfig = None) -> list:
        """
        Interviene antes de enviar la data al LLM. 
        Inyecta reglas de forma EFÍMERA en el SystemPrompt.
        """
        config = config or {}
        
        # 1. Base System Prompt
        sys_content = self.system_prompt
        
        # 2. Extraer las reglas dinámicas desde la configuración (pasadas en stream/run_task)
        dynamic_rules = config.get("configurable", {}).get("dynamic_rules", "")
        if dynamic_rules:
            sys_content += f"\n\n=== Dynamic Rules (NO HALLUCINATE) ===\n{dynamic_rules}\n=========================================="
        
        # 3. (OPCIONAL) Proteger el historial podando si supera 4000 tokens
        # trimmed_messages = trim_messages(state["messages"], max_tokens=4000, strategy="last", token_counter=self.llm)
        
        # 4. DEBUG DE TOKENS: Imprimir en CLI para que veas qué está consumiendo
        # sys_len = len(sys_content) // 4
        # msg_len = sum(len(str(m.content)) // 4 for m in state["messages"])
        # print(f"\n[DEBUG TOKENS] System: ~{sys_len} | Historial: ~{msg_len}")
        
        return [SystemMessage(content=sys_content)] + state["messages"]
    
    def _extract_dynamic_rules(self, instruction: str) -> tuple[str, str, dict]:
        """
        Retorna: (instruccion_limpia, contenido_inyectable, contexto_skills)
        Ya NO muta el prompt del usuario directamente.
        """
        injected_content = ""
        instruction_lower = instruction.lower()
        context = {"rules": [], "skills": [], "mcp": 0}
        
        # -- RULES --
        rules_dir = Path(__file__).parent / "rules"
        agent_rules_dir = Path(__file__).parent.parent / self.name.lower() / "rules" 
        
        # 1. Regla obligatoria
        global_rule = rules_dir / "anti_hallucination.md"
        if global_rule.exists():
            injected_content += global_rule.read_text(encoding="utf-8") + "\n\n"
            context["rules"].append("anti_hallucination")
            
        agent_rule = agent_rules_dir / "anti_hallucination.md"
        if agent_rule.exists():
            injected_content += agent_rule.read_text(encoding="utf-8") + "\n\n"
            context["rules"].append(f"anti_hallucination_{self.name.lower()}")

        # 2.Triggers para Skills
        skill_triggers = ["skill", "crea una skill", "descarga una skill", "actualiza la skill"]
        if any(trigger in instruction_lower for trigger in skill_triggers):
            skills_path = rules_dir / "skills_workflow.md"
            if skills_path.exists():
                injected_content += skills_path.read_text(encoding="utf-8") + "\n\n"
                context["rules"].append("skills_workflow")

        # 3. Treiggers para files
        file_triggers = ["archivo", "carpeta", "file", "folder", "directorio", "renombra", "elimina", "borra", "dónde está", "busca"]
        if any(trigger in instruction_lower for trigger in file_triggers):
            files_path = rules_dir / "file_operations.md"
            if files_path.exists():
                injected_content += files_path.read_text(encoding="utf-8") + "\n\n"
                context["rules"].append("file_operations")

        return instruction, injected_content, context
    
    # --- Make the action ---
    def run_task(self, instruction: str, user_id: str, chat_id: str = None, thread_id: str = None) -> dict:
        
        # Inyectamos reglas para el agente
        original_instruction = instruction
        instruction, dynamic_rules, context = self._extract_dynamic_rules(instruction)
        self._last_context = context
        
        # ==========================================
        # INTERCEPTOR SDD (SPEC-DRIVEN DEVELOPMENT)
        # ==========================================
        sdd_triggers = ["use sdd", "modo sdd", "sdd", "usar sdd"]
        is_sdd_trigger = any(t in instruction.lower() for t in sdd_triggers)
        sdd_exit_triggers = ["salir del modo sdd", "salir sdd", "cancelar sdd", "abortar sdd", "exit sdd", "salir"]
        
        # Si ya hay un flujo en proceso, lo atrapa y no llama a LangGraph LLM
        if self.sdd.is_sdd_active():
            if any(t in instruction.lower() for t in sdd_exit_triggers):
                self.sdd.current_session = None
                return {
                    "output": "Saliste del modo SDD. ¿En qué más te ayudo?",
                    "status": "completed",
                    "metadata": {"agent": self.name, "sdd_mode": False}
                }

            start_time = time.time()
            sdd_response = self.sdd.process_user_response(instruction)
            return {
                "output": sdd_response,
                "status": "completed",
                "metadata": {"agent": self.name, "time_sec": round(time.time() - start_time, 2), "sdd_mode": True}
            }
            
        # Si el usuario activa SDD por primera vez en este prompt
        elif is_sdd_trigger:
            start_time = time.time()
            clean_instruction = instruction
            for t in sdd_triggers: clean_instruction = clean_instruction.lower().replace(t, "").strip()
            
            sdd_response = self.sdd.start_sdd(clean_instruction)
            return {
                "output": sdd_response,
                "status": "completed",
                "metadata": {"agent": self.name, "time_sec": round(time.time() - start_time, 2), "sdd_mode": True}
            }
        # ==========================================
        
        # 1. CREAR LA SESIÓN EN BASE DE DATOS (Aparece en tu Frontend Panel)
        session_id = create_agent_session(
            user_id=user_id,
            task_description=original_instruction,
            chat_id=chat_id,
            thread_id=thread_id,
            assigned_agent=self.name.lower(),
            timeout_seconds=3600
        )
        
        current_thread_id = thread_id if thread_id else session_id
        
        # Configurar LangGraph con el session_id generado
        config = {
            "configurable": {
                "thread_id": current_thread_id or "default-thread",
                "user_id": user_id,
                "session_id": thread_id,
                "dynamic_rules": dynamic_rules
            },
            "recursion_limit": 15 # Limitar recursión para evitar loops infinitos
        }
        
        # Variables para métricas
        start_time = time.time()
        response_time = 0.0

        try:
            # MAGIA: Envolvemos la llamada al agente en el callback
            with get_openai_callback() as cb:
                state = self.app.invoke(
                    {"messages": [HumanMessage(content=instruction)]}, 
                    config=config
                )
            
            # Calculamos tiempo final
            response_time = time.time() - start_time
            
            # Si el cb falla (ej. Gemini), usamos una estimación rápida
            in_tok = cb.prompt_tokens if cb.total_tokens > 0 else (len(instruction) // 4)
            out_tok = cb.completion_tokens if cb.total_tokens > 0 else (len(state["messages"][-1].content) // 4)

            # Guardar en Base de Datos (TokensLog)
            self._save_tokens(
                user_id=user_id,
                chat_id=chat_id,
                input_tokens=in_tok,
                output_tokens=out_tok,
                response_time=response_time,
                status="success"
            )

            final_message = state["messages"][-1].content
            complete_session(session_id=session_id, result_summary=final_message)
            
            # DEVOLVEMOS LOS TOKENS PARA EL FRONTEND
            return {
                "output": final_message, 
                "status": "completed",
                "metadata": {
                    "agent": self.name,
                    "tokens": {
                        "prompt": cb.prompt_tokens,
                        "completion": cb.completion_tokens,
                        "total": cb.total_tokens,
                        "cost_usd": round(cb.total_cost, 6) # LangChain calcula el costo en $ por ti!
                    },
                    "time_sec": round(response_time, 2)
                }
            }

        except GraphInterrupt as e:
            response_time = time.time() - start_time
            print(f"\n[HITL INTERRUPT] El agente se detuvo: {str(e)}")
            return {"output": str(e), "status": "waiting_approval", "session_id": session_id}
            
        except Exception as e:
            response_time = time.time() - start_time
            fail_session(session_id=session_id, error_message=str(e))
            
            return {"output": f"Error interno: {str(e)}", "status": "failed"}

        finally:
            gc.collect()

    # --- STREAMING ---
    def stream_task(self, instruction: str, user_id: str, chat_id: str = None, thread_id: str = None):
        """
        Versión Streaming compatible con LangGraph
        """
        original_instruction = instruction
        instruction, dynamic_rules, context = self._extract_dynamic_rules(instruction)
        self._last_context = context
        
        session_id = create_agent_session(
            user_id=user_id,
            task_description=original_instruction,
            chat_id=chat_id,
            thread_id=thread_id,
            assigned_agent=self.name.lower(),
            timeout_seconds=3600
        )
        self._last_session_id = session_id  
        current_thread_id = thread_id if thread_id else session_id
        config = {
            "configurable": {
                "thread_id": current_thread_id or "default-thread",
                "user_id": user_id,
                "session_id": thread_id,
                "dynamic_rules": dynamic_rules
            }, 
            "recursion_limit": 35
        }
        inputs = {"messages": [("user", instruction)]}
        # Para ver el tiempo de ejecucion
        start_time = time.time()
        final_message_content = ""
        
        try:
            # 1. Ejecutamos el stream y cedemos los datos al CLI/UI
            for event in self.app.stream(inputs, config=config, stream_mode="values"):
                
                # Extraemos el texto más reciente para luego contar tokens
                if "messages" in event and len(event["messages"]) > 0:
                    last_msg = event["messages"][-1]
                    if last_msg.type == "ai":
                        final_message_content = last_msg.content
                
                # Cedemos el evento para que tu CLI lo siga leyendo tal cual lo hacía antes
                yield event
            
            # 2. Finalizó el stream con éxito
            response_time = time.time() - start_time
            
            # LangGraph en streaming a veces no devuelve uso exacto de tokens según el LLM (1 token ≈ 4 caracteres)
            est_input_tokens = len(instruction) // 4
            est_output_tokens = len(final_message_content) // 4

            # Intentamos extraer métricas exactas si el LLM las proveyó al final
            if "messages" in event and event["messages"]:
                last_msg = event["messages"][-1]
                if hasattr(last_msg, 'response_metadata') and 'token_usage' in last_msg.response_metadata:
                    usage = last_msg.response_metadata['token_usage']
                    est_input_tokens = usage.get('prompt_tokens', est_input_tokens)
                    est_output_tokens = usage.get('completion_tokens', est_output_tokens)

            # 3. Guardar logs con CHAT_ID
            self._save_tokens(
                user_id=user_id,
                chat_id=chat_id,
                input_tokens=est_input_tokens,
                output_tokens=est_output_tokens,
                response_time=response_time,
                status="success"
            )
            
            # 4. Cerrar sesión
            complete_session(session_id=session_id, result_summary=final_message_content)

        except GraphInterrupt as e:
            # Caso de HITL (Esperando aprobación humana)
            response_time = time.time() - start_time
            print(f"\n[HITL INTERRUPT] El agente se detuvo esperando aprobación")
            yield {"interrupt": str(e), "status": "waiting_approval", "session_id": session_id}
            
        except Exception as e:
            # Caso de error
            response_time = time.time() - start_time
            self._save_tokens(
                user_id=user_id, chat_id=chat_id, 
                input_tokens=len(instruction)//4, output_tokens=0, 
                response_time=response_time, status="error"
            )
            fail_session(session_id=session_id, error_message=str(e))
            yield {"error": str(e), "status": "failed"}
            
        finally:
            gc.collect()
    
    
        