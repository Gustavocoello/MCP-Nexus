# src/services/agent/common/base_agent.py
import gc
from pathlib import Path
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
    def _inject_dynamic_rules(self, instruction: str) -> str:
        """
        Inyecta reglas base siempre, y reglas específicas según triggers en el input.
        """
        instruction_lower = instruction.lower()
        rules_dir = Path(__file__).parent / "rules"
        
        injected_content = ""

        # 1. REGLA OBLIGATORIA (Siempre se inyecta)
        anti_hallucination_path = rules_dir / "anti_hallucination.md"
        if anti_hallucination_path.exists():
            injected_content += anti_hallucination_path.read_text(encoding="utf-8") + "\n\n"

        # 2. TRIGGERS PARA SKILLS
        skill_triggers = ["skill", "crea una skill", "descarga una skill", "actualiza la skill"]
        if any(trigger in instruction_lower for trigger in skill_triggers):
            skills_path = rules_dir / "skills_workflow.md"
            if skills_path.exists():
                print(f"[{self.name}] Trigger detectado: Inyectando reglas de Skills.")
                injected_content += skills_path.read_text(encoding="utf-8") + "\n\n"

        # 3. TRIGGERS PARA ARCHIVOS (Files)
        file_triggers = ["archivo", "carpeta", "file", "folder", "directorio", "renombra", "elimina", "borra", "dónde está", "busca"]
        if any(trigger in instruction_lower for trigger in file_triggers):
            files_path = rules_dir / "file_operations.md"
            if files_path.exists():
                print(f"[{self.name}] Trigger detectado: Inyectando reglas de Archivos.")
                injected_content += files_path.read_text(encoding="utf-8") + "\n\n"

        # Si sumamos alguna regla, reconstruimos el prompt
        if injected_content:
            return f"""
                {instruction}

                ==================================================
                SYSTEM INJECTION (CRITICAL BEHAVIOR RULES):
                {injected_content}
                ==================================================
                """
        return instruction
    
    # --- Make the action ---
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
        # Inyectamos reglas para el agente
        instruction = self._inject_dynamic_rules(instruction)
        # Inyectamos el sdd de OpenSepc
        instruction = self._inject_openspec_skill(instruction)

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

    # --- STREAMING ---
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
            "recursion_limit": 50
        }
        
        # LangGraph devuelve eventos (chunks) paso a paso
        return self.app.stream(
            {"messages": [HumanMessage(content=instruction)]},
            config=config,
            stream_mode="values"
        )
    # --- Inyect Rules ---
    
    
        
    # --- SDD + OpenSeps --- 
    def _inject_openspec_skill(self, instruction: str) -> str:
        """
        Intercepta comandos como /opsx:propose y carga las instrucciones
        y skills de OpenSpec desde la arquitectura del backend.
        """
        # __file__ es base_agent.py. 
        # .parent es 'common'
        # .parent.parent es 'agent'
        agent_dir = Path(__file__).parent.parent 
        
        # Mapeamos el comando con su archivo .md y su respectivo SKILL.md
        command_map = {
            "/opsx:propose": {
                "cmd": agent_dir / "common" / "commands" / "opsx" / "propose.md",
                "skill": agent_dir / "skills" / "openspec-propose" / "SKILL.md"
            },
            "/opsx:apply": {
                "cmd": agent_dir / "common" / "commands" / "opsx" / "apply.md",
                "skill": agent_dir / "skills" / "openspec-apply-change" / "SKILL.md"
            },
            "/opsx:archive": {
                "cmd": agent_dir / "common" / "commands" / "opsx" / "archive.md",
                "skill": agent_dir / "skills" / "openspec-archive-change" / "SKILL.md"
            },
            "/opsx:explore": {
                "cmd": agent_dir / "common" / "commands" / "opsx" / "explore.md",
                "skill": agent_dir / "skills" / "openspec-explore" / "SKILL.md"
            },
            "/opsx:sync": {
                "cmd": agent_dir / "common" / "commands" / "opsx" / "sync.md",
                "skill": agent_dir / "skills" / "openspec-sync-specs" / "SKILL.md"
            }
        }

        for cmd_trigger, paths in command_map.items():
            if instruction.strip().startswith(cmd_trigger):
                print(f"[{self.name}] Comando OpenSpec detectado: {cmd_trigger}")
                
                cmd_content = ""
                skill_content = ""
                
                # Leemos el comando de /common/
                if paths["cmd"].exists():
                    cmd_content = paths["cmd"].read_text(encoding="utf-8")
                else:
                    print(f"Advertencia: No se encontró {paths['cmd']}")
                    
                # Leemos el skill de /skills/
                if paths["skill"].exists():
                    skill_content = paths["skill"].read_text(encoding="utf-8")
                else:
                    print(f"Advertencia: No se encontró {paths['skill']}")
                
                # Retornamos el Mega-Prompt vitaminado
                return f"""
                    Eres un agente ejecutando un flujo de Spec-Driven Development.

                    === INSTRUCCIONES DEL COMANDO ===
                    {cmd_content}

                    === HABILIDAD REQUERIDA (CÓMO HACERLO) ===
                    {skill_content}

                    === PETICIÓN DEL USUARIO ===
                    {instruction}
                    """
        
        # Si no empieza con /opsx, devolvemos la instrucción normal
        return instruction
    
    # --- SDD + JARVIS ---
    def process_sdd_request(self, instruction: str, user_id: str, chat_id: str = None) -> dict:
        """
        Procesa una solicitud en modo SDD (Spec-Driven Development)
        Combina el flujo interactivo de SDD con OpenSpec como herramienta
        """
        
        # Paso 1: Detectar si es una solicitud SDD
        sdd_triggers = ["use sdd", "hazlo con sdd", "modo sdd", "usar sdd"]
        is_sdd = any(trigger in instruction.lower() for trigger in sdd_triggers)
        
        if not is_sdd:
            # Modo normal: usa el flujo existente
            return self.run_task(instruction, user_id, chat_id)
        
        # Paso 2: Extraer la tarea real (quitar "use sdd")
        task_description = instruction.lower()
        for trigger in sdd_triggers:
            task_description = task_description.replace(trigger, "").strip()
        
        # Paso 3: Iniciar flujo SDD
        return self._start_sdd_workflow(task_description, user_id, chat_id)

    def _start_sdd_workflow(self, task: str, user_id: str, chat_id: str) -> dict:
        """
        Inicia el flujo SDD con las 6 fases:
        EXPLORE → PROPOSE → SPEC → DESIGN → IMPLEMENT → VERIFY
        """
        
        # FASE 1: EXPLORE - Recopilar contexto
        explore_prompt = f"""🔍 **FASE 1: EXPLORACIÓN - Recopilando Contexto**

    Estoy analizando tu solicitud: "{task}"

    Por favor, ayúdame a entender mejor:

    1. ¿Qué problema específico quieres resolver?
    2. ¿Hay archivos específicos que deba revisar?
    3. ¿Hay restricciones o requisitos especiales?

    Responde con esta información para continuar..."""

        return {
            "output": explore_prompt,
            "status": "sdd_explore",
            "metadata": {
                "sdd_phase": "explore",
                "task": task,
                "user_id": user_id,
                "chat_id": chat_id
            }
        }

    def process_sdd_response(self, user_response: str, context: dict) -> dict:
        """
        Procesa la respuesta del usuario en cada fase del SDD
        """
        current_phase = context.get("sdd_phase")
        task = context.get("task")
        
        if current_phase == "explore":
            # Guardar requisitos y pasar a PROPOSE
            return self._sdd_propose_phase(task, context, user_response)
        
        elif current_phase == "propose":
            # Procesar dónde guardar (chat o local)
            if "local" in user_response.lower():
                # Ejecutar OpenSpec CLI
                return self._execute_openspec_propose(task, context)
            else:
                # Modo chat - solo mostrar plan
                return self._sdd_chat_mode_plan(task, context)
        
        elif current_phase == "spec":
            # Procesar especificaciones
            return self._sdd_design_phase(task, context, user_response)
        
        # ... más fases

    def _execute_openspec_propose(self, task: str, context: dict) -> dict:
        """
        Ejecuta el comando de OpenSpec para crear el proposal
        """
        import subprocess
        import os
        
        # Nombre del proposal (sanitizado)
        proposal_name = task.lower().replace(" ", "-")[:50]
        
        # Ejecutar openspec propose
        try:
            result = subprocess.run(
                ["openspec", "propose", proposal_name],
                capture_output=True,
                text=True,
                cwd=os.getcwd()  # Directorio raíz donde está openspec/
            )
            
            if result.returncode == 0:
                # Éxito - leer los archivos creados
                proposal_path = f"openspec/changes/{proposal_name}/"
                
                return {
                    "output": f"""✅ **Proposal creado exitosamente**

                    He creado la estructura de OpenSpec en:
                    `{proposal_path}`

                    Archivos creados:
                    - proposal.md
                    - design.md  
                    - tasks.md

    ¿Deseas que continúe con el flujo SDD revisando estos archivos?""",
                    "status": "sdd_spec",
                    "metadata": {
                        "sdd_phase": "spec",
                        "proposal_name": proposal_name,
                        "proposal_path": proposal_path,
                        **context
                    }
                }
            else:
                return {
                    "output": f"⚠️ Error al crear proposal: {result.stderr}",
                    "status": "error"
                }
                
        except Exception as e:
            return {
                "output": f"⚠️ Error ejecutando OpenSpec: {str(e)}",
                "status": "error"
            }