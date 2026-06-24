# src/services/agent/common/mcp_errors.py
import re
import asyncio
import json

# ---------- HELPERS=------------------

# sdd_orchestador
def _generate_feature_name(self, prompt: str) -> str:
    words = re.findall(r'[a-zA-ZáéíóúñÁÉÍÓÚÑ0-9]+', prompt.lower())
    stopwords = {"el","la","los","las","un","una","de","que","y","a","para","con","se","en","del","vamos","creando"}
    keywords = [w for w in words if w not in stopwords][:4]
    return "-".join(keywords) if keywords else "feature-update"

# Agents
def _run(coro):
    """Helper to run async code from synchronous LangChain tools."""
    import concurrent.futures
    def run_in_thread():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(run_in_thread)
        return future.result()

def _parse_mcp_result(result) -> str:
    """Extracts text from the MCP result and returns it as a string."""
    try:
        content = result.get("data", result)
        
        if isinstance(content, list):
            texts = []
            for item in content:
                if hasattr(item, "text"):
                    texts.append(item.text)
                elif isinstance(item, dict):
                    texts.append(json.dumps(item, ensure_ascii=False))
                else:
                    texts.append(str(item))
            return "\n".join(texts)
        
        if isinstance(content, str):
            return content
            
        return json.dumps(content, ensure_ascii=False)
    except Exception as e:
        return f"Error parsing result: {e}"
    
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