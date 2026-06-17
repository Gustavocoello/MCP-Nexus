# src/services/agent/common/base_agent.py
import gc
import logging
import time
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.prebuilt import create_react_agent
from  src.services.agent.Koda.tools.hitl import create_agent_session, complete_session, fail_session 
from langgraph.checkpoint.memory import MemorySaver 
from langgraph.errors import NodeInterrupt
from langchain_community.callbacks import get_openai_callback

from src.database.models.models import TokenLog 
from src.database.settings.connection import get_db


logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

class BaseAgent:
    """
    Base class for all agents (LangGraph Version).
    Handles the ReAct engine, state checkpointing, and tool injection.
    """
    name: str = "BaseAgent"

    def __init__(self, llm: ChatOpenAI, tools: list, template: str):
        self.llm = llm
        self.tools = tools
        self.system_prompt = template
        self.memory = MemorySaver()
        self.app = create_react_agent(          # Construimos el Grafo del Agente
            model=self.llm,
            tools=self.tools,
            state_modifier=self.system_prompt,  # Reemplaza el PromptTemplate
            checkpointer=self.memory            # Fundamental para el HITL
        )

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
    
    def run_task(self, instruction: str, user_id: str, chat_id: str = None, thread_id: str = None) -> dict:
        
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
            "recursion_limit": 25 # Limitar recursión para evitar loops infinitos
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

        except NodeInterrupt as e:
            response_time = time.time() - start_time
            print(f"\n[HITL INTERRUPT] El agente se detuvo: {str(e)}")
            return {"output": str(e), "status": "waiting_approval", "session_id": session_id}
            
        except Exception as e:
            response_time = time.time() - start_time
            fail_session(session_id=session_id, error_message=str(e))
            
            return {"output": f"Error interno: {str(e)}", "status": "failed"}

        finally:
            gc.collect()

    def stream_task(self, instruction: str, user_id: str, session_id: str):
        """
        Versión Streaming compatible con LangGraph
        """
        config = {
            "configurable": {
                "thread_id": session_id,
                "user_id": user_id,
                "session_id": session_id
            }, 
            "recursion_limit": 25
        }
        
        # LangGraph devuelve eventos (chunks) paso a paso
        return self.app.stream(
            {"messages": [HumanMessage(content=instruction)]},
            config=config,
            stream_mode="values"
        )