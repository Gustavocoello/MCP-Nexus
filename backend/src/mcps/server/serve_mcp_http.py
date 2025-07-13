# src/mcps/server/serve_mcp_http.py
from src.mcps.server.calendar_server import mcp

app = mcp.app  # FastAPI app que necesita Render
