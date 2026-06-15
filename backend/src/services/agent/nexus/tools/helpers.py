import json
import asyncio
import json as _json

def _run(coro):
    """Helper para correr async desde tools síncronas de LangChain."""
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
    """Extrae el texto del resultado MCP y lo devuelve como string."""
    try:
        content = result.get("data", result)
        
        # Si es lista de TextContent objects
        if isinstance(content, list):
            texts = []
            for item in content:
                if hasattr(item, "text"):          # TextContent object
                    texts.append(item.text)
                elif isinstance(item, dict):        # ya es dict
                    texts.append(json.dumps(item, ensure_ascii=False))
                else:
                    texts.append(str(item))
            return "\n".join(texts)
        
        # Si ya es string
        if isinstance(content, str):
            return content
            
        return json.dumps(content, ensure_ascii=False)
    except Exception as e:
        return f"Error parsing result: {e}"
    
def _parse_args(kwargs: dict, expected_keys: list) -> dict:
    """
    Sanitiza argumentos del LLM.
    Caso 1: {"key": "valor"} → correcto, pasa directo
    Caso 2: {"key": '{"key": "valor", "key2": "valor2"}'} → extrae el JSON del string
    Caso 3: Cualquier valor string que contenga JSON con las keys esperadas
    """
    # Revisar TODOS los valores, no solo el primero
    for key, val in kwargs.items():
        if isinstance(val, str):
            val_stripped = val.strip()
            if val_stripped.startswith("{"):
                try:
                    parsed = _json.loads(val_stripped)
                    # Si el JSON parseado contiene AL MENOS UNA key esperada → úsalo
                    if any(k in parsed for k in expected_keys):
                        return parsed
                except Exception:
                    pass
    
    return kwargs

def _clean_id(value) -> str:
    """Limpia IDs que el LLM manda como JSON completo."""
    if not value:
        return value
    value = str(value).strip()
    if value.startswith("{"):
        try:
            parsed = _json.loads(value)
            return str(next(iter(parsed.values())))
        except Exception:
            pass
    return value