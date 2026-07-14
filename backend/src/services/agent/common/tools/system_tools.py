from pathlib import Path
from langchain_core.tools import tool

@tool
def invoke_skill(skill_name: str) -> str:
    """
    Loads the complete instructions and workflow of a specific skill.
    ALWAYS call this tool when the AGENTS.md auto-invoke table tells you to use a skill.
    """
    current_file = Path(__file__).resolve()
    
    # 0: tools/
    # 1: common/
    # 2: agent/
    
    # Subimos 3 niveles para llegar a la carpeta 'agent'
    agent_root = current_file.parents[2] 
    
    # Entramos a la carpeta 'skills' (backend/src/services/agent/skills)
    skills_dir = agent_root / "skills"
    
    skill_path = skills_dir / skill_name / "SKILL.md"
    
    if skill_path.exists():
        return skill_path.read_text(encoding="utf-8")
    
    return f"Error: Skill '{skill_name}' no encontrada. Revisa el nombre exacto."