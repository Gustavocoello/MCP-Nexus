import asyncio
import json

# ---------- HELPERS=------------------
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