# MCP SERVER FILE - Ahi se utiliza
import os
from dotenv import load_dotenv

load_dotenv()
# Security: Lock the MCP to a specific directory (your portfolio project)
# You can set this in a .env file or default to the current directory
BASE_DIR = os.getenv("MCP_PROJECT_PATH")

def _get_safe_path(file_path: str) -> str:
    """Ensures the requested file path is safely within the BASE_DIR."""
    target_path = os.path.abspath(os.path.join(BASE_DIR, file_path))
    if not target_path.startswith(BASE_DIR):
        raise ValueError(f"Security Error: Access denied to paths outside {BASE_DIR}")
    return target_path

def list_local_directory(directory_path: str = ".") -> str:
    """Returns a list of files and folders in the specified directory."""
    try:
        target_path = _get_safe_path(directory_path)
        if not os.path.exists(target_path) or not os.path.isdir(target_path):
            return f"Error: Directory '{directory_path}' does not exist."
        
        items = os.listdir(target_path)
        return f"Directory contents of '{directory_path}':\n" + "\n".join(items)
    except Exception as e:
        return f"Error listing directory: {str(e)}"

def read_local_file(file_path: str) -> str:
    """Reads the content of a file."""
    try:
        target_path = _get_safe_path(file_path)
        if not os.path.exists(target_path) or not os.path.isfile(target_path):
            return f"Error: File '{file_path}' does not exist."
            
        with open(target_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if len(content) > 20000:
            return content[:20000] + "\n\n...[Content truncated due to length]..."
        return content
    except Exception as e:
        return f"Error reading file: {str(e)}"

def patch_local_file(file_path: str, search_block: str, replace_block: str) -> str:
    """Surgically replaces a block of code in a file."""
    try:
        target_path = _get_safe_path(file_path)
        if not os.path.exists(target_path):
            return f"Error: File '{file_path}' does not exist."
            
        with open(target_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if search_block not in content:
            preview = content[:500] + "\n...[truncated]...\n" if len(content) > 500 else content
            return (
                "Error: 'search_block' not found exactly as written. "
                "Check indentation, line breaks, or spaces. "
                f"Here is a preview of the file:\n{preview}"
            )
            
        new_content = content.replace(search_block, replace_block)
        
        with open(target_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
            
        return f"Success: File '{file_path}' updated safely."
    except Exception as e:
        return f"Error patching file: {str(e)}"