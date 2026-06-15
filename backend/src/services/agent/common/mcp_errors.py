# src/services/agent/common/mcp_errors.py

def mcp_offline_error(provider: str, tool_name: str, error: str) -> str:
    return (
        f"CRITICAL FAILURE: '{provider}' MCP server is OFFLINE or unreachable "
        f"(tool: {tool_name}, error: {error}). "
        f"DO NOT INVENT or assume any data. "
        f"STOP immediately and report this exact error to JARVIS."
    )

def mcp_no_client(provider: str) -> str:
    return (
        f"CRITICAL FAILURE: '{provider}' MCP client could not be initialized — "
        f"server is OFFLINE or not configured. "
        f"DO NOT INVENT any data. STOP and report to JARVIS immediately."
    )