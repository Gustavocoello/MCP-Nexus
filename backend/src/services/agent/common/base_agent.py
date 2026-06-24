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
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver 
from langchain_community.callbacks import get_openai_callback
from langchain_core.messages import SystemMessage, HumanMessage

from psycopg_pool import ConnectionPool
from langgraph.checkpoint.postgres import PostgresSaver
from src.database.settings.connection import DATABASE_URL  # Importamos TU URL ya resuelta

from .helpers import _generate_feature_name
from src.core.logging import get_logger 
from src.database.models.models import TokenLog 
from src.database.settings.connection import get_db
from src.services.agent.jarvis.spec.sdd_orchestrator import SDDOrchestrator
from .utils.session_manager import create_agent_session, complete_session, fail_session 


logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = get_logger("Base_agent")

class BaseAgent:
    """
    Base class for all agents (LangGraph Version).
    Handles the ReAct engine, state checkpointing, and tool injection.
    """
    name: str = "BaseAgent"

    def __init__(self, llm: ChatOpenAI, tools: list, template: str):
        self.llm = llm.bind(parallel_tool_calls=False)
        self.tools = tools
        self.system_prompt = template
        self.memory = MemorySaver()
        self.sdd = SDDOrchestrator(jarvis_agent=self)
        self.app = create_react_agent(          # Construimos el Grafo del Agente
            model=self.llm,
            tools=self.tools,
            prompt=self.system_prompt,  # Reemplaza el PromptTemplate
            checkpointer=self.memory            # Fundamental para el HITL
        )

    # --- Save Logs ---
    def _save_llm_log(self, user_id, chat_id, cb, response_time, status="success"):
        """Función auxiliar para guardar el log en la base de datos"""
        try:
            db = next(get_db())
            # Extraer el nombre del modelo (ej. "gpt-4o")
            model_name = getattr(self.llm, "model_name", "unknown-model")
                
            log = TokenLog(
                user_id=user_id,
                chat_id=chat_id,
                model_name=model_name,
                input_tokens=cb.prompt_tokens,
                output_tokens=cb.completion_tokens,
                total_tokens=cb.total_tokens,
                response_time_sec=round(response_time, 2),
                status=status
                )
            db.add(log)
            db.commit()
        except Exception as e:
            logging.error(f"Error guardando LLMLog en BD: {str(e)}")
    
    # --- Inject Rules --- 
    def _inject_dynamic_rules(self, instruction: str) -> tuple[str, dict]:
        """
        Inyecta reglas base siempre, y reglas específicas según triggers en el input.
        """
        injected_content = ""
        instruction_lower = instruction.lower()
        context = {"rules": [], "skills": 0, "mcp": 0}

        rules_dir = Path(__file__).parent / "rules"
        agent_rules_dir = Path(__file__).parent.parent \
                  / self.name.lower() / "rules" 
        
        # 1. REGLA OBLIGATORIA (Siempre se inyecta) General + Personal
        global_rule = rules_dir / "anti_hallucination.md" # Reglas Globales
        if global_rule.exists():
            injected_content += global_rule.read_text(encoding="utf-8") + "\n\n"
            context["rules"].append("anti_hallucination")
            
        agent_rule = agent_rules_dir / "anti_hallucination.md" # Reglas personales para cada agent
        if agent_rule.exists():
            injected_content += agent_rule.read_text(encoding="utf-8") + "\n\n"
            context["rules"].append(f"anti_hallucination_{self.name.lower()}")

        # 2. TRIGGERS PARA SKILLS - RULES
        skill_triggers = ["skill", "crea una skill", "descarga una skill", "actualiza la skill"]
        if any(trigger in instruction_lower for trigger in skill_triggers):
            skills_path = rules_dir / "skills_workflow.md"
            if skills_path.exists():
                logger.info(f"[{self.name}] Trigger detectado: Inyectando reglas de Skills.")
                injected_content += skills_path.read_text(encoding="utf-8") + "\n\n"
                context["rules"].append("skills_workflow")

        # 3. TRIGGERS PARA ARCHIVOS (Files)
        file_triggers = ["archivo", "carpeta", "file", "folder", "directorio", "renombra", "elimina", "borra", "dónde está", "busca"]
        if any(trigger in instruction_lower for trigger in file_triggers):
            files_path = rules_dir / "file_operations.md"
            if files_path.exists():
                logger.info(f"[{self.name}] Trigger detectado: Inyectando reglas de Archivos.")
                injected_content += files_path.read_text(encoding="utf-8") + "\n\n"
                context["rules"].append("file_operations")

        # Si sumamos alguna regla, reconstruimos el prompt
        if injected_content:
            modified = f"""
                {instruction}

                ==================================================
                SYSTEM INJECTION (CRITICAL BEHAVIOR RULES):
                {injected_content}
                ==================================================
                """
            return modified, context
        return instruction, context
    
    # --- Make the action ---
    def run_task(self, instruction: str, user_id: str, chat_id: str = None, thread_id: str = None) -> dict:
        
        # Inyectamos reglas para el agente
        instruction, context = self._inject_dynamic_rules(instruction)
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
            task_description=instruction,
            chat_id=chat_id,
            timeout_seconds=3600
        )
        
        current_thread_id = thread_id if thread_id else session_id
        
        # Configurar LangGraph con el session_id generado
        config = {
            "configurable": {
                "thread_id": current_thread_id,
                "user_id": user_id,
                "session_id": session_id
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
            
            # Guardar en Base de Datos (LLMLog)
            self._save_llm_log(user_id, chat_id, cb, response_time, status="success")

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

        except interrupt as e:
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
        instruction, context = self._inject_dynamic_rules(instruction)
        self._last_context = context
        
        session_id = create_agent_session(
            user_id=user_id,
            task_description=instruction,
            chat_id=chat_id,
            timeout_seconds=3600
        )
        self._last_session_id = session_id  
        current_thread_id = thread_id if thread_id else session_id
        config = {
            "configurable": {
                "thread_id": current_thread_id,
                "user_id": user_id,
                "session_id": session_id
            }, 
            "recursion_limit": 35
        }
        
        # LangGraph devuelve eventos (chunks) paso a paso
        return self.app.stream(
            {"messages": [HumanMessage(content=instruction)]},
            config=config,
            stream_mode="values"
        )
    
    
        