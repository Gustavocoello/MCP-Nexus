# src/services/agent/jarvis/tool.py
from src.core.logging import get_logger
from src.services.agent.jarvis.tools.delegation import build_delegation_tools
from src.services.agent.jarvis.tools.run_skills import build_skills_tools

logger = get_logger("jarvis_tools")


def build_jarvis_tools(user_id: str) -> list:
    return [
        *build_delegation_tools(user_id),
        *build_skills_tools(user_id),
    ]