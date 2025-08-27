# backend/src/mcps/client/base_client.py
import os
from fastmcp import Client, FastMCP
from dotenv import load_dotenv

load_dotenv()

MCP_URL = os.getenv("MCP")


mcp_client = Client(f"{MCP_URL}")


