# src/agents/common/base_agent.py
from abc import ABC, abstractmethod

class BaseAgent(ABC):
    def __init__(self, llm_provider, tools=None):
        self.llm = llm_provider  # Aquí inyectamos el router de 20 APIs
        self.tools = tools or []
        self.memory = []

    @abstractmethod
    def run(self, task):
        """Cada agente debe implementar su propia lógica de ejecución"""
        pass

    def log_thought(self, thought):
        print(f"🤔 [{self.__class__.__name__}]: {thought}")