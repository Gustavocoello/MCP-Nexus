# src/services/agent/nexus/tools.py
import asyncio
import json
import json as _json
from typing import Optional, Dict, List
from langchain.tools import tool
from src.mcps.client.client_manager import MCPClientManager

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

# --- CALENDAR TOOLS ---
def build_calendar_tools(user_id: str):
    """
    Factory: genera las 12 tools de Google Calendar vinculadas a un user_id.
    """
    manager = MCPClientManager(user_id=user_id)

    def get_calendar():
        return manager.get_client("google_calendar")

    @tool
    def google_listar_calendarios() -> str:
        """Lista todos los calendarios del usuario en Google Calendar."""
        result = _run(get_calendar().google_listar_calendarios())
        return _parse_mcp_result(result)

    @tool
    def google_resumen_diario(calendar_id: str = "") -> str:
        """
        Resumen de eventos de hoy. 
        Usa calendar_id="" para todos los calendarios.
        """
        result = _run(get_calendar().google_resumen_diario(calendar_id=calendar_id or None))
        return _parse_mcp_result(result)

    @tool
    def google_resumen_semanal(calendar_id: str = "") -> str:
        """
        Resumen de eventos de la semana actual.
        Usa calendar_id="" para todos los calendarios.
        """
        result = _run(get_calendar().google_resumen_semanal(calendar_id=calendar_id or None))
        return _parse_mcp_result(result)

    @tool
    def google_disponibilidad_diaria(date: str = "", duration_minutes: int = 60) -> str:
        """
        Espacios libres del día en horario Ecuador (GMT-5).
        Input: date (YYYY-MM-DD, vacío = hoy), duration_minutes (mínimo en minutos).
        """
        result = _run(get_calendar().google_disponibilidad_diaria(
            date=date or None, duration_minutes=duration_minutes
        ))
        return _parse_mcp_result(result)

    @tool
    def google_disponibilidad_semanal(duration_minutes: int = 60) -> str:
        """Espacios libres de los próximos 7 días en horario Ecuador (GMT-5)."""
        result = _run(get_calendar().google_disponibilidad_semanal(duration_minutes=duration_minutes))
        return _parse_mcp_result(result)

    @tool
    def eventos_por_titulo(calendar_id: str, keyword: Optional[str] = None) -> str:
        """
        Busca eventos que contengan una palabra clave en el título.
        Input: calendar_id, keyword.
        """
        args = _parse_args(
            {"calendar_id": calendar_id, "keyword": keyword},
            ["calendar_id", "keyword"]
        )
        calendar_id = _clean_id(args.get("calendar_id", calendar_id))
        keyword = args.get("keyword", keyword)
        
        result = _run(get_calendar().eventos_por_titulo(calendar_id=calendar_id, keyword=keyword))
        return _parse_mcp_result(result)

    @tool
    def eventos_por_rango(calendar_id: str, start_date: str, end_date: Optional[str] = None) -> str:
        """
        Eventos de un calendario en un rango de fechas.
        Input: calendar_id, start_date (ISO), end_date (ISO).
        """
        args = _parse_args(
            {"calendar_id": calendar_id, "start_date": start_date, "end_date": end_date or ""},
            ["calendar_id", "start_date", "end_date"]
        )
        calendar_id = _clean_id(args.get("calendar_id", calendar_id))
        start_date = args.get("start_date", start_date)
        end_date = args.get("end_date", end_date)
        
        if not end_date:
            return "Error: end_date es requerido."
        
        result = _run(get_calendar().eventos_por_rango(
            calendar_id=calendar_id, start_date=start_date, end_date=end_date
        ))
        return _parse_mcp_result(result)

    @tool
    def eventos_todos_calendarios_rango(start_date: str, end_date: Optional[str] = None) -> str:
        """
        Eventos de TODOS los calendarios en un rango de fechas.
        Input: start_date (ISO), end_date (ISO).
        """
        args = _parse_args(
            {"start_date": start_date, "end_date": end_date or ""},
            ["start_date", "end_date"]
        )
        start_date = args.get("start_date", start_date)
        end_date = args.get("end_date", end_date)
        
        if not end_date:
            return "Error: end_date es requerido."
    
        result = _run(get_calendar().eventos_todos_calendarios_rango(
            start_date=start_date, end_date=end_date
        ))
        return _parse_mcp_result(result)

    @tool
    def crear_evento(summary: str, description: str = "", start_time: Optional[str] = None,
                     end_time: Optional[str] = None, calendar_id: str = "primary") -> str:
        """
        Crea un evento en Google Calendar.
        Input: summary, description, start_time (ISO), end_time (ISO), calendar_id.
        """
        safe_description = description or ""
        
        args = _parse_args(
            {
                "summary": summary, 
                "description": safe_description,
                "start_time": start_time or "", 
                "end_time": end_time or "", 
                "calendar_id": calendar_id
            },
            ["summary", "start_time", "end_time"]
        )
        summary = args.get("summary", summary)
        description = args.get("description", safe_description)
        start_time = args.get("start_time", start_time)
        end_time = args.get("end_time", end_time)
        calendar_id = _clean_id(args.get("calendar_id", calendar_id))

        # Validación manual (tú tienes el control, no Pydantic)
        if not summary or not start_time or not end_time:
            return "Error: summary, start_time y end_time son requeridos."
        
        result = _run(get_calendar().crear_evento(
            summary=summary, description=description,
            start_time=start_time, end_time=end_time, calendar_id=calendar_id
        ))
        return _parse_mcp_result(result)

    @tool
    def crear_evento_desde_texto(texto_usuario: str, calendar_id: str = "primary") -> str:
        """
        Crea un evento a partir de lenguaje natural.
        Ejemplo: "Reunión con Juan el martes a las 3pm por 1 hora".
        Input: texto_usuario, calendar_id (opcional).
        """
        result = _run(get_calendar().crear_evento_desde_texto(
            texto_usuario=texto_usuario, calendar_id=calendar_id
        ))
        return _parse_mcp_result(result)

    @tool
    def actualizar_evento(calendar_id: str, event_id: str, summary: str = "",
                          description: str = "", start_time: str = "", end_time: str = "") -> str:
        """
        Actualiza un evento existente. Solo modifica los campos que se pasen.
        Input: calendar_id, event_id (obtenido de búsqueda previa), 
               y los campos a cambiar: summary, description, start_time, end_time.
        """
        args = _parse_args(
            {"calendar_id": calendar_id, "event_id": event_id,
            "summary": summary, "description": description,
            "start_time": start_time, "end_time": end_time},
            ["calendar_id", "event_id"]
        )
        calendar_id = _clean_id(args.get("calendar_id", calendar_id))
        event_id = _clean_id(args.get("event_id", event_id))
        summary = args.get("summary", summary)
        description = args.get("description", description)
        start_time = args.get("start_time", start_time)
        end_time = args.get("end_time", end_time)
        
        result = _run(get_calendar().actualizar_evento(
            calendar_id=calendar_id, event_id=event_id,
            summary=summary or None, description=description or None,
            start_time=start_time or None, end_time=end_time or None
        ))
        return _parse_mcp_result(result)

    @tool
    def eliminar_evento(calendar_id: str, event_id: str) -> str:
        """
        Elimina un evento del calendario.
        SOLO usar cuando el usuario lo pida explícitamente.
        Input: calendar_id, event_id (obtenido de búsqueda previa).
        """
        args = _parse_args(
            {"calendar_id": calendar_id, "event_id": event_id},
            ["calendar_id", "event_id"]
        )
        calendar_id = _clean_id(args.get("calendar_id", calendar_id))
        event_id = _clean_id(args.get("event_id", event_id))
        
        result = _run(get_calendar().eliminar_evento(
            calendar_id=calendar_id, event_id=event_id
        ))
        return _parse_mcp_result(result)

    return [
        google_listar_calendarios,
        google_resumen_diario,
        google_resumen_semanal,
        google_disponibilidad_diaria,
        google_disponibilidad_semanal,
        eventos_por_titulo,
        eventos_por_rango,
        eventos_todos_calendarios_rango,
        crear_evento,
        crear_evento_desde_texto,
        actualizar_evento,
        eliminar_evento,
    ]


# --- NOTION TOOLS ---

def build_notion_tools(user_id: str):
    """
    Factory: genera las 9 tools de Notion vinculadas a un user_id específico.
    Se llama UNA vez al crear NexusAgent(user_id).
    """
    manager = MCPClientManager(user_id=user_id)

    def get_notion():
        return manager.get_client("notion")

    # ----------------------------------------------------------------

    @tool
    def notion_search(query: str) -> str:
        """
        Busca páginas, bases de datos y bloques en Notion del usuario.
        Usa esto cuando el usuario pregunte por contenido general en su Notion.
        Input: query (str) — término de búsqueda.
        """
        result = _run(get_notion().notion_search(query=query))
        return _parse_mcp_result(result)
    @tool
    def notion_get_page(page_id: str) -> str:
        """
        Obtiene el contenido completo de una página de Notion por su ID.
        Usa esto cuando ya tienes el page_id y necesitas ver su contenido.
        Input: page_id (str) — ID de la página.
        """
        result = _run(get_notion().notion_get_page(page_id=page_id))
        return _parse_mcp_result(result)

    @tool
    def notion_get_block_children(block_id: str) -> str:
        """
        Obtiene los bloques hijos de una página o bloque de Notion.
        Usa esto para leer el contenido interno de una página.
        Input: block_id (str) — ID del bloque o página.
        """
        result = _run(get_notion().notion_get_block_children(block_id=block_id))
        return _parse_mcp_result(result)

    @tool
    def notion_create_page(parent_id: str, properties: Optional [str] = None, is_db_parent: bool = True) -> str:
        """
        Crea una nueva página en Notion dentro de una base de datos o página padre.
        Usa esto cuando el usuario quiera crear una tarea, nota, o entrada nueva.
        Input: parent_id (str), properties (str JSON), is_db_parent (bool).
        """
        args = _parse_args(
            {"parent_id": parent_id, "properties": properties or "", "is_db_parent": is_db_parent},
            ["parent_id", "properties"]
        )
        parent_id = _clean_id(args.get("parent_id", parent_id))
        properties = args.get("properties", properties)
        is_db_parent = args.get("is_db_parent", is_db_parent)
        
        if not properties:
            return "Error: properties es requerido."
        
        props = json.loads(properties) if isinstance(properties, str) else properties
        result = _run(get_notion().notion_create_page(
            parent_id=parent_id, properties=props, is_db_parent=is_db_parent
        ))
        return _parse_mcp_result(result)

    @tool
    def notion_update_page_properties(page_id: str, properties: Optional [str] = None) -> str:
        """
        Actualiza las propiedades de una página existente en Notion.
        Usa esto para marcar tareas como completadas, cambiar status, fechas, etc.
        Input: page_id (str), properties (str JSON con los campos a actualizar).
        """
        args = _parse_args(
            {"page_id": page_id, "properties": properties or ""},
            ["page_id", "properties"]
        )
        page_id = _clean_id(args.get("page_id", page_id))
        properties = args.get("properties", properties)
        
        if not properties:
            return "Error: properties es requerido."

        props = _json.loads(properties) if isinstance(properties, str) else properties
        result = _run(get_notion().notion_update_page_properties(
            page_id=page_id, properties=props
        ))
        return _parse_mcp_result(result)

    @tool
    def notion_append_block_children(block_id: str, blocks: Optional [str] = None) -> str:
        """
        Añade contenido (bloques) a una página o bloque existente en Notion.
        Usa esto para agregar texto, listas, o notas a una página ya creada.
        Input: block_id (str), blocks (str JSON — lista de bloques Notion).
        """
        args = _parse_args(
            {"block_id": block_id, "blocks": blocks or ""},
            ["block_id", "blocks"]
        )
        block_id = _clean_id(args.get("block_id", block_id))
        blocks = args.get("blocks", blocks)
        
        if not blocks:
            return "Error: blocks es requerido."
        
        blocks_list = _json.loads(blocks) if isinstance(blocks, str) else blocks
        result = _run(get_notion().notion_append_block_children(
            block_id=block_id, blocks=blocks_list
        ))
        return _parse_mcp_result(result)

    @tool
    def notion_query_database(database_id: str, filter_params: Optional[str] = None) -> str:
        """
        Consulta una base de datos de Notion con filtros opcionales.
        Usa esto para listar tareas, filtrar por status, fecha, prioridad, etc.
        Input: database_id (str), filter_params (str JSON opcional con filtros Notion).
        """
        args = _parse_args(
            {"database_id": database_id, "filter_params": filter_params},
            ["database_id"]
        )
        database_id = _clean_id(args.get("database_id", database_id))
        filter_params = args.get("filter_params", filter_params)
    
        params = _json.loads(filter_params) if filter_params else None
        result = _run(get_notion().notion_query_database(
            database_id=database_id, filter_params=params
        ))
        return _parse_mcp_result(result)

    @tool
    def notion_get_database_structure(database_id: str) -> str:
        """
        Obtiene el esquema (estructura de columnas) de una base de datos Notion.
        Usa esto PRIMERO cuando no conoces las propiedades de una DB antes de crear o filtrar.
        Input: database_id (str).
        """
        result = _run(get_notion().notion_get_database_structure(database_id=database_id))
        return _parse_mcp_result(result)

    @tool
    def notion_delete_block(block_id: str) -> str:
        """
        Elimina (archiva) un bloque o página de Notion por su ID.
        Usa esto solo cuando el usuario explícitamente pida eliminar algo.
        Input: block_id (str).
        """
        result = _run(get_notion().notion_delete_block(block_id=block_id))
        return _parse_mcp_result(result)

    return [
        notion_search,
        notion_get_page,
        notion_get_block_children,
        notion_create_page,
        notion_update_page_properties,
        notion_append_block_children,
        notion_query_database,
        notion_get_database_structure,
        notion_delete_block,
    ]