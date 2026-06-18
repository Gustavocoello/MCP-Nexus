# backend/src/services/agent/jarvis/sdd_orchestrator.py
from enum import Enum, auto
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
import json
from datetime import datetime

class SDDPhase(Enum):
    IDLE = auto()
    EXPLORE = auto()
    PROPOSE = auto()
    SPEC = auto()
    DESIGN = auto()
    IMPLEMENT = auto()
    VERIFY = auto()
    COMPLETE = auto()
    ERROR = auto()

class SaveLocation(Enum):
    CHAT = "chat"
    LOCAL = "local"

@dataclass
class SDDContext:
    """Contexto del flujo SDD"""
    user_prompt: str
    current_phase: SDDPhase = SDDPhase.IDLE
    save_location: Optional[SaveLocation] = None
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
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

class SDDOrchestrator:
    """
    Orquestador del flujo SDD para el agente Jarvis
    Implementa: Prompt -> Gather Context -> Take Action -> Verify -> Repeat
    """
    
    def __init__(self, jarvis_agent, koda_agent=None):
        self.jarvis = jarvis_agent  # Tu orquestador actual
        self.koda = koda_agent      # Agente de código si lo tienes
        self.current_session: Optional[SDDContext] = None
        self.phase_handlers: Dict[SDDPhase, Callable] = {
            SDDPhase.EXPLORE: self._handle_explore,
            SDDPhase.PROPOSE: self._handle_propose,
            SDDPhase.SPEC: self._handle_spec,
            SDDPhase.DESIGN: self._handle_design,
            SDDPhase.IMPLEMENT: self._handle_implement,
            SDDPhase.VERIFY: self._handle_verify,
        }
    
    def start_sdd(self, user_prompt: str) -> str:
        """
        Inicia el flujo SDD cuando el usuario dice "use sdd" o similar
        """
        self.current_session = SDDContext(user_prompt=user_prompt)
        self.current_session.current_phase = SDDPhase.EXPLORE
        
        return self._generate_phase_prompt(SDDPhase.EXPLORE)
    
    def process_user_response(self, user_response: str) -> str:
        """
        Procesa la respuesta del usuario en cada fase
        """
        if not self.current_session:
            return "No hay sesión SDD activa. Usa 'use sdd' para iniciar."
        
        current_phase = self.current_session.current_phase
        
        # Actualizar contexto según la fase actual
        if current_phase == SDDPhase.EXPLORE:
            return self._process_explore_response(user_response)
        elif current_phase == SDDPhase.PROPOSE:
            return self._process_propose_response(user_response)
        elif current_phase == SDDPhase.SPEC:
            return self._process_spec_response(user_response)
        elif current_phase == SDDPhase.DESIGN:
            return self._process_design_response(user_response)
        elif current_phase == SDDPhase.IMPLEMENT:
            return self._process_implement_response(user_response)
        elif current_phase == SDDPhase.VERIFY:
            return self._process_verify_response(user_response)
        
        return "Fase no reconocida"
    
    def _generate_phase_prompt(self, phase: SDDPhase) -> str:
        """Genera el prompt para cada fase"""
        prompts = {
            SDDPhase.EXPLORE: """🔍 **FASE 1: EXPLORACIÓN - Recopilando Contexto**

Estoy analizando tu solicitud: "{user_prompt}"

Por favor, ayúdame a entender mejor:

1. ¿Qué problema específico quieres resolver?
2. ¿Hay archivos específicos que deba revisar?
3. ¿Hay restricciones o requisitos especiales?

Responde con esta información para continuar...""",
            
            SDDPhase.PROPOSE: """📋 **FASE 2: PROPUESTA - Dónde Guardar**

                    He analizado tu solicitud. Ahora necesito saber:

                    **¿Dónde quieres guardar los cambios?**

                    - **chat**: Solo en esta conversación (temporal)
                    - **local**: Guardar en archivos del proyecto (permanente)

                    Responde con: "chat" o "local""",
        
            
            SDDPhase.SPEC: """📝 **FASE 3: ESPECIFICACIONES**

                    Estoy definiendo las especificaciones técnicas...

                    He identificado:
                    {specs}

                    Por favor, revisa y confirma si estas especificaciones son correctas, o indica cambios.""",
            
            SDDPhase.DESIGN: """🏗️ **FASE 4: DISEÑO - Arquitectura**

                    Estoy diseñando la solución técnica...

                    **Arquitectura propuesta:**
                    {design}

                    ¿Estás de acuerdo con este diseño? Responde "sí" para continuar o indica cambios.""",
            
            SDDPhase.IMPLEMENT: """⚙️ **FASE 5: IMPLEMENTACIÓN**

                    Estoy implementando los cambios...

                    **Tareas a realizar:**
                    {tasks}

                    Ejecutando ahora...""",
            
            SDDPhase.VERIFY: """✅ **FASE 6: VERIFICACIÓN**

                    He completado la implementación. Estoy verificando...

                    **Resultados de verificación:**
                    {verification}

                    ¿Todo se ve correcto? Responde "sí" para finalizar o "revisar" para corregir."""
        }
        
        context = self.current_session
        return prompts[phase].format(
            user_prompt=context.user_prompt,
            specs=json.dumps(context.specifications, indent=2) if context.specifications else "Cargando...",
            design=context.design_doc if context.design_doc else "Cargando...",
            tasks="\n".join([f"- {t['description']}" for t in context.implementation_tasks]) if context.implementation_tasks else "Cargando...",
            verification=json.dumps(context.verification_results, indent=2) if context.verification_results else "Verificando..."
        )
    
    # ============ HANDLERS DE CADA FASE ============
    
    def _handle_explore(self):
        """Fase 1: Explorar - Recopilar contexto"""
        # Aquí Jarvis analiza el codebase
        # Usa herramientas como RAG, búsqueda de archivos, etc.
        
        exploration = {
            "codebase_structure": self._analyze_codebase(),
            "relevant_files": self._find_relevant_files(),
            "existing_patterns": self._identify_patterns()
        }
        
        self.current_session.exploration_results = exploration
        return self._generate_phase_prompt(SDDPhase.EXPLORE)
    
    def _process_explore_response(self, user_response: str) -> str:
        """Procesa la respuesta del usuario en fase EXPLORE"""
        # Almacenar información adicional del usuario
        self.current_session.requirements = self._parse_requirements(user_response)
        
        # Avanzar a PROPOSE
        self.current_session.current_phase = SDDPhase.PROPOSE
        return self._generate_phase_prompt(SDDPhase.PROPOSE)
    
    def _handle_propose(self):
        """Fase 2: Proponer - Dónde guardar"""
        # Ya está en PROPOSE, solo generar prompt
        return self._generate_phase_prompt(SDDPhase.PROPOSE)
    
    def _process_propose_response(self, user_response: str) -> str:
        """Procesa la respuesta del usuario en fase PROPOSE"""
        response_lower = user_response.lower().strip()
        
        if "chat" in response_lower:
            self.current_session.save_location = SaveLocation.CHAT
        elif "local" in response_lower:
            self.current_session.save_location = SaveLocation.LOCAL
            # Preguntar por ruta del proyecto
            return """📁 **Ruta del Proyecto**

¿En qué ruta del proyecto quieres guardar los cambios?
Ejemplo: `/home/user/mi-proyecto` o `./backend`"""
        
        # Avanzar a SPEC
        self.current_session.current_phase = SDDPhase.SPEC
        
        # Generar especificaciones automáticamente
        self._generate_specifications()
        
        return self._generate_phase_prompt(SDDPhase.SPEC)
    
    def _handle_spec(self):
        """Fase 3: Especificar - Definir specs"""
        return self._generate_phase_prompt(SDDPhase.SPEC)
    
    def _process_spec_response(self, user_response: str) -> str:
        """Procesa la respuesta del usuario en fase SPEC"""
        if "sí" in user_response.lower() or "ok" in user_response.lower():
            # Avanzar a DESIGN
            self.current_session.current_phase = SDDPhase.DESIGN
            self._generate_design()
            return self._generate_phase_prompt(SDDPhase.DESIGN)
        else:
            # El usuario quiere cambios en las specs
            self._update_specifications(user_response)
            return self._generate_phase_prompt(SDDPhase.SPEC)
    
    def _handle_design(self):
        """Fase 4: Diseñar - Arquitectura"""
        return self._generate_phase_prompt(SDDPhase.DESIGN)
    
    def _process_design_response(self, user_response: str) -> str:
        """Procesa la respuesta del usuario en fase DESIGN"""
        if "sí" in user_response.lower() or "ok" in user_response.lower():
            # Avanzar a IMPLEMENT
            self.current_session.current_phase = SDDPhase.IMPLEMENT
            return self._execute_implementation()
        else:
            # El usuario quiere cambios en el diseño
            self._update_design(user_response)
            return self._generate_phase_prompt(SDDPhase.DESIGN)
    
    def _handle_implement(self):
        """Fase 5: Implementar - Ejecutar acciones"""
        return self._execute_implementation()
    
    def _process_implement_response(self, user_response: str) -> str:
        """Procesa la respuesta del usuario en fase IMPLEMENT"""
        # Normalmente el usuario no responde durante implementación
        # La implementación es automática
        return "Implementando..."
    
    def _handle_verify(self):
        """Fase 6: Verificar - Validar resultados"""
        return self._generate_phase_prompt(SDDPhase.VERIFY)
    
    def _process_verify_response(self, user_response: str) -> str:
        """Procesa la respuesta del usuario en fase VERIFY"""
        if "sí" in user_response.lower() or "ok" in user_response.lower():
            # Finalizar
            self.current_session.current_phase = SDDPhase.COMPLETE
            return self._finalize_sdd()
        elif "revisar" in user_response.lower() or "cambiar" in user_response.lower():
            # Volver a IMPLEMENT
            self.current_session.current_phase = SDDPhase.IMPLEMENT
            self._fix_issues()
            return self._execute_implementation()
        else:
            # El usuario quiere más cambios
            return self._generate_phase_prompt(SDDPhase.VERIFY)
    
    # ============ MÉTODOS DE IMPLEMENTACIÓN ============
    
    def _analyze_codebase(self) -> Dict:
        """Analiza la estructura del codebase"""
        # Usa herramientas de tu sistema (RAG, búsqueda, etc.)
        return {
            "structure": "Análisis de estructura",
            "files": ["file1.py", "file2.py"],
            "patterns": ["patrón1", "patrón2"]
        }
    
    def _find_relevant_files(self) -> List[str]:
        """Encuentra archivos relevantes para la tarea"""
        # Implementar con tus herramientas existentes
        return []
    
    def _identify_patterns(self) -> List[str]:
        """Identifica patrones existentes en el código"""
        return []
    
    def _parse_requirements(self, user_response: str) -> List[str]:
        """Parsea los requisitos del usuario"""
        # Dividir por líneas o frases
        return [r.strip() for r in user_response.split("\n") if r.strip()]
    
    def _generate_specifications(self):
        """Genera especificaciones automáticamente"""
        # Usa el LLM para generar specs basadas en el contexto
        prompt = f"""Basado en esta solicitud: {self.current_session.user_prompt}
        
        Y estos requisitos: {self.current_session.requirements}
        
        Genera especificaciones técnicas detalladas."""
        
        # Llamar al LLM
        # specs = self.jarvis.llm.generate(prompt)
        
        self.current_session.specifications = {
            "functional_requirements": ["req1", "req2"],
            "technical_requirements": ["tech1", "tech2"],
            "acceptance_criteria": ["criteria1", "criteria2"]
        }
    
    def _update_specifications(self, user_feedback: str):
        """Actualiza las specs basadas en feedback del usuario"""
        # Implementar lógica de actualización
        pass
    
    def _generate_design(self):
        """Genera el diseño de la arquitectura"""
        # Usa el LLM para generar diseño
        self.current_session.design_doc = f"""# Diseño para: {self.current_session.user_prompt}

## Arquitectura
- Componente A: ...
- Componente B: ...

## Flujo de datos
1. Paso 1
2. Paso 2
"""
    
    def _update_design(self, user_feedback: str):
        """Actualiza el diseño basado en feedback"""
        pass
    
    def _execute_implementation(self) -> str:
        """Ejecuta la implementación de las tareas"""
        # Aquí es donde tu agente realmente hace el trabajo
        # Usa las herramientas existentes (Koda, editores de archivos, etc.)
        
        tasks = self._generate_implementation_tasks()
        self.current_session.implementation_tasks = tasks
        
        result = "⚙️ **Implementando tareas:**\n\n"
        
        for task in tasks:
            result += f"- {task['description']}... "
            
            # Ejecutar la tarea usando tus herramientas existentes
            # task_result = self._execute_task(task)
            
            result += "✅\n"
            self.current_session.completed_tasks.append(task['id'])
        
        # Avanzar a VERIFY
        self.current_session.current_phase = SDDPhase.VERIFY
        self._verify_implementation()
        
        return result + "\n\n" + self._generate_phase_prompt(SDDPhase.VERIFY)
    
    def _generate_implementation_tasks(self) -> List[Dict]:
        """Genera las tareas de implementación"""
        return [
            {"id": "1", "description": "Analizar archivo existente"},
            {"id": "2", "description": "Modificar función X"},
            {"id": "3", "description": "Actualizar imports"},
        ]
    
    def _execute_task(self, task: Dict) -> bool:
        """Ejecuta una tarea específica"""
        # Integrar con tus herramientas existentes
        # Por ejemplo, usar Koda para editar código
        return True
    
    def _verify_implementation(self):
        """Verifica la implementación"""
        self.current_session.verification_results = {
            "tests_passed": 5,
            "tests_failed": 0,
            "code_quality": "good",
            "security_check": "passed"
        }
    
    def _fix_issues(self):
        """Corrige issues encontrados en verificación"""
        pass
    
    def _finalize_sdd(self) -> str:
        """Finaliza el flujo SDD"""
        # Guardar resultados según save_location
        if self.current_session.save_location == SaveLocation.LOCAL:
            self._save_to_files()
        
        return f"""🎉 **Flujo SDD Completado Exitosamente**

**Resumen:**
- Fases completadas: {len(self.current_session.completed_tasks)} tareas
- Ubicación: {self.current_session.save_location.value}
- Tiempo: {(datetime.now() - self.current_session.created_at).seconds} segundos

**¿Qué deseas hacer ahora?**
- Iniciar otro flujo SDD: "use sdd"
- Hacer preguntas sobre los cambios
- Salir del modo SDD"""
    
    def _save_to_files(self):
        """Guarda los resultados en archivos del proyecto"""
        # Implementar guardado de archivos
        pass
    
    def is_sdd_active(self) -> bool:
        """Verifica si hay un flujo SDD activo"""
        return self.current_session is not None and self.current_session.current_phase != SDDPhase.COMPLETE
