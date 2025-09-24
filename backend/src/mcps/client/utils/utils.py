# src/mcps/client/utils/serialize_utils.py (por ejemplo)

def safe_serialize_textcontent(obj):
    """
    Extrae .text de TextContent-like objects si existen.
    """
    try:
        # si es un objeto con .text
        if hasattr(obj, "text"):
            return obj.text
        # si es objeto pydantic simple
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        if hasattr(obj, "dict"):
            # fallback pydantic v1 (advertencia deprecación)
            return obj.dict()
    except Exception:
        # si algo raro, caer al str()
        pass
    return str(obj)


def safe_serialize_content(item):
    """
    Serializador robusto que devuelve solo tipos primitivos (dict/list/str/int/float/bool/None)
    Evita llamadas genéricas a .dict() en todo objeto sin control.
    """
    # None/direct primitives
    if item is None or isinstance(item, (str, int, float, bool)):
        return item

    # lista/tupla
    if isinstance(item, (list, tuple)):
        return [safe_serialize_content(i) for i in item]

    # dict
    if isinstance(item, dict):
        return {k: safe_serialize_content(v) for k, v in item.items()}

    # fastmcp CallToolResult or similar: intentar mapear manualmente
    # Comprueba propiedades típicas
    if hasattr(item, "content") or hasattr(item, "structured_content") or hasattr(item, "is_error"):
        # Objetivo: devolver dict simple sin referencias
        try:
            content = getattr(item, "content", None)
            structured = getattr(item, "structured_content", None) or getattr(item, "data", None)
            is_error = getattr(item, "is_error", None) or getattr(item, "isError", None)
            # procesar content (puede ser lista de TextContent)
            safe_content = []
            if content:
                for cb in content:
                    safe_content.append(safe_serialize_content(cb))
            return {
                "content": safe_content,
                "structured_content": safe_serialize_content(structured),
                "is_error": bool(is_error)
            }
        except Exception:
            return str(item)

    # TextContent-like
    if hasattr(item, "text"):
        return safe_serialize_textcontent(item)

    # Pydantic objects (model_dump preferible)
    if hasattr(item, "model_dump"):
        try:
            return safe_serialize_content(item.model_dump())
        except Exception:
            pass

    if hasattr(item, "dict"):
        try:
            return safe_serialize_content(item.dict())
        except Exception:
            pass

    # fallback
    return str(item)


def safe_serialize_call_result(result):
    """
    Wrapper que devuelve UN dict simple listo para json.dumps sin riesgo de recursión.
    """
    return safe_serialize_content(result)
