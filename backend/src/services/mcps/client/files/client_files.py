from typing import Optional, Dict, Any
from unittest import result
from ..base_client import BaseMCPClient

class FilesMCPClient(BaseMCPClient):
    """
    Specialized MCP Client for File System operations.
    Inherits security and transport logic from BaseMCPClient.
    """
    
    def __init__(self, url: Optional[str] = None, user_id: Optional[str] = None):
        super().__init__(
            url=url, 
            provider="files", 
            user_id=user_id
        )

    # =================================================================
    #            WRAPPER METHODS FOR FILES TOOLS
    # =================================================================

    async def list_directory(self, directory_path: str = ".") -> Dict[str, Any]:
        result = await self._call_server("mcp_list_directory", {"directory_path": directory_path})
        return {"data": result.content or "", "success": not getattr(result, "is_error", False)}

    async def read_file(self, file_path: str) -> Dict[str, Any]:
        result = await self._call_server("mcp_read_file", {"file_path": file_path})
        return {"data": result.content or "", "success": not getattr(result, "is_error", False)}

    async def patch_file(self, file_path: str, search_block: str, replace_block: str) -> Dict[str, Any]:
        arguments = {
            "file_path": file_path,
            "search_block": search_block,
            "replace_block": replace_block
        }
        result = await self._call_server("mcp_patch_file", arguments)
        return {"data": result.content or "", "success": not getattr(result, "is_error", False)}
    
    async def search_items(self, query: str, search_type: str = "all") -> Dict[str, Any]:
        result = await self._call_server("mcp_search_items", {"query": query, "search_type": search_type})
        return {"data": result.content or "", "success": not getattr(result, "is_error", False)}

    async def set_workspace(self, new_absolute_path: str) -> Dict[str, Any]:
        result = await self._call_server("mcp_set_workspace", {"new_absolute_path": new_absolute_path})
        return {"data": result.content or "", "success": not getattr(result, "is_error", False)}

    async def get_tree(self, directory_path: str = ".", max_depth: int = 3) -> Dict[str, Any]:
        result = await self._call_server("mcp_get_tree", {"directory_path": directory_path, "max_depth": max_depth})
        return {"data": result.content or "", "success": not getattr(result, "is_error", False)}
    
    async def write_file(self, file_path: str, content: str, overwrite: bool = False) -> Dict[str, Any]:
        result = await self._call_server(
            "mcp_write_file",
            {"file_path": file_path, "content": content, "overwrite": overwrite}
        )
        return {"data": result.content or "", "success": not getattr(result, "is_error", False)}

    async def list_skills(self) -> Dict[str, Any]:
        result = await self._call_server("mcp_list_skills", {})
        return {"data": result.content or "", "success": not getattr(result, "is_error", False)}