from fastapi import FastAPI
import os

class FastMCP:
    def __init__(self, name: str, stateless_http: bool = False):
        self.app = FastAPI(title=name)
        

    def run(self, **kwargs):
        import uvicorn
        uvicorn.run(self.app, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
