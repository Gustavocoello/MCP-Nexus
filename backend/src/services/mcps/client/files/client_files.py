from typing import Optional, Dict, Any
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