# src/mcps/server/fastmcp.py
from fastapi import FastAPI
import os

class FastMCP:
    def __init__(self, name: str, stateless_http: bool = False):
        self._app = FastAPI(title=name)  # usa _app internamente
        # puedes hacer cosas como registrar routers, middlewares, etc.

    @property
    def app(self):
        return self._app  # <- esta propiedad lo expone públicamente como mcp.app

    def run(self, **kwargs):
        import uvicorn
        uvicorn.run(self.app, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
