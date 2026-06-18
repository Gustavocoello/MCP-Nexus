import os
import yaml
import subprocess
import platform
from pathlib import Path
from langchain_core.tools import Tool
from src.core.logging import get_logger

logger = get_logger("JarvisTools_run_skills")

REPO_ROOT = Path(__file__).resolve().parents[2]  # carpeta que contiene jarvis/, Koda/, skills/, etc.
SKILLS_DIR = Path(__file__).resolve().parents[2] / "skills"  # ajusta al árbol real

# Whitelist de carpetas permitidas para evitar que JARVIS toque cosas fuera de su scope
ALLOWED_PREFIXES = ("./skills/",)

def run_bash(command: str) -> str:
    """
    Ejecuta un comando bash, restringido a la carpeta skills/.
    Solo para comandos que empiecen con ./skills/...
    """
    logger.info(f"[JARVIS → BASH] cmd={command}")

    cmd_stripped = command.strip()
    if not cmd_stripped.startswith(ALLOWED_PREFIXES):
        return (
            f"BLOCKED: JARVIS You can only run scripts within ./skills/. "
            f"Command rejected: '{command}'. "
            f"if you need to write/edit files outside of skills/, delegate to ask_koda."
        )
    
     # En Windows, los .sh necesitan correrse vía bash (Git Bash / WSL)
    needs_bash = platform.system() == "Windows" and ".sh" in cmd_stripped

    if needs_bash:
        cmd_to_run = f"bash {cmd_stripped}"
    else:
        cmd_to_run = cmd_stripped

    try:
        result = subprocess.run(
            cmd_to_run,
            shell=True,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=120
        )
        output = result.stdout + result.stderr
        if result.returncode != 0:
            logger.error(f"[JARVIS → BASH] CRITICAL ERROR (exit {result.returncode}):\n{output}")
            return f"CRITICAL ERROR (exit {result.returncode}):\n{output}"
        logger.info(f"[JARVIS → BASH] Comando ejecutado correctamente:\n{output}")
        return f"Comando ejecutado correctamente:\n{output}"
    except subprocess.TimeoutExpired:
        return f"CRITICAL ERROR: timeout (120s) ejecutando '{command}'"
    except Exception as e:
        logger.error(f"[JARVIS → BASH] CRITICAL FAILURE: {str(e)}")
        return f"CRITICAL FAILURE: {str(e)}"
    

def list_skills() -> str:
    """Escanea skills/*/SKILL.md y devuelve solo el frontmatter (índice ligero)."""
    entries = []
    for skill_dir in sorted(SKILLS_DIR.iterdir()):
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue
        content = skill_md.read_text(encoding="utf-8")
        if not content.startswith("---"):
            continue
        _, frontmatter, _ = content.split("---", 2)
        meta = yaml.safe_load(frontmatter)
        entries.append({
            "name": meta.get("name", skill_dir.name),
            "description": meta.get("description", "").strip(),
            "scope": meta.get("metadata", {}).get("scope", []),
        })
    if not entries:
        return "No se encontraron skills."
    lines = [f"- {e['name']} (scope={e['scope']}): {e['description']}" for e in entries]
    return "ÍNDICE DE SKILLS DISPONIBLES:\n" + "\n".join(lines)    

def read_skill(skill_name: str) -> str:
    """Lee el SKILL.md completo de un skill específico."""
    skill_md = SKILLS_DIR / skill_name / "SKILL.md"
    if not skill_md.exists():
        return f"CRITICAL ERROR: '{skill_name}' no existe en {SKILLS_DIR}"
    return skill_md.read_text(encoding="utf-8")


# ---- TOOLS FOR JARVIS ----

def build_skills_tools(user_id: str) -> list:

    def _read_skill(skill_name: str) -> str:
        logger.info(f"[JARVIS → SKILLS] user={user_id} | read_skill={skill_name}")
        return read_skill(skill_name.strip())

    def _run_bash(command: str) -> str:
        logger.info(f"[JARVIS → SKILLS] user={user_id} | run_bash={command[:80]}")
        return run_bash(command.strip())

    return [
        Tool.from_function(
            func=_read_skill,
            name="read_skill",
            description=(
                "Reads the full SKILL.md of one skill. "
                "Only call when user explicitly asks to run or use a specific skill."
            )
        ),
        Tool.from_function(
            func=_run_bash,
            name="run_bash",
            description=(
                "Executes a command from a skill's ## Commands section. "
                "Restricted to ./skills/* paths. "
                "Only call AFTER read_skill and ONLY if user asked to RUN something."
            )
        ),
    ]