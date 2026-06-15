# src/servers/mcp_servers/files/sources/file_manager.py
# MCP SERVER FILE - Ahi se utiliza
import os
from dotenv import load_dotenv

load_dotenv()
# Security: Lock the MCP to a specific directory (your portfolio project)
# You can set this in a .env file or default to the current directory
# ─── Workspace base (fallback si el usuario no tiene uno asignado) ────────────
BASE_WORKSPACE = os.getenv("MCP_PROJECT_PATH", os.getcwd())

# Workspace aislado por usuario — clave: user_id, valor: path absoluto
_user_workspaces: dict[str, str] = {}

def _resolve_path(path: str, user_id: str = None, expect_dir: bool = False) -> tuple[str, str | None]:
    """
    Helper interno: resuelve cualquier path, usando find_skills_dir para skills/.
    Retorna (target_path, error_message). Si error_message es None, el path es válido.
    """
    normalized = path.replace("\\", "/").lstrip("./")
    
    if normalized.startswith("skills/") or normalized == "skills":
        skills_dir = find_skills_dir(user_id)
        if not skills_dir:
            return None, f"CRITICAL ERROR: Could not find skills/ directory from workspace '{get_workspace(user_id)}'. DO NOT RETRY."
        
        # Si es exactamente "skills" o "skills/" sin subcarpeta
        relative = normalized[len("skills/"):] if "/" in normalized else ""
        if not relative:
            return skills_dir, None
            
        target = os.path.abspath(os.path.join(skills_dir, relative))
        if not target.startswith(os.path.abspath(skills_dir)):
            return None, "CRITICAL ERROR: Path traversal detected. DO NOT RETRY."
        return target, None
    
    try:
        return _get_safe_path(path, user_id), None
    except ValueError as e:
        return None, f"CRITICAL ERROR: {str(e)}. DO NOT RETRY."
    
# ─── Workspace helpers ────────────────────────────────────────────────────────

def get_workspace(user_id: str = None) -> str:
    """Retorna el workspace del usuario, o BASE_WORKSPACE si no tiene uno asignado."""
    if user_id and user_id in _user_workspaces:
        return _user_workspaces[user_id]
    return BASE_WORKSPACE


def set_active_workspace(new_absolute_path: str, user_id: str = None) -> str:
    """Cambia el workspace del usuario específico. No afecta a otros usuarios."""
    if not os.path.exists(new_absolute_path) or not os.path.isdir(new_absolute_path):
        return f"CRITICAL ERROR: The path '{new_absolute_path}' does not exist or is not a directory. DO NOT RETRY blindly."

    abs_path = os.path.abspath(new_absolute_path)
    if user_id:
        _user_workspaces[user_id] = abs_path
        return f"Success: Workspace for user '{user_id}' changed to '{abs_path}'."
    else:
        # Sin user_id: cambia el BASE_WORKSPACE (compatibilidad hacia atrás)
        global BASE_WORKSPACE
        BASE_WORKSPACE = abs_path
        return f"Success: Global workspace changed to '{abs_path}'."
    
def _is_valid_skills_dir(path: str) -> bool:
    """Verifica que la carpeta skills/ tenga al menos un SKILL.md adentro."""
    try:
        for entry in os.listdir(path):
            skill_md = os.path.join(path, entry, "SKILL.md")
            if os.path.exists(skill_md):
                return True
    except Exception:
        pass
    return False

def find_skills_dir(user_id: str = None) -> str | None:
    """
    Busca la carpeta skills/ en dos fases:
    1. Sube desde el workspace hacia la raíz (max 6 niveles)
    2. Si no encuentra, busca recursivamente hacia abajo (max 4 niveles de profundidad)
    Retorna la ruta absoluta de skills/ o None si no se encuentra.
    """
    workspace = get_workspace(user_id)
    current = os.path.abspath(workspace)

    # FASE 1: subir hacia la raíz
    for _ in range(6):
        candidate = os.path.join(current, "skills")
        if os.path.exists(candidate) and os.path.isdir(candidate) and _is_valid_skills_dir(candidate):
                return candidate
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent

    # FASE 2: buscar hacia abajo recursivamente desde el workspace original
    workspace_abs = os.path.abspath(workspace)
    ignore = {'venv', 'node_modules', '__pycache__', 'dist', 'build', '.git', '.next', 'env'}

    def _search_down(path: str, depth: int) -> str | None:
        if depth > 4:
            return None
        try:
            entries = os.listdir(path)
        except PermissionError:
            return None

        # Primero busca "skills" directo en este nivel
        for entry in entries:
            if entry == "skills":
                full = os.path.join(path, entry)
                if os.path.isdir(full) and _is_valid_skills_dir(full):
                    return full

        # Luego entra a subcarpetas (ignorando las pesadas)
        for entry in entries:
            if entry in ignore or entry.startswith('.'):
                continue
            full = os.path.join(path, entry)
            if os.path.isdir(full):
                result = _search_down(full, depth + 1)
                if result:
                    return result
        return None

    return _search_down(workspace_abs, 0)


def _get_safe_path(file_path: str, user_id: str = None) -> str:
    """Ensures the requested file path is safely within the user's workspace."""
    workspace = get_workspace(user_id)

    if os.path.isabs(file_path):
        file_path = file_path.lstrip("/\\").replace("C:", "").replace("c:", "")

    target_path = os.path.abspath(os.path.join(workspace, file_path))

    if not target_path.startswith(os.path.abspath(workspace)):
        raise ValueError(f"Security Error: Access denied to paths outside {workspace}")
    return target_path


# ─── File operations ──────────────────────────────────────────────────────────

def list_local_directory(directory_path: str = ".", user_id: str = None) -> str:
    try:
        target_path, error = _resolve_path(directory_path, user_id, expect_dir=True)
        if error:
            return error
        if not os.path.exists(target_path) or not os.path.isdir(target_path):
            return f"CRITICAL ERROR: Directory '{directory_path}' does not exist. DO NOT RETRY."

        items = os.listdir(target_path)
        if not items:
            return f"Directory contents of '{directory_path}':\n[Directory is completely empty]"

        return f"Directory contents of '{directory_path}':\n" + "\n".join(items)
    except Exception as e:
        return f"CRITICAL ERROR listing directory: {str(e)}. DO NOT RETRY."


def read_local_file(file_path: str, user_id: str = None) -> str:
    try:
        target_path, error = _resolve_path(file_path, user_id)
        if error:
            return error
        if not os.path.exists(target_path) or not os.path.isfile(target_path):
            return f"CRITICAL ERROR: File '{file_path}' does not exist. DO NOT RETRY."

        with open(target_path, 'r', encoding='utf-8') as f:
            content = f.read()

        if len(content) > 20000:
            return content[:20000] + "\n\n...[Content truncated due to length]..."
        return content
    except Exception as e:
        return f"CRITICAL ERROR reading file: {str(e)}. DO NOT RETRY."


def patch_local_file(file_path: str, search_block: str, replace_block: str, user_id: str = None) -> str:
    try:
        target_path, error = _resolve_path(file_path, user_id)
        if error:
            return error
        if not os.path.exists(target_path):
            return f"CRITICAL ERROR: File '{file_path}' does not exist. DO NOT RETRY."

        with open(target_path, 'r', encoding='utf-8') as f:
            content = f.read()

        if search_block not in content:
            preview = content[:500] + "\n...[truncated]...\n" if len(content) > 500 else content
            return f"CRITICAL ERROR: 'search_block' not found exactly as written. DO NOT RETRY.\n{preview}"

        new_content = content.replace(search_block, replace_block)
        with open(target_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        return f"Success: File '{file_path}' updated safely."
    except Exception as e:
        return f"CRITICAL ERROR patching file: {str(e)}. DO NOT RETRY."


def search_local_items(query: str, search_type: str = "all", user_id: str = None) -> str:
    workspace = get_workspace(user_id)
    try:
        results = []
        query_lower = query.lower()

        for root, dirs, files in os.walk(workspace):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['venv', 'node_modules', '__pycache__', 'dist']]

            rel_root = os.path.relpath(root, workspace)
            if rel_root == ".":
                rel_root = ""

            if search_type in ["all", "dir"]:
                for d in dirs:
                    if query_lower in d.lower():
                        results.append(f"[DIR]  {os.path.join(rel_root, d)}")

            if search_type in ["all", "file"]:
                for f in files:
                    if query_lower in f.lower():
                        results.append(f"[FILE] {os.path.join(rel_root, f)}")

        if not results:
            return f"No results found for '{query}' in {workspace}."

        if len(results) > 100:
            return f"Found {len(results)} matches (showing first 100):\n" + "\n".join(results[:100]).replace("\\", "/")

        return f"Found {len(results)} matches:\n" + "\n".join(results).replace("\\", "/")
    except Exception as e:
        return f"CRITICAL ERROR searching items: {str(e)}. DO NOT RETRY."


def generate_project_tree(directory_path: str = ".", max_depth: int = 5, user_id: str = None) -> str:
    try:
        target_path = _get_safe_path(directory_path, user_id)
        if not os.path.exists(target_path) or not os.path.isdir(target_path):
            return f"CRITICAL ERROR: Directory '{directory_path}' does not exist. DO NOT RETRY."

        ignore_dirs = {'.git', 'node_modules', 'venv', 'env', '__pycache__', 'dist', 'build', '.next'}
        tree_str = f"Directory Tree of '{directory_path}' (Max depth: {max_depth}):\n.\n"

        def build_tree(current_path, prefix="", current_depth=0):
            if current_depth >= max_depth:
                return ""
            try:
                entries = os.listdir(current_path)
            except PermissionError:
                return prefix + "└── [Permission Denied]\n"

            entries = [e for e in entries if e not in ignore_dirs]
            entries.sort(key=lambda x: (not os.path.isdir(os.path.join(current_path, x)), x.lower()))

            result = ""
            for i, entry in enumerate(entries):
                is_last = (i == len(entries) - 1)
                full_path = os.path.join(current_path, entry)
                connector = "└── " if is_last else "├── "
                result += f"{prefix}{connector}{entry}\n"
                if os.path.isdir(full_path):
                    extension = "    " if is_last else "│   "
                    result += build_tree(full_path, prefix + extension, current_depth + 1)
            return result

        tree_output = build_tree(target_path)
        if not tree_output.strip():
            return tree_str + "└── [Empty or only ignored folders]"
        return tree_str + tree_output
    except Exception as e:
        return f"CRITICAL ERROR generating tree: {str(e)}. DO NOT RETRY."


def write_local_file(file_path: str, content: str, overwrite: bool = False, user_id: str = None) -> str:
    """
    Creates a new file. For skills/ paths, auto-resolves using find_skills_dir
    so it works regardless of where MCP_PROJECT_PATH points.
    """
    try:
        normalized = file_path.replace("\\", "/").lstrip("./")

        if normalized.startswith("skills/"):
            # Auto-descubrimiento: busca skills/ subiendo en el árbol
            skills_dir = find_skills_dir(user_id)
            if not skills_dir:
                return (
                    f"CRITICAL ERROR: Could not find skills/ directory from "
                    f"workspace '{get_workspace(user_id)}'. "
                    f"Check MCP_PROJECT_PATH or set workspace manually. DO NOT RETRY."
                )
            relative_inside_skills = normalized[len("skills/"):]
            target_path = os.path.abspath(os.path.join(skills_dir, relative_inside_skills))

            # Verifica que siga dentro de skills/
            if not target_path.startswith(os.path.abspath(skills_dir)):
                return "CRITICAL ERROR: Path traversal detected in skills/ write. DO NOT RETRY."
        else:
            target_path = _get_safe_path(file_path, user_id)

        if os.path.exists(target_path) and not overwrite:
            return (
                f"CRITICAL ERROR: File '{file_path}' already exists. "
                f"Use overwrite=True to replace it. DO NOT RETRY blindly."
            )

        os.makedirs(os.path.dirname(target_path), exist_ok=True)

        with open(target_path, 'w', encoding='utf-8') as f:
            f.write(content)

        return f"Success: File '{file_path}' created at '{target_path}' ({len(content)} bytes)."
    except Exception as e:
        return f"CRITICAL ERROR writing file: {str(e)}. DO NOT RETRY."


def list_skills(user_id: str = None) -> str:
    """
    Finds the skills/ directory and lists all available skills with their names.
    Works regardless of where the workspace is pointing.
    """
    skills_dir = find_skills_dir(user_id)
    if not skills_dir:
        return (
            f"CRITICAL ERROR: Could not find skills/ directory from "
            f"workspace '{get_workspace(user_id)}'. DO NOT RETRY."
        )

    try:
        entries = [
            d for d in os.listdir(skills_dir)
            if os.path.isdir(os.path.join(skills_dir, d))
            and not d.startswith('.')
        ]

        if not entries:
            return f"Skills directory found at '{skills_dir}' but it is empty."

        return (
            f"Skills directory: '{skills_dir}'\n"
            f"Available skills ({len(entries)}):\n" +
            "\n".join(f"  - {e}" for e in sorted(entries))
        )
    except Exception as e:
        return f"CRITICAL ERROR listing skills: {str(e)}. DO NOT RETRY."