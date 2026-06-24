# backend/src/services/agent/jarvis/sdd_orchestrator.py
import json
import unicodedata
from enum import Enum, auto
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field, asdict

from src.services.agent.common.helpers import _generate_feature_name

class SDDPhase(str, Enum):
    IDLE = "IDLE"
    EXPLORE = "EXPLORE"
    PROPOSE = "PROPOSE"
    SPEC = "SPEC"
    DESIGN = "DESIGN"
    IMPLEMENT = "IMPLEMENT"
    VERIFY = "VERIFY"
    COMPLETE = "COMPLETE"
    ERROR = "ERROR"

class SaveLocation(str, Enum):
    CHAT = "chat"
    LOCAL = "local"

@dataclass
class SDDContext:
    """Contexto del flujo SDD serializable para LangGraph"""
    user_prompt: str
    feature_name: str = "feature-update" # Nombre para la carpeta openspec
    current_phase: str = SDDPhase.IDLE.value
    save_location: Optional[str] = None
    project_path: Optional[str] = None
    
    # Fase EXPLORE
    exploration_results: Dict = field(default_factory=dict)
    codebase_analysis: str = ""
    requirements: List[str] = field(default_factory=list)
    
    # Fase PROPOSE
    proposal: Dict = field(default_factory=dict)
    
    # Fase SPEC
    specifications: Dict = field(default_factory=dict)
    
    # Fase DESIGN
    design_doc: str = ""
    architecture: Dict = field(default_factory=dict)
    
    # Fase IMPLEMENT
    implementation_tasks: List[Dict] = field(default_factory=list)
    completed_tasks: List[str] = field(default_factory=list)
    
    # Fase VERIFY
    verification_results: Dict = field(default_factory=dict)
    issues_found: List[str] = field(default_factory=list)
    
    # Metadata (Strings para compatibilidad JSON con LangGraph)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SDDContext':
        if not data:
            return None
        return cls(**data)

# --- Helpers ---

def _is_affirmative(text: str) -> bool:
        """Normaliza tildes/mayúsculas y detecta respuestas afirmativas de forma robusta."""
        normalized = unicodedata.normalize('NFKD', text.lower().strip()).encode('ascii', 'ignore').decode('ascii')
        affirmatives = {"si", "ok", "yes", "dale", "correcto", "aprobado", "afirmativo", "vale", "perfecto"}
        return normalized in affirmatives

class SDDOrchestrator:
    """
    Orquestador del flujo SDD para el agente Jarvis
    Implementa: Prompt -> Gather Context -> Take Action -> Verify -> Repeat
    """
    
    def __init__(self, jarvis_agent, koda_agent=None):
        self.jarvis = jarvis_agent  # Tu orquestador actual
        self.koda = koda_agent      # Agente de código
        self.current_session: Optional[SDDContext] = None
    
    # Permite restaurar la sesión desde el estado de LangGraph
    def load_session(self, session_dict: dict):
        if session_dict:
            self.current_session = SDDContext.from_dict(session_dict)

    def start_sdd(self, user_prompt: str) -> str:
        """Inicia el flujo SDD"""
        # Generar un nombre de feature básico basado en el prompt
        feature_name = self._generate_feature_name(user_prompt)
        
        self.current_session = SDDContext(user_prompt=user_prompt, feature_name=feature_name)
        self.current_session.current_phase = SDDPhase.EXPLORE.value
        
        return self._generate_phase_prompt(SDDPhase.EXPLORE)
    
    def process_user_response(self, user_response: str) -> str:
        """Procesa la respuesta del usuario en cada fase"""
        if not self.current_session:
            return "No hay sesión SDD activa. Usa 'use sdd' para iniciar."
        
        current_phase = self.current_session.current_phase
        self.current_session.updated_at = datetime.now().isoformat()
        
        if current_phase == SDDPhase.EXPLORE.value:
            return self._process_explore_response(user_response)
        elif current_phase == SDDPhase.PROPOSE.value:
            return self._process_propose_response(user_response)
        elif current_phase == SDDPhase.SPEC.value:
            return self._process_spec_response(user_response)
        elif current_phase == SDDPhase.DESIGN.value:
            return self._process_design_response(user_response)
        elif current_phase == SDDPhase.IMPLEMENT.value:
            return self._process_implement_response(user_response)
        elif current_phase == SDDPhase.VERIFY.value:
            return self._process_verify_response(user_response)
        
        return "Fase no reconocida"
    
    def _generate_phase_prompt(self, phase: str) -> str:
        """Genera el prompt para cada fase"""
        prompts = {
            SDDPhase.EXPLORE.value: """🔍 **FASE 1: EXPLORACIÓN - Recopilando Contexto**
            Estoy analizando tu solicitud: "{user_prompt}"

            Por favor, ayúdame a entender mejor:
            1. ¿Qué problema específico quieres resolver?
            2. ¿Hay archivos específicos que deba revisar?
            3. ¿Hay restricciones o non-goals (cosas que NO queremos hacer)?

            Responde con esta información para continuar...""",
            
            SDDPhase.PROPOSE.value: """📋 **FASE 2: PROPUESTA - Dónde Guardar**
            He analizado tu solicitud. Ahora necesito saber:
            **¿Dónde quieres guardar los artefactos OpenSpec?**
            - **chat**: Solo en esta conversación (efímero, para pruebas)
            - **local**: Crear carpeta `openspec/changes/` en el proyecto (permanente)

            Responde con: "chat" o "local" """,
                        
                        SDDPhase.SPEC.value: """📝 **FASE 3: ESPECIFICACIONES**
            Estoy definiendo el Contrato Verificable (Specs)...
            He identificado:
            {specs}

            ¿Apruebas estas especificaciones? Responde "sí" para avanzar al Diseño, o indica qué cambiamos.""",
                        
                        SDDPhase.DESIGN.value: """🏗️ **FASE 4: DISEÑO - Arquitectura**
            **Arquitectura y Componentes tocados:**
            {design}

            ¿Estás de acuerdo con este diseño? Responde "sí" para generar el Tasks.md y empezar a codificar.""",
                        
                        SDDPhase.IMPLEMENT.value: """⚙️ **FASE 5: IMPLEMENTACIÓN ESTRICTA (TDD)**
            **Tareas a realizar (Unidades atómicas):**
            {tasks}

            Iniciando ejecución. Koda tomará una tarea a la vez aplicando RED -> GREEN -> REFACTOR...""",
                        
                        SDDPhase.VERIFY.value: """✅ **FASE 6: VERIFICACIÓN**
            He completado la implementación.
            **Resultados de verificación:**
            {verification}

            ¿Todo se ve correcto? Responde "sí" para finalizar el flujo SDD o "revisar" para iterar."""
        }
        
        context = self.current_session
        return prompts[phase].format(
            user_prompt=context.user_prompt,
            specs=json.dumps(context.specifications, indent=2) if context.specifications else "Generando...",
            design=context.design_doc if context.design_doc else "Generando...",
            tasks="\n".join([f"- [ ] {t['description']}" for t in context.implementation_tasks]) if context.implementation_tasks else "Generando...",
            verification=json.dumps(context.verification_results, indent=2) if context.verification_results else "Esperando pruebas..."
        )
    
    # ============ HANDLERS DE CADA FASE ============
    
    def _handle_explore(self):
        """Fase 1: Explorar - Recopilar contexto"""
        exploration = {
            "codebase_structure": self._analyze_codebase(),
            "relevant_files": self._find_relevant_files(),
            "existing_patterns": self._identify_patterns()
        }
        self.current_session.exploration_results = exploration
        return self._generate_phase_prompt(SDDPhase.EXPLORE.value)
    
    def _process_explore_response(self, user_response: str) -> str:
        """Procesa la respuesta del usuario en fase EXPLORE"""
        self.current_session.requirements = self._parse_requirements(user_response)
        self.current_session.current_phase = SDDPhase.PROPOSE.value
        return self._generate_phase_prompt(SDDPhase.PROPOSE.value)
    
    def _handle_propose(self):
        return self._generate_phase_prompt(SDDPhase.PROPOSE.value)
    
    def _process_propose_response(self, user_response: str) -> str:
        response_lower = user_response.lower().strip()
        
        if "chat" in response_lower:
            self.current_session.save_location = SaveLocation.CHAT.value
        elif "local" in response_lower:
            self.current_session.save_location = SaveLocation.LOCAL.value
            return """📁 **Ruta del Proyecto**
            ¿En qué ruta del proyecto quieres guardar los cambios?
            Ejemplo: `/home/user/mi-proyecto` o `./backend`"""
        
        self.current_session.current_phase = SDDPhase.SPEC.value
        self._generate_specifications()
        return self._generate_phase_prompt(SDDPhase.SPEC.value)
    
    def _handle_spec(self):
        return self._generate_phase_prompt(SDDPhase.SPEC.value)
    
    def _process_spec_response(self, user_response: str) -> str:
        if _is_affirmative(user_response):
            self.current_session.current_phase = SDDPhase.DESIGN.value
            self._generate_design()
            return self._generate_phase_prompt(SDDPhase.DESIGN.value)
        else:
            self.current_session.specifications["user_feedback"] = user_response
            return "Anotado. Modificando specs... \n" + self._generate_phase_prompt(SDDPhase.SPEC.value)
    
    def _handle_design(self):
        return self._generate_phase_prompt(SDDPhase.DESIGN.value)
    
    def _process_design_response(self, user_response: str) -> str:
        if _is_affirmative(user_response):
            self.current_session.current_phase = SDDPhase.IMPLEMENT.value
            if self.current_session.save_location == SaveLocation.LOCAL.value:
                self._save_openspec_files()
            return self._execute_implementation()
        else:
            self.current_session.design_doc += f"\nFeedback: {user_response}"
            return "Ajustando diseño... \n" + self._generate_phase_prompt(SDDPhase.DESIGN.value)
    
    def _handle_implement(self):
        return self._execute_implementation()
    
    def _process_implement_response(self, user_response: str) -> str:
        return "Implementación pausada o interactiva. Continuando con Koda..."
    
    def _handle_verify(self):
        return self._generate_phase_prompt(SDDPhase.VERIFY.value)
    
    def _process_verify_response(self, user_response: str) -> str:
        if _is_affirmative(user_response):
            self.current_session.current_phase = SDDPhase.COMPLETE.value
            return self._finalize_sdd()
        elif "revisar" in user_response.lower() or "cambiar" in user_response.lower():
            self.current_session.current_phase = SDDPhase.IMPLEMENT.value
            self._fix_issues()
            return "Reabriendo tareas de implementación para corregir...\n" + self._execute_implementation()
        else:
            return self._generate_phase_prompt(SDDPhase.VERIFY.value)
    
    # ============ MÉTODOS INTERNOS Y DE IMPLEMENTACIÓN ============
    
    def _analyze_codebase(self) -> Dict:
        """Analiza la estructura del codebase"""
        return {
            "structure": "Análisis de estructura",
            "files": ["file1.py", "file2.py"],
            "patterns": ["patrón1", "patrón2"]
        }
    
    def _find_relevant_files(self) -> List[str]:
        return []
    
    def _identify_patterns(self) -> List[str]:
        return []
    
    def _parse_requirements(self, user_response: str) -> List[str]:
        return [r.strip() for r in user_response.split("\n") if r.strip()]
    
    def _generate_specifications(self):
        """Genera especificaciones automáticamente"""
        # Aquí eventualmente Jarvis llamará a su LLM. Por ahora, mock estructural:
        prompt = f"""Basado en esta solicitud: {self.current_session.user_prompt}
        Y estos requisitos: {self.current_session.requirements}
        Genera especificaciones técnicas detalladas."""
        
        self.current_session.specifications = {
            "functional_requirements": ["El sistema debe...", "El usuario debe poder..."],
            "technical_requirements": ["Se usará Python", "Base de datos PostgreSQL"],
            "acceptance_criteria": ["Given/When/Then...", "Tests deben pasar"]
        }
    
    def _update_specifications(self, user_feedback: str):
        pass
    
    def _generate_design(self):
        """Genera el diseño de la arquitectura"""
        self.current_session.design_doc = f"""# Diseño para: {self.current_session.feature_name}
        ## Arquitectura
        - Modificar `archivo_a.py` para inyectar X.
        - Crear `archivo_b.py` para manejar Y.
        - Patrones a usar: Factory, TDD.

        ## Flujo de datos
        1. Paso 1
        2. Paso 2
        """
    
    def _update_design(self, user_feedback: str):
        pass
    
    def _save_openspec_files(self):
        """Genera propuesta.md, design.md y tasks.md físicamente en la raíz del monorepo"""
        from pathlib import Path
        
        # 1. Encontrar la raíz del Monorepo (mcp-scratch) de forma segura
        # __file__ está en backend/src/services/agent/jarvis/sdd_orchestrator.py
        current_dir = Path(__file__).resolve().parent
        monorepo_root = current_dir
        
        # Subimos por el árbol de carpetas hasta encontrar 'backend'
        while monorepo_root.name != 'backend' and monorepo_root.parent != monorepo_root:
            monorepo_root = monorepo_root.parent
            
        # Al encontrar 'backend', subimos UN nivel más para llegar a la raíz del proyecto
        if monorepo_root.name == 'backend':
            monorepo_root = monorepo_root.parent
            
        # 2. Crear el directorio de la feature
        feature_dir = monorepo_root / "openspec" / "changes" / self.current_session.feature_name
        feature_dir.mkdir(parents=True, exist_ok=True)
        
        # 3. Escribir proposal.md
        proposal_content = f"# Proposal: {self.current_session.feature_name}\n\n"
        proposal_content += f"## Solicitud Original\n{self.current_session.user_prompt}\n\n"
        proposal_content += "## Especificaciones Técnicas\n```json\n"
        proposal_content += json.dumps(self.current_session.specifications, indent=2, ensure_ascii=False)
        proposal_content += "\n```\n"
        (feature_dir / "proposal.md").write_text(proposal_content, encoding="utf-8")
        
        # 4. Escribir design.md
        (feature_dir / "design.md").write_text(self.current_session.design_doc, encoding="utf-8")
        
        # 5. Escribir tasks.md (El checklist para Koda)
        tasks_content = f"# Tareas de Implementación: {self.current_session.feature_name}\n\n"
        tasks_content += "> **Metodología**: TDD Estricto. Por cada tarea ejecutar RED -> GREEN -> REFACTOR.\n\n"
        
        for task in self.current_session.implementation_tasks:
            tasks_content += f"- [ ] **Task {task['id']}**: {task['description']}\n"
            
        (feature_dir / "tasks.md").write_text(tasks_content, encoding="utf-8")
        
        # Guardar la ruta en la sesión
        self.current_session.project_path = str(feature_dir)
        print(f"\n[SDD Orchestrator] ¡Artefactos guardados exitosamente en: {feature_dir}!\n")
    
    def _execute_implementation(self) -> str:
        """Ejecuta la implementación de las tareas"""
        tasks = self._generate_implementation_tasks()
        self.current_session.implementation_tasks = tasks
        
        result = "⚙️ **Implementando tareas (RED->GREEN->REFACTOR):**\n\n"
        
        for task in tasks:
            result += f"- {task['description']}... "
            # task_result = self._execute_task(task)
            result += "✅\n"
            self.current_session.completed_tasks.append(task['id'])
        
        self.current_session.current_phase = SDDPhase.VERIFY.value
        self._verify_implementation()
        
        return result + "\n\n(Simulación terminada, pasando a Verificación)...\n" + self._generate_phase_prompt(SDDPhase.VERIFY.value)
    
    def _generate_implementation_tasks(self) -> List[Dict]:
        return [
            {"id": "1", "description": "Escribir test fallido (RED)"},
            {"id": "2", "description": "Implementar lógica base (GREEN)"},
            {"id": "3", "description": "Limpiar código (REFACTOR)"},
        ]
    
    def _execute_task(self, task: Dict) -> bool:
        return True
    
    def _verify_implementation(self):
        self.current_session.verification_results = {
            "tests_passed": 5,
            "tests_failed": 0,
            "code_quality": "good",
            "security_check": "passed"
        }
    
    def _fix_issues(self):
        pass
    
    def _finalize_sdd(self) -> str:
        """Finaliza el flujo SDD"""
        if self.current_session.save_location == SaveLocation.LOCAL.value:
            self._save_to_files()
            
        # Parse timestamp string for duration calculation
        start_time = datetime.fromisoformat(self.current_session.created_at)
        duration = (datetime.now() - start_time).seconds
        
        return f"""🎉 **Flujo SDD Completado Exitosamente (Metodología Gentle AI)**

            **Resumen:**
            - Fases completadas: {len(self.current_session.completed_tasks)} tareas
            - Ubicación: {self.current_session.save_location}
            - Tiempo: {duration} segundos

            **¿Qué deseas hacer ahora?**
            - Iniciar otro flujo SDD: "use sdd"
            - Hacer preguntas sobre los cambios
            - Salir del modo SDD"""
    
    def _save_to_files(self):
        pass
    
    def is_sdd_active(self) -> bool:
        return self.current_session is not None and self.current_session.current_phase != SDDPhase.COMPLETE.value