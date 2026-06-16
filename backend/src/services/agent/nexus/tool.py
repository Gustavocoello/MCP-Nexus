# src/services/agent/nexus/tool.py

from src.services.agent.nexus.tools.github import build_github_tools
from src.services.agent.nexus.tools.calendar import build_calendar_tools
from src.services.agent.nexus.tools.files import build_files_tools
from src.services.agent.nexus.tools.notion import build_notion_tools
from src.services.agent.nexus.tools.devtools import build_devtools_tools
#from src.services.agent.nexus.tools.web.webwright_tool import build_webwright_tools

def build_nexus_tools(user_id: str, chat_id=None, db_session=None) -> list:
    return [
        *build_github_tools(user_id, chat_id, db_session),
        *build_files_tools(user_id, chat_id, db_session),
        *build_notion_tools(user_id, chat_id, db_session),
        *build_calendar_tools(user_id, chat_id, db_session),
        *build_devtools_tools(user_id, chat_id, db_session),
        #*build_webwright_tools(user_id, chat_id, db_session)
    ]