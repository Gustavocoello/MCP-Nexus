import os
import json
import platform
import getpass
import asyncio
from pathlib import Path
from typing import List, Optional
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from langgraph.errors import NodeInterrupt      

from .hitl import hitl_guard, is_paused
from src.services.agent.common.helpers import _run, _parse_mcp_result

from src.database.models.models import Message, User
from src.database.settings.connection import get_db
from src.services.mcps.client.client_manager import MCPClientManager

# =======================================
#   ESTADO NATIVO LOCAL
# =======================================
_native_user_workspaces: dict[str, str] = {}

def get_project_shortcuts() -> dict:
    current_file = Path(__file__).resolve()
    backend_root = current_file.parents[5] 
    workspace_root = backend_root.parent 

    return {
        "root": workspace_root,
        "backend": backend_root,
        "api": backend_root/"api",
        "frontend": workspace_root / "frontend",
        "ui": workspace_root / "frontend",
        "sdk": workspace_root / "sdk",               
        "database": backend_root / "src" / "database",
        "mcp_server": backend_root / "servers",
        "agents": backend_root / "src" / "services" / "agent",
        "skills": backend_root / "skills"
    }

def get_native_workspace(user_id: str) -> Path:
    if user_id in _native_user_workspaces:
        return Path(_native_user_workspaces[user_id])
    return Path.cwd()

def resolve_native_path(file_path: str, user_id: str) -> Path:
    workspace = get_native_workspace(user_id)
    path = Path(file_path)
    if path.is_absolute():
        return path.resolve()
    return (workspace / path).resolve()

def is_local_admin(user_id: str) -> bool:
    try:
        is_windows = platform.system() == "Windows"
        if not is_windows:
            return False

        # get_db() es un generador para FastAPI, usamos next() para sacar la sesión real
        db = next(get_db())
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user: return False
            
            email_valido = user.email and user.email.startswith("coellog634@gmail.com")
            if email_valido and user.is_admin:
                return True
                
            return False
        finally:
            # Siempre cerramos la sesión manualmente ya que no estamos usando 'with'
            db.close()

    except Exception as e:
        print(f"Error validando seguridad de Admin: {e}")
        return False
# =======================================
#   FACTORY DE HERRAMIENTAS UNIFICADAS
# =======================================

def build_koda_files_tools(user_id: str, chat_id: Optional[str] = None, db_session=None):
    """
    Factory unificada: Intenta Nativo primero, si falla hace fallback a MCP automáticamente.
    El agente LLM ya no tiene que decidir qué versión usar.
    """
    manager = MCPClientManager(user_id=user_id)

    def get_files_mcp():
        return manager.get_client("files")

    def _record_tool_usage(tool_name: str, provider: str = "native"):
        if not db_session or not chat_id: return
        mcp_context_str = json.dumps({"tool_used": tool_name, "provider": provider})
        mcp_msg = Message(chat_id=chat_id, role="mcp-tool", content=mcp_context_str)
        db_session.add(mcp_msg)
        db_session.commit()

    @tool
    def koda_set_workspace(new_absolute_path: str) -> str:
        """Changes the root working directory of the project SAFELY."""
        native_err = None
        if is_local_admin(user_id):
            try:
                shortcuts = get_project_shortcuts()
                if new_absolute_path.lower() in shortcuts:
                    path = shortcuts[new_absolute_path.lower()].resolve()
                else:
                    path = Path(new_absolute_path).resolve()
                    
                if path.exists() and path.is_dir():
                    _native_user_workspaces[user_id] = str(path)
                    _record_tool_usage("set_workspace", "native")
                    return f"Éxito Nativo: Workspace cambiado a {path}"
                native_err = f"Directorio {path} no existe."
            except Exception as e:
                native_err = str(e)
        else:
            native_err = "Entorno local no detectado o sin permisos."

        # FALLBACK MCP
        try:
            client = get_files_mcp()
            if not client: return f"Fallo Nativo ({native_err}) y Servidor MCP Offline."
            result = _run(client.set_workspace(new_absolute_path=new_absolute_path))
            _record_tool_usage("set_workspace", "mcp")
            return f"Éxito MCP: Workspace cambiado. (Nativo falló: {native_err})"
        except Exception as e:
            return f"ERROR: Nativo ({native_err}) | MCP ({str(e)})"

    @tool
    def koda_list_directory(directory_path: str = ".") -> str:
        """Lists all files and folders inside a specific directory."""
        native_err = None
        if is_local_admin(user_id):
            try:
                path = resolve_native_path(directory_path, user_id)
                if path.exists() and path.is_dir():
                    items = os.listdir(path)
                    _record_tool_usage("koda_list_directory", "native")
                    return f"Contenido de {path}:\n" + "\n".join(items)
                native_err = f"El directorio {path} no existe."
            except Exception as e:
                native_err = str(e)
        else:
            native_err = "Entorno local no detectado."

        # FALLBACK MCP
        try:
            client = get_files_mcp()
            if not client: return f"Fallo Nativo ({native_err}) y Servidor MCP Offline."
            result = _run(client.list_directory(directory_path=directory_path))
            _record_tool_usage("koda_list_directory", "mcp")
            return _parse_mcp_result(result)
        except Exception as e:
            return f"ERROR: Nativo ({native_err}) | MCP ({str(e)})"

    @tool
    def koda_search_items(query: str, search_type: str = "all") -> str:
        """Searches recursively for files or folders matching a specific name."""
        native_err = None
        if is_local_admin(user_id):
            try:
                base_path = get_native_workspace(user_id)
                results = []
                for root, dirs, files in os.walk(base_path):
                    if any(ignored in root for ignored in ['node_modules', '.git', '__pycache__', '.venv', 'dist']): continue
                    if search_type in ["all", "dir"]:
                        for d in dirs:
                            if query.lower() in d.lower(): results.append(os.path.join(root, d))
                    if search_type in ["all", "file"]:
                        for f in files:
                            if query.lower() in f.lower(): results.append(os.path.join(root, f))
                    if len(results) > 50:
                        results.append("... [Demasiados resultados, se truncó]")
                        break
                _record_tool_usage("koda_search_items", "native")
                return "\n".join(results) if results else f"No se encontró '{query}'."
            except Exception as e:
                native_err = str(e)
        else:
            native_err = "Entorno local no detectado."

        # FALLBACK MCP
        try:
            client = get_files_mcp()
            if not client: return f"Fallo Nativo ({native_err}) y Servidor MCP Offline."
            result = _run(client.search_items(query=query, search_type=search_type))
            _record_tool_usage("koda_search_items", "mcp")
            return _parse_mcp_result(result)
        except Exception as e:
            return f"ERROR: Nativo ({native_err}) | MCP ({str(e)})"

    @tool
    def koda_read_file(file_path: str) -> str:
        """Reads the full content of a file."""
        native_err = None
        if is_local_admin(user_id):
            try:
                path = resolve_native_path(file_path, user_id)
                if path.exists() and path.is_file():
                    content = path.read_text(encoding="utf-8", errors="replace")
                    if len(content) > 60000:
                        content = content[:60000] + "\n\n... [TRUNCADO]"
                    _record_tool_usage("koda_read_file", "native")
                    return content
                native_err = f"El archivo {path} no existe."
            except Exception as e:
                native_err = str(e)
        else:
            native_err = "Entorno local no detectado."

        # FALLBACK MCP
        try:
            client = get_files_mcp()
            if not client: return f"Fallo Nativo ({native_err}) y Servidor MCP Offline."
            result = _run(client.read_file(file_path=file_path))
            _record_tool_usage("koda_read_file", "mcp")
            return _parse_mcp_result(result)
        except Exception as e:
            return f"ERROR: Nativo ({native_err}) | MCP ({str(e)})"

    @tool
    def koda_write_file(file_path: str, content: str, config: RunnableConfig) -> str:
        """CREATES or OVERWRITES an existing file with new content."""
        configurable = config.get("configurable", {})
        session_id = configurable.get("session_id")
        
        if session_id and is_paused(session_id): raise NodeInterrupt(f"Sesión {session_id} pausada.")
        if len(content) > 100000: return "ERROR: Contenido demasiado grande."

        guard_msg = hitl_guard(text=content, tool_name="koda_write_file", user_id=user_id, session_id=session_id)
        if guard_msg and "HITL_REQUIRES_APPROVAL" in guard_msg: raise NodeInterrupt(guard_msg)

        native_err = None
        if is_local_admin(user_id):
            try:
                path = resolve_native_path(file_path, user_id)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
                _record_tool_usage("koda_write_file", "native")
                return f"Éxito Nativo: Archivo {path} creado/sobrescrito."
            except Exception as e:
                native_err = str(e)
        else:
            native_err = "Permisos insuficientes."

        # FALLBACK MCP
        normalized = file_path.replace("\\", "/").lstrip("./")
        if not normalized.startswith("skills/"):
            return f"NATIVO FALLÓ ({native_err}). MCP BLOQUEADO: '{file_path}' está fuera de skills/. MCP solo puede escribir en skills/."

        try:
            client = get_files_mcp()
            if not client: return f"NATIVO FALLÓ ({native_err}) y MCP Offline."
            result = _run(client.write_file(file_path=file_path, content=content))
            _record_tool_usage("koda_write_file", "mcp")
            return f"Éxito MCP: Archivo escrito. (Nativo falló: {native_err})"
        except Exception as e:
            return f"ERROR: Nativo ({native_err}) | MCP ({str(e)})"

    @tool
    def koda_patch_file(file_path: str, search_block: str, replace_block: str, config: RunnableConfig) -> str:
        """EDIT existing files surgically without rewriting the entire document."""
        configurable = config.get("configurable", {})
        session_id = configurable.get("session_id")
        
        if session_id and is_paused(session_id): raise NodeInterrupt(f"Sesión pausada.")
        
        guard_msg = hitl_guard(text=replace_block, tool_name="koda_patch_file", user_id=user_id, session_id=session_id)
        if guard_msg and "HITL_REQUIRES_APPROVAL" in guard_msg: raise NodeInterrupt(guard_msg)

        native_err = None
        if is_local_admin(user_id):
            try:
                path = resolve_native_path(file_path, user_id)
                if path.exists():
                    content = path.read_text(encoding="utf-8")
                    if search_block in content:
                        new_content = content.replace(search_block, replace_block, 1)
                        path.write_text(new_content, encoding="utf-8")
                        _record_tool_usage("koda_patch_file", "native")
                        return f"Éxito Nativo: Archivo {path} parcheado."
                    else:
                        native_err = "El 'search_block' NO se encontró exactamente."
                else:
                    native_err = f"Archivo {path} no encontrado."
            except Exception as e:
                native_err = str(e)
        else:
            native_err = "Entorno local no detectado."

        # FALLBACK MCP
        try:
            client = get_files_mcp()
            if not client: return f"NATIVO FALLÓ ({native_err}) y MCP Offline."
            result = _run(client.patch_file(file_path=file_path, search_block=search_block, replace_block=replace_block))
            _record_tool_usage("koda_patch_file", "mcp")
            return f"Éxito MCP: Archivo parcheado. (Nativo falló: {native_err})"
        except Exception as e:
            return f"ERROR: Nativo ({native_err}) | MCP ({str(e)})"

    @tool
    def koda_get_directory_tree(directory_path: str = ".", max_depth: int = 3) -> str:
        """Generates a visual map (tree) of a folder locally."""
        native_err = None
        if is_local_admin(user_id):
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
                
                _record_tool_usage("get_directory_tree", "native")
                return f"Tree of {path}:\n{generate_tree(path)}"
            except Exception as e:
                native_err = str(e)
        else:
            native_err = "Entorno local no detectado."

        # FALLBACK MCP
        try:
            client = get_files_mcp()
            if not client: return f"Fallo Nativo ({native_err}) y MCP Offline."
            result = _run(client.get_tree(directory_path=directory_path, max_depth=max_depth))
            _record_tool_usage("get_directory_tree", "mcp")
            return _parse_mcp_result(result)
        except Exception as e:
            return f"ERROR: Nativo ({native_err}) | MCP ({str(e)})"

    @tool
    def koda_append_to_file(file_path: str, text_to_append: str, config: RunnableConfig) -> str:
        """Safely APPENDS text to the END of a file. (Nativo solamente)"""
        # (El append no tenía versión MCP en tu código original, así que si falla nativo, lanza error)
        if not is_local_admin(user_id): return "Error: Entorno local no detectado."
        configurable = config.get("configurable", {})
        session_id = configurable.get("session_id")
        
        if session_id and is_paused(session_id): raise NodeInterrupt(f"Sesión pausada.")
        guard_msg = hitl_guard(text=text_to_append, tool_name="koda_append_to_file", user_id=user_id, session_id=session_id)
        if guard_msg and "HITL_REQUIRES_APPROVAL" in guard_msg: raise NodeInterrupt(guard_msg)

        try:
            path = resolve_native_path(file_path, user_id)
            with open(path, "a", encoding="utf-8") as f:
                f.write(f"\n{text_to_append}\n")
            _record_tool_usage("koda_append_to_file", "native")
            return f"Éxito: Texto agregado al final de {path}."
        except Exception as e:
            return f"Error haciendo append: {str(e)}"

    @tool
    def koda_list_skills() -> str:
        """Lists all available skills found in the skills/ directory."""
        try:
            shortcuts = get_project_shortcuts()
            skills_dir = shortcuts.get("skills")
            if skills_dir and skills_dir.exists():
                skills = [d.name for d in skills_dir.iterdir() if d.is_dir() and (d / "SKILL.md").exists()]
                return "Skills Nativos detectados:\n" + "\n".join(skills)
        except Exception:
            pass # Si falla, ignoramos e intentamos con MCP

        try:
            client = get_files_mcp()
            if not client: return "Fallo listando skills nativamente y servidor MCP Offline."
            result = _run(client.list_skills())
            _record_tool_usage("koda_list_skills", "mcp")
            return _parse_mcp_result(result)
        except Exception as e:
            return f"ERROR MCP listando skills: {str(e)}"
        
        
    @tool
    def koda_rename_item(old_path: str, new_path: str, config: RunnableConfig) -> str:
        """RENAMES or MOVES a file or directory locally."""
        if not is_local_admin(user_id): return "Error: Permisos insuficientes."
        configurable = config.get("configurable", {})
        session_id = configurable.get("session_id")
        
        if session_id and is_paused(session_id): raise NodeInterrupt(f"Sesión pausada.")

        # Guardián de seguridad opcional
        guard_msg = hitl_guard(text=f"Renombrar {old_path} a {new_path}", tool_name="koda_rename_item", user_id=user_id, session_id=session_id)
        if guard_msg and "HITL_REQUIRES_APPROVAL" in guard_msg: raise NodeInterrupt(guard_msg)

        native_err = None
        try:
            old_p = resolve_native_path(old_path, user_id)
            new_p = resolve_native_path(new_path, user_id)
            
            if not old_p.exists():
                return f"Error: El origen {old_p} no existe."
                
            new_p.parent.mkdir(parents=True, exist_ok=True)
            old_p.rename(new_p)
            _record_tool_usage("koda_rename_item", "native")
            return f"Éxito Nativo: Renombrado/Movido de {old_p.name} a {new_p.name}"
        except Exception as e:
            native_err = str(e)
            return f"ERROR Nativo al renombrar: {native_err}"
        
    @tool
    def koda_copy_item(source_path: str, dest_path: str, config: RunnableConfig) -> str:
        """
        COPIES a file or directory to a new location.
        Use when the user wants to duplicate a file/folder without removing the original.
        """
        if not is_local_admin(user_id): return "Error: Permisos insuficientes."
        configurable = config.get("configurable", {})
        session_id = configurable.get("session_id")
        if session_id and is_paused(session_id): raise NodeInterrupt(f"Sesión pausada.")

        try:
            import shutil
            src = resolve_native_path(source_path, user_id)
            dst = resolve_native_path(dest_path, user_id)
            
            if not src.exists():
                return f"Error: El origen '{src}' no existe."
            
            dst.parent.mkdir(parents=True, exist_ok=True)
            
            if src.is_dir():
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)
                
            _record_tool_usage("koda_copy_item", "native")
            return f"Éxito: '{src.name}' copiado a '{dst}'"
        except Exception as e:
            return f"ERROR copiando: {str(e)}"
        
    @tool
    def koda_delete_item(path_to_delete: str, config: RunnableConfig) -> str:
        """
        🚨 DANGER: DELETES A FILE OR DIRECTORY PERMANENTLY. 🚨
        CRITICAL RULE: USE THIS TOOL **ONLY** IF THE USER EXPLICITLY AND CLEARLY ASKS TO DELETE OR REMOVE SOMETHING.
        NEVER USE THIS TO "CLEAN UP" OR GUESS. IF IN DOUBT, DO NOT USE IT.
        """
        if not is_local_admin(user_id): return "Error: Permisos insuficientes."
        configurable = config.get("configurable", {})
        session_id = configurable.get("session_id")
        
        if session_id and is_paused(session_id): raise NodeInterrupt(f"Sesión pausada.")

        # Guardián de seguridad obligatorio
        guard_msg = hitl_guard(text=f"ELIMINAR: {path_to_delete}", tool_name="koda_delete_item", user_id=user_id, session_id=session_id)
        if guard_msg and "HITL_REQUIRES_APPROVAL" in guard_msg: raise NodeInterrupt(guard_msg)

        try:
            import shutil
            target_p = resolve_native_path(path_to_delete, user_id)
            if not target_p.exists():
                return f"Error: {target_p} no existe."
            
            if target_p.is_dir():
                shutil.rmtree(target_p)
            else:
                target_p.unlink()
                
            _record_tool_usage("koda_delete_item", "native")
            return f"Éxito: Eliminado permanentemente {target_p.name}"
        except Exception as e:
            return f"ERROR al eliminar: {str(e)}"

    # Retornamos UNA ÚNICA LISTA DE TOOLS LIMPIA
    return [
        koda_set_workspace,
        koda_list_directory,
        koda_search_items,
        koda_read_file,
        koda_write_file,
        koda_patch_file,
        koda_append_to_file,
        koda_get_directory_tree,
        koda_list_skills,
        koda_rename_item,
        koda_copy_item,
        koda_delete_item
    ]