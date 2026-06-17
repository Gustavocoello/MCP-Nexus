import os
import json
import platform
import getpass
from pathlib import Path
from typing import List, Optional
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from langgraph.errors import NodeInterrupt      

from .hitl import hitl_guard, is_paused

from src.database.models.models import Message, User
from src.database.settings.connection import get_db

# =======================================
#        TOOLS FILES NATIVO (LOCAL)
# =======================================

# Diccionario para almacenar el workspace activo por usuario sin romper el backend
_native_user_workspaces: dict[str, str] = {}

def get_project_shortcuts() -> dict:
    """
    Mapea las rutas principales del proyecto basándose en la estructura real (mcp-scratch).
    El archivo actual está en: backend/src/services/agent/Koda/tools/files.py
    """
    # Subimos 5 niveles desde files.py para llegar a "backend"
    # files.py(0) -> tools(1) -> Koda(2) -> agent(3) -> services(4) -> src(5) -> backend(6)
    current_file = Path(__file__).resolve()
    backend_root = current_file.parents[5] 
    
    # El super-root (mcp-scratch) es el padre de backend
    workspace_root = backend_root.parent 

    return {
        "root": workspace_root,
        "backend": backend_root,
        "api": backend_root/"api",
        "frontend": workspace_root / "frontend",
        "ui": workspace_root / "frontend",
        "sdk": workspace_root / "sdk",               # Tu carpeta sdk (jarvis-cli, jarvis-ui)
        "database": backend_root / "src" / "database",
        "mcp_server": backend_root / "servers",
        "agents": backend_root / "src" / "services" / "agent",
        "skills": backend_root / "skills"
    }

def get_native_workspace(user_id: str) -> Path:
    """Devuelve el workspace actual del usuario. Por defecto es la raíz del backend."""
    if user_id in _native_user_workspaces:
        return Path(_native_user_workspaces[user_id])
    return Path.cwd()

def resolve_native_path(file_path: str, user_id: str) -> Path:
    """Resuelve rutas relativas basadas en el workspace del usuario."""
    workspace = get_native_workspace(user_id)
    path = Path(file_path)
    if path.is_absolute():
        return path.resolve()
    return (workspace / path).resolve()

def is_local_admin(user_id: str) -> bool:
    """Verifica seguridad a nivel de OS y de Base de Datos."""
    try:
        is_windows = platform.system() == "Windows"
        is_gustavo = "Gustavocoello" in getpass.getuser().lower()
        if not (is_windows and is_gustavo):
            return False

        with get_db() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if not user: return False
            email_valido = user.email and user.email.startswith("coellog634@gmail.com")
            if email_valido and user.is_admin:
                return True
        return False
    except Exception as e:
        print(f"Error validando seguridad de Admin: {e}")
        return False

def build_koda_files_tools(user_id: str, chat_id: Optional[str] = None, db_session=None):
    """
    Factory: generates the native local file tools for Koda.
    Bypasses MCP entirely for maximum speed and stability locally.
    """
    
    def _record_tool_usage(tool_name: str):
        """Guarda un registro en BD de la herramienta utilizada."""
        if not db_session or not chat_id: return
        mcp_context_str = json.dumps({"tool_used": tool_name, "provider": "koda_file_native"})
        mcp_msg = Message(chat_id=chat_id, role="mcp-tool", content=mcp_context_str)
        db_session.add(mcp_msg)
        db_session.commit()

    @tool
    def set_workspace(new_absolute_path: str) -> str:
        """
        Changes the root working directory of the project SAFELY.
        Supports shortcuts: 'root', 'api', 'ui', 'sdk', 'database', 'mcp_server', 'agents', 'skills'.
        """
        if not is_local_admin(user_id): return "Error: Entorno local no detectado."
        try:
            shortcuts = get_project_shortcuts()
            
            # Si el modelo usa un atajo (ej: "sdk" o "ui")
            if new_absolute_path.lower() in shortcuts:
                path = shortcuts[new_absolute_path.lower()].resolve()
            else:
                path = Path(new_absolute_path).resolve()
                
            if not path.exists() or not path.is_dir():
                return f"Error: El directorio {path} no existe."
            
            _native_user_workspaces[user_id] = str(path)
            _record_tool_usage("set_workspace")
            return f"Workspace cambiado con éxito al atajo/ruta: {path}"
        except Exception as e:
            return f"Error cambiando workspace: {str(e)}"

    @tool
    def koda_list_directory(directory_path: str = ".") -> str:
        """Lists all files and folders inside a specific directory."""
        if not is_local_admin(user_id): return "Error: Entorno local no detectado."
        try:
            path = resolve_native_path(directory_path, user_id)
            if not path.exists() or not path.is_dir():
                return f"Error: El directorio {path} no existe."
                
            items = os.listdir(path)
            _record_tool_usage("koda_list_directory")
            return f"Contenido de {path}:\n" + "\n".join(items)
        except Exception as e:
            return f"Error local: {str(e)}"

    @tool
    def koda_search_items(query: str, search_type: str = "all") -> str:
        """Searches recursively for files or folders matching a specific name."""
        if not is_local_admin(user_id): return "Error: Entorno local no detectado."
        try:
            base_path = get_native_workspace(user_id)
            results = []
            
            for root, dirs, files in os.walk(base_path):
                if any(ignored in root for ignored in ['node_modules', '.git', '__pycache__', '.venv', 'dist']):
                    continue
                    
                if search_type in ["all", "dir"]:
                    for d in dirs:
                        if query.lower() in d.lower(): results.append(os.path.join(root, d))
                if search_type in ["all", "file"]:
                    for f in files:
                        if query.lower() in f.lower(): results.append(os.path.join(root, f))
                            
                if len(results) > 50:
                    results.append("... [Demasiados resultados, se truncó la búsqueda]")
                    break

            _record_tool_usage("koda_search_items")
            if not results: return f"No se encontró '{query}'."
            return "\n".join(results)
        except Exception as e:
            return f"Error de búsqueda local: {str(e)}"

    @tool
    def koda_read_file(file_path: str) -> str:
        """Reads the full content of a local file safely."""
        if not is_local_admin(user_id): return "Error: Entorno local no detectado."
        try:
            path = resolve_native_path(file_path, user_id)
            if not path.exists() or not path.is_file(): return f"Error: El archivo {path} no existe."

            content = path.read_text(encoding="utf-8", errors="replace")
            if len(content) > 60000:
                content = content[:60000] + "\n\n... [CONTENIDO TRUNCADO POR SEGURIDAD DE TOKENS]"
                
            _record_tool_usage("koda_read_file")
            return content
        except Exception as e:
            return f"Error leyendo archivo: {str(e)}"

    @tool
    def koda_patch_file(file_path: str, search_block: str, replace_block: str, config: RunnableConfig) -> str:
        """EDIT existing files surgically without rewriting the entire document."""
        if not is_local_admin(user_id): return "Error: Entorno local no detectado."
        configurable = config.get("configurable", {})
        session_id = configurable.get("session_id")
        
        if session_id and is_paused(session_id): raise NodeInterrupt(f"La sesión {session_id} ha sido pausada.")
        if len(replace_block) > 50000: return "ERROR CRÍTICO: Bloque de reemplazo demasiado grande."

        guard_msg = hitl_guard(text=replace_block, tool_name="koda_patch_file", user_id=user_id, session_id=session_id)
        if guard_msg and "HITL_REQUIRES_APPROVAL" in guard_msg: raise NodeInterrupt(guard_msg)

        try:
            path = resolve_native_path(file_path, user_id)
            if not path.exists(): return f"Error: Archivo {path} no encontrado."

            content = path.read_text(encoding="utf-8")
            if search_block not in content:
                return f"Error: El 'search_block' NO se encontró exactamente. Verifica espacios o tabulaciones."

            new_content = content.replace(search_block, replace_block, 1)
            path.write_text(new_content, encoding="utf-8")
            _record_tool_usage("koda_patch_file")
            return f"Éxito: Archivo {path} editado correctamente."
        except Exception as e:
            return f"Error parcheando archivo: {str(e)}"

    @tool
    def koda_append_to_file(file_path: str, text_to_append: str, config: RunnableConfig) -> str:
        """Safely APPENDS text to the END of a file."""
        if not is_local_admin(user_id): return "Error: Entorno local no detectado."
        configurable = config.get("configurable", {})
        session_id = configurable.get("session_id")
        
        if session_id and is_paused(session_id): raise NodeInterrupt(f"La sesión {session_id} ha sido pausada.")
        if len(text_to_append) > 10000: return "ERROR: Texto a agregar demasiado largo."

        guard_msg = hitl_guard(text=text_to_append, tool_name="koda_append_to_file", user_id=user_id, session_id=session_id)
        if guard_msg and "HITL_REQUIRES_APPROVAL" in guard_msg: raise NodeInterrupt(guard_msg)

        try:
            path = resolve_native_path(file_path, user_id)
            with open(path, "a", encoding="utf-8") as f:
                f.write(f"\n{text_to_append}\n")
            _record_tool_usage("koda_append_to_file")
            return f"Éxito: Texto agregado al final de {path}."
        except Exception as e:
            return f"Error haciendo append: {str(e)}"

    @tool
    def koda_write_file(file_path: str, content: str, config: RunnableConfig) -> str:
        """CREATES a new file or OVERWRITES an existing file with new content."""
        if not is_local_admin(user_id): return "Error de Seguridad: Permisos insuficientes."
        configurable = config.get("configurable", {})
        session_id = configurable.get("session_id")
        
        if session_id and is_paused(session_id): raise NodeInterrupt(f"La sesión {session_id} ha sido pausada.")
        if len(content) > 100000: return "ERROR CRÍTICO: Contenido demasiado grande."

        guard_msg = hitl_guard(text=content, tool_name="koda_write_file", user_id=user_id, session_id=session_id)
        if guard_msg and "HITL_REQUIRES_APPROVAL" in guard_msg: raise NodeInterrupt(guard_msg)

        try:
            path = resolve_native_path(file_path, user_id)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            _record_tool_usage("koda_write_file")
            return f"Éxito: Archivo {path} creado/sobrescrito correctamente."
        except Exception as e:
            return f"Error al escribir el archivo: {str(e)}"

    @tool
    def get_directory_tree(directory_path: str = ".", max_depth: int = 3) -> str:
        """Generates a visual map (tree) of a folder locally."""
        if not is_local_admin(user_id): return "Error: Entorno local no detectado."
        try:
            path = resolve_native_path(directory_path, user_id)
            
            def generate_tree(dir_path: Path, current_depth: int = 0):
                if current_depth > max_depth: return ""
                tree_str = ""
                try:
                    for item in dir_path.iterdir():
                        if item.name in ['.git', 'node_modules', '__pycache__', '.venv', 'dist']: continue
                        prefix = "  " * current_depth + "├── "
                        tree_str += f"{prefix}{item.name}\n"
                        if item.is_dir(): tree_str += generate_tree(item, current_depth + 1)
                except PermissionError: pass
                return tree_str

            _record_tool_usage("get_directory_tree")
            return f"Tree of {path}:\n{generate_tree(path)}"
        except Exception as e:
            return f"Error generando tree: {str(e)}"

    return [
        koda_list_directory,
        koda_search_items,
        koda_read_file,
        koda_patch_file,
        koda_append_to_file,
        koda_write_file,
        set_workspace,
        get_directory_tree
    ]