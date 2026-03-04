# src/services/llm/lamar/agent.py
import os
import gc
import sys
from pathlib import Path
import logging
from dotenv import load_dotenv
# Esta es la forma más segura de importar AgentExecutor hoy en día
from langchain.agents import AgentExecutor, create_react_agent
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.agents import create_react_agent

current_dir = Path(__file__).resolve().parent.parent.parent
backend_dir = current_dir.parent.parent
sys.path.insert(0, str(backend_dir))

from src.services.agent.lamar.tools import get_current_datetime_and_knowledge_info, report_provider_status, get_llm_usage_report, trigger_full_system_check, test_single_provider, diagnose_provider_failure, diagnose_all_failed_providers
from src.services.llm.llm_router import API_PROVIDERS_TO_AGENT

load_dotenv()

logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

GROQ_KEY = os.getenv("GROQ_API_KEY0")

class LamarAgent:
    def __init__(self):
        # We use Groq (Llama 3.1 70B) for high-speed reasoning
        self.llm = ChatOpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=GROQ_KEY, 
            model="llama-3.3-70b-versatile",
            temperature=0
        )
        
        self.tools = [
            test_single_provider,
            report_provider_status, 
            get_llm_usage_report,
            trigger_full_system_check,
            get_current_datetime_and_knowledge_info,
            diagnose_provider_failure,
            diagnose_all_failed_providers
            ]
        
        # Conversational history stored un memory
        self.chat_history = [] 
        
        # --- ENGLISH REACT PROMPT (For better reasoning) ---
        template = """You are Lamar, an AI infrastructure orchestration agent.
        Your job is to manage 20+ LLM API providers and ensure system stability.

        LANGUAGE RULE (HIGHEST PRIORITY): You MUST think and reason in English at all times.
        Your Final Answer must be in the same language the Boss used.

        CONVERSATION HISTORY (use this to understand context from previous messages):
        {chat_history}

        You have access to the following tools:
        {tools}

        WHEN TO USE TOOLS:
        - Only use tools when the Boss explicitly asks for a system check, provider status, or token usage report.
        - If the Boss greets you or sends a message with no clear technical instruction, skip all tools entirely.
        - If the Boss says "yes", "sure", "please", "go ahead" or similar confirmations, check the conversation history to understand what was previously proposed and execute it.
        - test_single_provider: Use this when the Boss asks to TEST, CHECK, or VERIFY a specific provider by name or number. This does a REAL ping and returns if the provider is alive or not.
        - trigger_full_system_check: Use this when the Boss asks to check ALL providers at once.
        - report_provider_status: ONLY use this to manually LOG a status you already know. NEVER use this to test if a provider works.
        - get_llm_usage_report: Use this when the Boss asks about token usage or consumption.

        EXAMPLES:
        - "test provider 4" -> use test_single_provider
        - "is provider 4 working?" -> use test_single_provider  
        - "check all providers" -> use trigger_full_system_check
        - "log provider X as OK" -> use report_provider_status

        Use the following format STRICTLY:

        Thought: (always in English) Reason about whether you need a tool or not.

        --- If you DO need a tool:
        Action: one of [{tool_names}]
        Action Input: a valid JSON object, example: {{"provider_name": "Groq", "status": "OK", "details": "Working fine"}}
        Observation: the result of the action
        ... (repeat only if necessary)
        Thought: I now know the final answer.
        Final Answer: your response to the Boss.

        --- If you DO NOT need a tool (greetings, casual messages, no technical request):
        Thought: This message requires no tool. I will respond directly.
        Final Answer: your response to the Boss.

        CRITICAL RULES:
        1. NEVER use Action: None. If no tool is needed, go directly to Final Answer.
        2. Action Input MUST be a valid JSON object, never a function call like tool("arg1", "arg2").
        3. If you detect a 429 error, report it and suggest a provider swap.
        4. No emojis. Stay formal and technical, but you can call the Boss "socio".
        5. Final Answer must always match the language the Boss used.
        6. Use conversation history to resolve ambiguous messages like "yes", "do it", "please".
        7. If test_single_provider returns Alive: False, ALWAYS follow up with diagnose_provider_failure automatically before giving the Final Answer.
        8. NEVER call any tool more than once per provider in a single session. If multiple providers need diagnosis, use diagnose_all_failed_providers, not diagnose_provider_failure in a loop.
        9. NEVER invent, fabricate, or guess information. If you do not have the data from a tool result or from the conversation history, say exactly this: "I do not have that information. Use a tool or check the source directly." NEVER generate fake API key names, provider names, error codes, or any technical data that was not returned by a tool.
        10. API keys are CONFIDENTIAL. NEVER reveal, guess, or reference any API key name, value, or variable name. If the Boss asks about keys, respond: "API key details are confidential. Check your .env file directly."

        Boss input: {input}

        {agent_scratchpad}"""
        self.prompt = PromptTemplate.from_template(template)

    def run_task(self, instruction):
        api_names = [f"[{i+1}] {p['name']}" for i, p in enumerate(API_PROVIDERS_TO_AGENT)]
        system_context = (
            f"\n\n[SYSTEM CONTEXT]: You have {len(api_names)} active providers. "
            f"Numbered list: {', '.join(api_names)}. "
            "If the Boss refers to a number (e.g. the fifth one), identify it in this list."
        )

        # Format chat history
        if self.chat_history:
            history_str = "\n".join(
                [f"{role}: {msg}" for role, msg in self.chat_history]
            )
        else:
            history_str = "No previous conversation."

        # Inject chat_history as partial variable BEFORE the executor runs
        prompt_with_history = self.prompt.partial(chat_history=history_str)  # <-- FIX

        # Rebuild agent with the updated prompt each turn
        agent = create_react_agent(self.llm, self.tools, prompt_with_history)
        executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=5
        )

        try:
            response = executor.invoke({"input": instruction + system_context})

            self.chat_history.append(("Boss", instruction))
            self.chat_history.append(("Lamar", response["output"]))

            if len(self.chat_history) > 20:
                self.chat_history = self.chat_history[-20:]

            return response
        finally:
            gc.collect()
            
if __name__ == "__main__":
    print("\n" + "="*50)
    print("🤖 LAMAR: ONLINE RESILIENCE ORCHESTRATOR")
    print("Type 'q' to end the session.")
    print("="*50)
    
    lamar = LamarAgent()
    
    while True:
        try:
            user_input = input("\n User: ")
            
            if user_input.lower() in ["salir", "exit", "quit", "q"]:
                print("Locking systems... Until next time, socio.")
                break
            
            if not user_input.strip():
                continue

            print("\n Lamar thinking...")
            
            resultado = lamar.run_task(user_input)
            
            print(f"\n Lamar: {resultado['output']}")
            
        except KeyboardInterrupt:
            print("\n\nInterrupt detected. Exiting...")
            break
        except Exception as e:
            print(f"\n Error in main loop: {e}")