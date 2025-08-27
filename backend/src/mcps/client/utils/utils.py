def serialize_content(item):
    """
    Convierte recursivamente objetos no serializables (como TextContent) en dicts, listas o valores simples.
    """
    if hasattr(item, "dict"):  # si tiene método dict()
        return item.dict()
    elif isinstance(item, list):
        return [serialize_content(i) for i in item]
    elif isinstance(item, dict):
        return {k: serialize_content(v) for k, v in item.items()}
    else:
        return item  # str, int, etc.

def serialize_call_result(result):
    """
    Convierte un CallToolResult en un dict serializable a JSON.
    """
    return {
        "content": serialize_content(getattr(result, "content", None)),
        "structuredContent": serialize_content(getattr(result, "structuredContent", None)),
        "isError": getattr(result, "isError", None),
    }
