import os
import uuid
import json
import platform
import subprocess
import getpass
import asyncio
import traceback
from pathlib import Path
from typing import List, Optional
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
      
from langgraph.types import interrupt
from ..security.hitl import hitl_guard
from src.services.agent.common.utils.session_manager import is_paused
from src.services.agent.common.helpers import _run, _parse_mcp_result

from src.database.models.models import Message, User
from src.database.settings.connection import get_db
from src.services.mcps.client.client_manager import MCPClientManager

# =======================================
#   ESTADO NATIVO LOCAL
# =======================================
_native_user_workspaces: dict[str, str] = {}

# =======================================
# CLI - JARVIS_CLI
# =======================================

def set_workspace_direct(user_id: str, path: str) -> str:
    """
    Versión sin LLM de koda_set_workspace. Pensada para ser llamada por
    clientes (CLI, futuros) al arrancar sesión, sin gastar un turno de
    agente. Es la MISMA operación que la tool, solo que instantánea.
    """
    resolved = str(Path(path).resolve())
    _native_user_workspaces[user_id] = resolved
    return resolved


# --- HELPERS --- 
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
        "skills": backend_root /"src" / "services" / "agent" / "skills"
    }

def get_native_workspace(user_id: str) -> Path:
    if user_id in _native_user_workspaces:
        return Path(_native_user_workspaces[user_id])
    return Path.cwd()

def resolve_native_path(file_path: str, user_id: str) -> Path:
    """
    Convierte una ruta relativa en absoluta, basándose SIEMPRE en el 
    workspace activo del usuario en _native_user_workspaces.
    """
    # 1. Obtenemos dónde está parado el usuario (Si no hay registro, usamos CWD)
    current_workspace = _native_user_workspaces.get(user_id, os.getcwd())
    workspace_path = Path(current_workspace).resolve()
    
    # 2. Si el LLM mandó una ruta que ya es absoluta, la respetamos
    path_obj = Path(file_path)
    if path_obj.is_absolute():
        return path_obj.resolve()
        
    # 3. Concatenamos el workspace actual con el archivo que pide el LLM
    target_path = (workspace_path / path_obj).resolve()
    return target_path

def is_local_admin(user_id: str) -> bool:
    try:
        is_windows = platform.system() == "Windows"
        if not is_windows:
            return False

        # Extraer el generador de BD
        db = next(get_db())
        try:
            # 1. SOLUCIÓN UUID: Convertir el string a UUID para SQLAlchemy
            parsed_uuid = uuid.UUID(str(user_id))
            
            user = db.query(User).filter(User.id == parsed_uuid).first()
            if not user: 
                print(f"\n[DEBUG SEGURIDAD] Usuario no encontrado en DB con ID: {parsed_uuid}. ¿Se cargó el .env correcto?")
                return False
            
            email_valido = user.email and user.email.startswith("coellog634@gmail.com")
            if email_valido and user.is_admin:
                return True
                
            print(f"\n[DEBUG SEGURIDAD] Usuario encontrado, pero sin permisos. Admin: {user.is_admin}, Email: {user.email}")
            return False
            
        finally:
            db.close()

    except Exception as e:
        print(f"\n[ERROR CRÍTICO SEGURIDAD] Falló is_local_admin: {e}")
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

    # --- AMBOS CLI & UI
    # --- Directorios - PATH ---
    @tool
    def koda_set_workspace(directory: str, config: RunnableConfig) -> str:
        """
        Changes the current working directory for the agent. 
        Supports shortcuts: 'root', 'backend', 'api', 'frontend', 'ui', 'sdk', 'database', 'mcp_server', 'agents', 'skills'.
        Use this to quickly navigate the project.
        """
        try:
            # Usamos el user_id del closure (factory) por defecto
            current_user_id = config.get("configurable", {}).get("user_id", user_id)
            
            shortcuts = get_project_shortcuts()
            dir_lower = directory.lower().strip()
            native_err = None
            
            if is_local_admin(current_user_id):
                try:
                    if dir_lower in shortcuts:
                        new_path = shortcuts[dir_lower]
                    else:
                        new_path = resolve_native_path(directory, current_user_id)
                        
                    if not new_path.exists() or not new_path.is_dir():
                        return f"ERROR: The directory '{new_path}' does not exist on disk."
                        
                    _native_user_workspaces[current_user_id] = str(new_path)
                    return f"Success: Workspace changed. You are now at: {new_path}"
                except Exception as e:
                    native_err = str(e)
            else:
                native_err = "Entorno local no detectado o permisos insuficientes."

            # FALLBACK MCP
            try:
                client = get_files_mcp()
                if not client: return f"Fallo Nativo ({native_err}) y Servidor MCP Offline."
                result = _run(client.set_workspace(new_path=new_path))
                _record_tool_usage("set_workspace", "mcp")
                return f"Éxito MCP: Workspace cambiado. (Nativo falló: {native_err})"
            except Exception as e:
                return f"ERROR: Nativo ({native_err}) | MCP ({str(e)})"
                
        except Exception as e:
            return f"ERROR INTERNO DE PYTHON: {str(e)}\n{traceback.format_exc()}"

    @tool
    def koda_list_directory(directory_path: str = ".", config: RunnableConfig = None) -> str:
        """Lists all files and folders inside a specific directory."""
        try:
            current_user_id = config.get("configurable", {}).get("user_id", user_id) if config else user_id
            native_err = None
            
            if is_local_admin(current_user_id):
                try:
                    path = resolve_native_path(directory_path, current_user_id)
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
                
        except Exception as e:
            return f"ERROR INTERNO DE PYTHON: {str(e)}\n{traceback.format_exc()}"

    @tool
    def koda_search_items(query: str, search_type: str = "all", config: RunnableConfig = None) -> str:
        """Searches recursively for files or folders matching a specific name."""
        try:
            current_user_id = config.get("configurable", {}).get("user_id", user_id) if config else user_id
            native_err = None
            
            if is_local_admin(current_user_id):
                try:
                    base_path = get_native_workspace(current_user_id)
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
                
        except Exception as e:
            return f"ERROR INTERNO DE PYTHON: {str(e)}\n{traceback.format_exc()}"
    
    @tool
    def koda_get_directory_tree(directory_path: str = ".", max_depth: int = 10, config: RunnableConfig = None) -> str:
        """Generates a visual map (tree) of a folder locally."""
        try:
            current_user_id = config.get("configurable", {}).get("user_id", user_id) if config else user_id
            native_err = None
            
            if is_local_admin(current_user_id):
                try:
                    path = resolve_native_path(directory_path, current_user_id)
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
                
        except Exception as e:
            return f"ERROR INTERNO DE PYTHON: {str(e)}\n{traceback.format_exc()}"

    @tool
    def koda_copy_item(source_path: str, dest_path: str, config: RunnableConfig) -> str:
        """
        COPIES a file or directory to a new location.
        Use when the user wants to duplicate a file/folder without removing the original.
        """
        try:
            configurable = config.get("configurable", {})
            session_id = configurable.get("session_id")
            current_user_id = configurable.get("user_id", user_id)
            
            if not is_local_admin(current_user_id): return "Error: Permisos insuficientes."
            if session_id and is_paused(session_id): raise interrupt(f"Sesión pausada.")

            import shutil
            src = resolve_native_path(source_path, current_user_id)
            dst = resolve_native_path(dest_path, current_user_id)
            
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
            return f"ERROR INTERNO DE PYTHON: {str(e)}\n{traceback.format_exc()}"
    
    @tool
    def koda_list_skills() -> str:
        """Lists all available skills found in the skills/ directory."""
        try:
            try:
                shortcuts = get_project_shortcuts()
                skills_dir = shortcuts.get("skills")
                if skills_dir and skills_dir.exists():
                    skills = [d.name for d in skills_dir.iterdir() if d.is_dir() and (d / "SKILL.md").exists()]
                    return "Skills Nativos detectados:\n" + "\n".join(skills)
            except Exception:
                pass # Si falla, ignoramos e intentamos con MCP

            client = get_files_mcp()
            if not client: return "Fallo listando skills nativamente y servidor MCP Offline."
            result = _run(client.list_skills())
            _record_tool_usage("koda_list_skills", "mcp")
            return _parse_mcp_result(result)
            
        except Exception as e:
            return f"ERROR INTERNO DE PYTHON: {str(e)}\n{traceback.format_exc()}"
        
    # --- READ FILE ---
    @tool
    def koda_read_file(file_path: str, config: RunnableConfig) -> str:
        """Reads the full content of a file."""
        try:
            configurable = config.get("configurable", {})
            user_id = configurable.get("user_id", "default_user")
            
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
                
        except Exception as e:
            error_details = traceback.format_exc()
            return f"ERROR INTERNO DE PYTHON: {str(e)}\n{error_details}"

    # --- WRITE FILE ---
    @tool
    def koda_write_file(file_path: str, content: str, config: RunnableConfig) -> str:
        """CREATES or OVERWRITES an existing file with new content."""
        try:
            configurable = config.get("configurable", {})
            session_id = configurable.get("session_id")
            user_id = configurable.get("user_id", "default_user") # <-- SOLUCIONADO
            
            if session_id and is_paused(session_id): raise interrupt(f"Sesión {session_id} pausada.")
            if len(content) > 100000: return "ERROR: Contenido demasiado grande."

            guard_msg = hitl_guard(text=content, tool_name="koda_write_file", user_id=user_id, session_id=session_id)
            if guard_msg and "HITL_REQUIRES_APPROVAL" in guard_msg: raise interrupt(guard_msg)

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
                
        except Exception as e:
            error_details = traceback.format_exc()
            return f"ERROR INTERNO DE PYTHON: {str(e)}\n{error_details}"

    # Editar File - dentro de Write File
    @tool
    def koda_patch_file(file_path: str, search_block: str, replace_block: str, config: RunnableConfig) -> str:
        """EDIT existing files surgically without rewriting the entire document."""
        try:
            configurable = config.get("configurable", {})
            session_id = configurable.get("session_id")
            user_id = configurable.get("user_id", "default_user") # <-- SOLUCIONADO
            
            if session_id and is_paused(session_id): raise interrupt(f"Sesión pausada.")
            
            guard_msg = hitl_guard(text=replace_block, tool_name="koda_patch_file", user_id=user_id, session_id=session_id)
            if guard_msg and "HITL_REQUIRES_APPROVAL" in guard_msg: raise interrupt(guard_msg)

            native_err = None
            if is_local_admin(user_id):
                try:
                    path = resolve_native_path(file_path, user_id)
                    if path.exists():
                        content = path.read_text(encoding="utf-8")
                        occurrences = content.count(search_block)
                        if occurrences == 0:
                            return (
                                "ERROR: 'search_block' not found in file. "
                                "Ensure indentation, spaces, and line breaks match perfectly."
                            )
                        elif occurrences > 1:
                            return (
                                f"ERROR: 'search_block' was found {occurrences} times. "
                                "This would cause an ambiguous replacement. "
                                "Include more surrounding lines to make your 'search_block' unique."
                            )
                        
                        new_content = content.replace(search_block, replace_block, 1)
                        path.write_text(new_content, encoding="utf-8")
                        _record_tool_usage("koda_patch_file", "native")
                        return f"Éxito Nativo: Archivo {path} parcheado."
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
                
        except Exception as e:
            error_details = traceback.format_exc()
            return f"ERROR INTERNO DE PYTHON: {str(e)}\n{error_details}"

    # Dentro de Write File
    @tool
    def koda_append_to_file(file_path: str, text_to_append: str, config: RunnableConfig) -> str:
        """Safely APPENDS text to the END of a file. (Nativo solamente)"""
        try:
            configurable = config.get("configurable", {})
            session_id = configurable.get("session_id")
            user_id = configurable.get("user_id", "default_user") # <-- AQUÍ ESTABA EL BUG
            
            if not is_local_admin(user_id): return "Error: Entorno local no detectado."
            if session_id and is_paused(session_id): raise interrupt(f"Sesión pausada.")
            
            guard_msg = hitl_guard(text=text_to_append, tool_name="koda_append_to_file", user_id=user_id, session_id=session_id)
            if guard_msg and "HITL_REQUIRES_APPROVAL" in guard_msg: raise interrupt(guard_msg)

            path = resolve_native_path(file_path, user_id)
            with open(path, "a", encoding="utf-8") as f:
                f.write(f"\n{text_to_append}\n")
            _record_tool_usage("koda_append_to_file", "native")
            return f"Éxito: Texto agregado al final de {path}."
            
        except Exception as e:
            error_details = traceback.format_exc()
            return f"ERROR INTERNO DE PYTHON: {str(e)}\n{error_details}"

        
    # --- RENAME FILE ---    
    @tool
    def koda_rename_item(old_path: str, new_path: str, config: RunnableConfig) -> str:
        """RENAMES or MOVES a file or directory locally."""
        try:
            configurable = config.get("configurable", {})
            session_id = configurable.get("session_id")
            current_user_id = configurable.get("user_id", user_id)
            
            if not is_local_admin(current_user_id): return "Error: Permisos insuficientes."
            if session_id and is_paused(session_id): raise interrupt(f"Sesión pausada.")

            guard_msg = hitl_guard(text=f"Renombrar {old_path} a {new_path}", tool_name="koda_rename_item", user_id=current_user_id, session_id=session_id)
            if guard_msg and "HITL_REQUIRES_APPROVAL" in guard_msg: raise interrupt(guard_msg)

            old_p = resolve_native_path(old_path, current_user_id)
            new_p = resolve_native_path(new_path, current_user_id)
            
            if not old_p.exists():
                return f"Error: El origen {old_p} no existe."
                
            new_p.parent.mkdir(parents=True, exist_ok=True)
            old_p.rename(new_p)
            _record_tool_usage("koda_rename_item", "native")
            return f"Éxito Nativo: Renombrado/Movido de {old_p.name} a {new_p.name}"
            
        except Exception as e:
            return f"ERROR INTERNO DE PYTHON: {str(e)}\n{traceback.format_exc()}"
        
        
    # --- DELETE FILE ---
    @tool
    def koda_delete_item(path_to_delete: str, config: RunnableConfig) -> str:
        """
        🚨 DANGER: DELETES A FILE OR DIRECTORY PERMANENTLY. 🚨
        CRITICAL RULE: USE THIS TOOL **ONLY** IF THE USER EXPLICITLY AND CLEARLY ASKS TO DELETE OR REMOVE SOMETHING.
        NEVER USE THIS TO "CLEAN UP" OR GUESS. IF IN DOUBT, DO NOT USE IT.
        """
        configurable = config.get("configurable", {})
        session_id = configurable.get("session_id")
        user_id = configurable.get("user_id")
        
        if not is_local_admin(user_id): return "Error: Permisos insuficientes."
        if session_id and is_paused(session_id): raise interrupt(f"Sesión pausada.")

        # Guardián de seguridad obligatorio
        guard_msg = hitl_guard(text=f"ELIMINAR: {path_to_delete}", tool_name="koda_delete_item", user_id=user_id, session_id=session_id)
        if guard_msg and "HITL_REQUIRES_APPROVAL" in guard_msg: raise interrupt(guard_msg)

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
        
        
     # --- TERMINAL / BASH ---
    @tool
    def koda_run_terminal(command: str, config: RunnableConfig) -> str:
        """
        Executes a shell/bash command on the local machine.
        Starts in the current agent workspace.
        Use this for running scripts (.sh), git commands, npm install, etc.
        """
        try:
            configurable = config.get("configurable", {})
            session_id = configurable.get("session_id")
            current_user_id = configurable.get("user_id", user_id)
            
            if not is_local_admin(current_user_id): 
                return "Error: Permisos insuficientes o entorno no local."
            
            if session_id and is_paused(session_id): 
                raise interrupt(f"Sesión pausada.")

            # 1. Seguridad: El HITL evaluará si es un comando peligroso (rm -rf, git push, etc)
            guard_msg = hitl_guard(text=command, tool_name="koda_run_terminal", user_id=current_user_id, session_id=session_id)
            if guard_msg and "HITL_REQUIRES_APPROVAL" in guard_msg: 
                raise interrupt(guard_msg)

            # 2. Obtener la ruta base donde Koda está parado actualmente
            cwd_path = get_native_workspace(current_user_id)

            # 3. Preparar el comando (Soporte para Git Bash / WSL en Windows)
            cmd_stripped = command.strip()
            needs_bash = platform.system() == "Windows" and ".sh" in cmd_stripped
            
            if needs_bash and not cmd_stripped.startswith("bash"):
                cmd_to_run = f"bash {cmd_stripped}"
            else:
                cmd_to_run = cmd_stripped

            # 4. Ejecutar el proceso
            result = subprocess.run(
                cmd_to_run,
                shell=True,
                cwd=cwd_path,
                capture_output=True,
                text=True,
                timeout=120  # Límite de 2 minutos
            )
            
            output = result.stdout + result.stderr
            _record_tool_usage("koda_run_terminal", "native")
            
            if result.returncode != 0:
                return f"El comando falló (exit {result.returncode}):\n{output}"
            
            return f"Ejecución exitosa:\n{output}"

        except subprocess.TimeoutExpired:
            return "Error: El comando excedió el tiempo límite (120 segundos) y fue cancelado."
        except Exception as e:
            return f"ERROR INTERNO DE PYTHON: {str(e)}\n{traceback.format_exc()}"

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
        koda_delete_item,
        koda_run_terminal
    ]