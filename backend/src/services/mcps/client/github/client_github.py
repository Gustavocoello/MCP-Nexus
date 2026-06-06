# src/mcps/client/github/client_github.py
import os
from typing import Optional, Dict, List, Any
from src.services.mcps.client.base_client import BaseMCPClient

class GithubMCPClient(BaseMCPClient):
    """
    Cliente MCP para GitHub a través de HTTPS/SSE.
    Aprovecha la sesión viva (Context Manager) del BaseMCPClient.
    """
    def __init__(self, url: Optional[str] = None, user_id: Optional[str] = None):
        super().__init__(
            url=url, 
            provider="github", 
            user_id=user_id
        )

    def _format_response(self, result) -> Dict[str, Any]:
        """Extrae el contenido de FastMCP y lo estandariza para LangChain"""
        # Si ocurre un error de red, result podría no tener is_error
        is_err = getattr(result, "is_error", False)
        content = getattr(result, "content", result)
        return {"data": content or [], "success": not is_err}

    # =================================================================
    #            MÉTODOS WRAPPERS PARA KODA (TOOLS DE GITHUB)
    # =================================================================

    # 1. Leer contenido de un archivo
    async def github_get_file_contents(self, owner: str, repo: str, path: str, branch: Optional[str] = None):
        args = {"owner": owner, "repo": repo, "path": path}
        if branch: args["branch"] = branch
        result = await self._call_server("github_get_file_contents", args)
        return self._format_response(result)

    # 2. Crear o actualizar un archivo (Ideal para parches de Koda)
    async def github_create_or_update_file(self, owner: str, repo: str, path: str, content: str, message: str, branch: str, sha: Optional[str] = None):
        args = {
            "owner": owner, "repo": repo, "path": path, 
            "content": content, "message": message, "branch": branch
        }
        if sha: args["sha"] = sha
        result = await self._call_server("github_create_or_update_file", args)
        return self._format_response(result)

    # 3. Buscar repositorios
    async def github_search_repositories(self, query: str):
        result = await self._call_server("github_search_repositories", {"query": query})
        return self._format_response(result)

    # 4. Buscar código (Muy útil para que Koda entienda un proyecto entero)
    async def github_search_code(self, query: str):
        result = await self._call_server("github_search_code", {"query": query})
        return self._format_response(result)

    # 5. Crear una rama nueva
    async def github_create_branch(self, owner: str, repo: str, ref: str, sha: str):
        """ref: 'refs/heads/nueva-rama', sha: el hash del commit base"""
        result = await self._call_server("github_create_branch", {"owner": owner, "repo": repo, "ref": ref, "sha": sha})
        return self._format_response(result)

    # 6. Abrir un Pull Request
    async def github_create_pull_request(self, owner: str, repo: str, title: str, head: str, base: str, body: Optional[str] = None):
        args = {"owner": owner, "repo": repo, "title": title, "head": head, "base": base}
        if body: args["body"] = body
        result = await self._call_server("github_create_pull_request", args)
        return self._format_response(result)

    # 7. Obtener un Issue
    async def github_get_issue(self, owner: str, repo: str, issue_number: int):
        result = await self._call_server("github_get_issue", {"owner": owner, "repo": repo, "issue_number": issue_number})
        return self._format_response(result)
        
    # 8. Obtener SHA (Helper necesario para crear ramas)
    async def github_get_branch_sha(self, owner: str, repo: str, branch: str = "main"):
        result = await self._call_server("github_get_branch_sha", {"owner": owner, "repo": repo, "branch": branch})
        return self._format_response(result)