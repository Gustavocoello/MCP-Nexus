# src/services/agent/common/base_agent.py
import gc
import logging
from langchain.agents import AgentExecutor, create_react_agent
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate

logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)


class BaseAgent:
    """
    Base class for all agents.
    Handles the ReAct engine, chat history, and prompt injection.
    Each agent defines its own llm, tools, and template.
    """
    name: str = "BaseAgent"

    def __init__(self, llm: ChatOpenAI, tools: list, template: str):
        self.llm = llm
        self.tools = tools
        self.chat_history = []
        self.prompt = PromptTemplate.from_template(template)

    def _build_history_str(self) -> str:
        if self.chat_history:
            return "\n".join([f"{role}: {msg}" for role, msg in self.chat_history])
        return "No previous conversation."

    def _build_executor(self, prompt_with_history) -> AgentExecutor:
        agent = create_react_agent(self.llm, self.tools, prompt_with_history)
        return AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=5
        )

    def _update_history(self, instruction: str, output: str):
        self.chat_history.append(("Boss", instruction))
        self.chat_history.append((self.name, output))
        if len(self.chat_history) > 20:
            self.chat_history = self.chat_history[-20:]

    def run_task(self, instruction: str) -> dict:
        prompt_with_history = self.prompt.partial(
            chat_history=self._build_history_str()
        )
        executor = self._build_executor(prompt_with_history)

        try:
            response = executor.invoke({"input": instruction})
            self._update_history(instruction, response["output"])
            return response
        finally:
            gc.collect()

    def clear_history(self):
        self.chat_history = []