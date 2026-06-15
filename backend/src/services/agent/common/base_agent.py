# src/services/agent/common/base_agent.py
import gc
import logging
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.prebuilt import create_react_agent
from  src.services.agent.Koda.tools.hitl import create_agent_session, complete_session, fail_session 
from langgraph.checkpoint.memory import MemorySaver 
from langgraph.errors import NodeInterrupt

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
        
        # Checkpointer: Es la "memoria" que permite pausar y reanudar el Grafo
        self.memory = MemorySaver()
        
        # Construimos el Grafo del Agente
        self.app = create_react_agent(
            model=self.llm,
            tools=self.tools,
            state_modifier=self.system_prompt, # Reemplaza el PromptTemplate
            checkpointer=self.memory # Fundamental para el HITL
        )

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

        try:
            # Koda empieza a trabajar
            state = self.app.invoke(
                {"messages": [HumanMessage(content=instruction)]}, 
                config=config
            )
            
            # Koda terminó sin interrupciones destructivas
            final_message = state["messages"][-1].content
            
            complete_session(session_id=session_id, result_summary=final_message)
            
            return {"output": final_message, "status": "completed"}

        except NodeInterrupt as e:
            print(f"\n[HITL INTERRUPT] El agente se detuvo: {e}")
            return {"output": str(e), "status": "waiting_approval", "session_id": session_id}
            
        except Exception as e:
            fail_session(session_id=session_id, error_message=str(e))
            return {"output": f"Error interno: {str(e)}", "status": "failed"}

        finally:
            import gc
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