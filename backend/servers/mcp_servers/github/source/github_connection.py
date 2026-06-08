import base64
import httpx
from typing import Optional, Dict, Any

class GithubConnector:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.github.com"
        self.timeout = httpx.Timeout(30.0, connect=10.0)
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }

    async def _request(self, method: str, endpoint: str, json_data: Optional[Dict] = None, params: Optional[Dict] = None):
        """Manejador central de peticiones asíncronas para GitHub"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            url = f"{self.base_url}/{endpoint}"
            response = await client.request(method, url, headers=self.headers, json=json_data, params=params)
            response.raise_for_status()
            
            # Para respuestas vacías (ej. 204 No Content en deletes)
            if not response.content:
                return {}
            return response.json()

    # --- 1. github_search_repositories ---
    async def search_repositories(self, query: str):
        return await self._request("GET", "search/repositories", params={"q": query})

    # --- 2. github_search_code ---
    async def search_code(self, query: str):
        return await self._request("GET", "search/code", params={"q": query})

    # --- 3. github_get_file_contents ---
    async def get_file_contents(self, owner: str, repo: str, path: str, branch: Optional[str] = None):
        """Obtiene el archivo y decodifica el Base64 a texto plano para el LLM."""
        params = {"ref": branch} if branch else None
        response = await self._request("GET", f"repos/{owner}/{repo}/contents/{path}", params=params)
        
        # Si es un archivo (no un directorio), decodificamos el contenido
        if isinstance(response, dict) and response.get("type") == "file" and "content" in response:
            try:
                decoded_bytes = base64.b64decode(response["content"])
                response["decoded_content"] = decoded_bytes.decode('utf-8')
            except Exception:
                response["decoded_content"] = "Error decodificando el archivo (quizás sea un binario/imagen)."
        
        return response

    # --- 4. github_create_or_update_file ---
    async def create_or_update_file(self, owner: str, repo: str, path: str, content: str, message: str, branch: str, sha: Optional[str] = None):
        """Koda envía texto plano, el conector lo pasa a Base64 para GitHub."""
        encoded_content = base64.b64encode(content.encode('utf-8')).decode('utf-8')
        payload = {
            "message": message,
            "content": encoded_content,
            "branch": branch
        }
        if sha:
            payload["sha"] = sha # Requerido si el archivo ya existe y se va a actualizar
            
        return await self._request("PUT", f"repos/{owner}/{repo}/contents/{path}", json_data=payload)

    # --- 5. github_create_branch ---
    async def create_branch(self, owner: str, repo: str, ref: str, sha: str):
        """ref debe ser estilo: 'refs/heads/nombre-de-la-rama'"""
        payload = {"ref": ref, "sha": sha}
        return await self._request("POST", f"repos/{owner}/{repo}/git/refs", json_data=payload)

    # --- 6. github_create_pull_request ---
    async def create_pull_request(self, owner: str, repo: str, title: str, head: str, base: str, body: Optional[str] = None):
        payload = {
            "title": title,
            "head": head,   # La rama de Koda (ej: 'fix-bug-login')
            "base": base,   # La rama destino (ej: 'main')
            "body": body or "Pull Request generado automáticamente por Koda (Jarvis)."
        }
        return await self._request("POST", f"repos/{owner}/{repo}/pulls", json_data=payload)

    # --- 7. github_get_issue ---
    async def get_issue(self, owner: str, repo: str, issue_number: int):
        return await self._request("GET", f"repos/{owner}/{repo}/issues/{issue_number}")
    
    # --- 8. github_get_branch_sha (Helper para create_branch) ---
    async def get_branch_sha(self, owner: str, repo: str, branch: str = "main"):
        """Útil para Koda: Obtiene el SHA de 'main' para usarlo al crear una nueva rama."""
        response = await self._request("GET", f"repos/{owner}/{repo}/git/ref/heads/{branch}")
        return response.get("object", {}).get("sha")