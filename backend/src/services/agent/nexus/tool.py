# src/services/agent/nexus/tools.py
import asyncio
import json
import json as _json
from typing import Optional, Dict, List
from langchain_core.tools import tool, Tool
from langchain_core.tools import StructuredTool
from langgraph.errors import NodeInterrupt
from src.services.agent.Koda.tools.hitl import is_paused, validate_path
from langchain_core.runnables import RunnableConfig
from src.services.mcps.client.client_manager import MCPClientManager
from src.services.agent.common.mcp_errors import mcp_offline_error, mcp_no_client

# Base de datos y Chat 
from src.database.models.models import Message

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
def build_calendar_tools(user_id: str, chat_id: Optional[str] = None, db_session=None):
    """
    Factory: genera las 12 tools de Google Calendar vinculadas a un user_id.
    """
    manager = MCPClientManager(user_id=user_id)
    provider_name = "google_calendar"

    def get_calendar():
        return manager.get_client(provider_name)
    
    def _record_tool_usage(tool_name: str):
        """Guarda un registro ligero en BD de qué herramienta usó el agente."""
        if not db_session or not chat_id:
            return
        
        # 1. Guardar en la Base de Datos (rol: mcp-tool)
        # Solo guardamos el nombre de la herramienta. ¡Nada de JSONs gigantes!
        mcp_context_str = json.dumps({
            "tool_used": tool_name,
            "provider": provider_name
        })
        
        mcp_msg = Message(chat_id=chat_id, role="mcp-tool", content=mcp_context_str)
        db_session.add(mcp_msg)
        db_session.commit()
    
    @tool
    def google_listar_calendarios() -> str:
        """Lista todos los calendarios del usuario en Google Calendar."""
        try: 
            client = get_calendar()
            if not client:
                return mcp_no_client("Google Calendar")
        
            result = _run(client.google_listar_calendarios())
            _record_tool_usage("google_listar_calendarios")
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error("Google Calendar", "google_listar_calendarios", str(e))

    @tool
    def google_resumen_diario(calendar_id: str = "") -> str:
        """
        Resumen de eventos de hoy. 
        Usa calendar_id="" para todos los calendarios.
        """
        try: 
            client = get_calendar()
            if not client:
                return mcp_no_client("Google Calendar")

            result = _run(client.google_resumen_diario(calendar_id=calendar_id or None))
            _record_tool_usage("google_resumen_diario")
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error("Google Calendar", "google_resumen_diario", str(e))

    @tool
    def google_resumen_semanal(calendar_id: str = "") -> str:
        """
        Resumen de eventos de la semana actual.
        Usa calendar_id="" para todos los calendarios.
        """
        try: 
            client = get_calendar()
            if not client:
                return mcp_no_client("Google Calendar")

            result = _run(client.google_resumen_semanal(calendar_id=calendar_id or None))
            _record_tool_usage("google_resumen_semanal")
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error("Google Calendar", "google_resumen_semanal", str(e))

    @tool
    def google_disponibilidad_diaria(date: str = "", duration_minutes: int = 60) -> str:
        """
        Espacios libres del día en horario Ecuador (GMT-5).
        Input: date (YYYY-MM-DD, vacío = hoy), duration_minutes (mínimo en minutos).
        """
        try: 
            client = get_calendar()
            if not client:
                return mcp_no_client("Google Calendar")
        
            result = _run(client.google_disponibilidad_diaria(
                date=date or None, duration_minutes=duration_minutes
            ))
            _record_tool_usage("google_disponibilidad_diaria")
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error("Google Calendar", "google_disponibilidad_diaria", str(e))

    @tool
    def google_disponibilidad_semanal(duration_minutes: int = 60) -> str:
        """Espacios libres de los próximos 7 días en horario Ecuador (GMT-5)."""
        try:
            client = get_calendar()
            if not client:
                return mcp_no_client("Google Calendar")

            result = _run(client.google_disponibilidad_semanal(duration_minutes=duration_minutes))
            _record_tool_usage("google_disponibilidad_semanal")
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error("Google Calendar", "google_disponibilidad_semanal", str(e))

    @tool
    def eventos_por_titulo(calendar_id: str, keyword: Optional[str] = None) -> str:
        """
        Busca eventos que contengan una palabra clave en el título.
        Input: calendar_id, keyword.
        """
        try: 
            client = get_calendar()
            if not client:
                return mcp_no_client("Google Calendar")
            args = _parse_args(
                {"calendar_id": calendar_id, "keyword": keyword},
                ["calendar_id", "keyword"]
            )
            calendar_id = _clean_id(args.get("calendar_id", calendar_id))
            keyword = args.get("keyword", keyword)
            
            result = _run(client.eventos_por_titulo(calendar_id=calendar_id, keyword=keyword))
            _record_tool_usage("eventos_por_titulo")
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error("Google Calendar", "eventos_por_titulo", str(e))

    @tool
    def eventos_por_rango(calendar_id: str, start_date: str, end_date: Optional[str] = None) -> str:
        """
        Eventos de un calendario en un rango de fechas.
        Input: calendar_id, start_date (ISO), end_date (ISO).
        """
        try:
            client = get_calendar()
            if not client:
                return mcp_no_client("Google Calendar")

            args = _parse_args(
                {"calendar_id": calendar_id, "start_date": start_date, "end_date": end_date or ""},
                ["calendar_id", "start_date", "end_date"]
            )
            calendar_id = _clean_id(args.get("calendar_id", calendar_id))
            start_date = args.get("start_date", start_date)
            end_date = args.get("end_date", end_date)

            if not end_date:
                return "Error: end_date es requerido."

            result = _run(client.eventos_por_rango(
                calendar_id=calendar_id, start_date=start_date, end_date=end_date
            ))
            _record_tool_usage("eventos_por_rango")
            return _parse_mcp_result(result)
        except Exception as e:
                return mcp_offline_error("Google Calendar", "eventos_por_rango", str(e))

    @tool
    def eventos_todos_calendarios_rango(start_date: str, end_date: Optional[str] = None) -> str:
        """
        Eventos de TODOS los calendarios en un rango de fechas.
        Input: start_date (ISO), end_date (ISO).
        """
        try: 
            client = get_calendar()
            if not client:
                return mcp_no_client("Google Calendar")
        
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
            _record_tool_usage("eventos_todos_calendarios_rango")
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error("Google Calendar", "eventos_todos_calendarios_rango", str(e))

    @tool
    def crear_evento(summary: str, description: str = "", start_time: Optional[str] = None,
                     end_time: Optional[str] = None, calendar_id: str = "primary") -> str:
        """
        Crea un evento en Google Calendar.
        Input: summary, description, start_time (ISO), end_time (ISO), calendar_id.
        """
        try: 
            client = get_calendar()
            if not client:
                return mcp_no_client("Google Calendar")
        
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
            _record_tool_usage("crear_evento")
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error("Google Calendar", "crear_evento", str(e))

    @tool
    def crear_evento_desde_texto(texto_usuario: str, calendar_id: str = "primary") -> str:
        """
        Crea un evento a partir de lenguaje natural.
        Ejemplo: "Reunión con Juan el martes a las 3pm por 1 hora".
        Input: texto_usuario, calendar_id (opcional).
        """
        try: 
            client = get_calendar()
            if not client:
                return mcp_no_client("Google Calendar")
        
            result = _run(get_calendar().crear_evento_desde_texto(
                texto_usuario=texto_usuario, calendar_id=calendar_id
            ))
            _record_tool_usage("crear_evento_desde_texto")
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error("Google Calendar", "crear_evento_desde_texto", str(e))

    @tool
    def actualizar_evento(calendar_id: str, event_id: str, summary: str = "",
                          description: str = "", start_time: str = "", end_time: str = "") -> str:
        """
        Actualiza un evento existente. Solo modifica los campos que se pasen.
        Input: calendar_id, event_id (obtenido de búsqueda previa), 
               y los campos a cambiar: summary, description, start_time, end_time.
        """
        try: 
            client = get_calendar()
            if not client:
                return mcp_no_client("Google Calendar")
        
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
            _record_tool_usage("actualizar_evento")
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error("Google Calendar", "actualizar_evento", str(e))

    @tool
    def eliminar_evento(calendar_id: str, event_id: str) -> str:
        """
        Elimina un evento del calendario.
        SOLO usar cuando el usuario lo pida explícitamente.
        Input: calendar_id, event_id (obtenido de búsqueda previa).
        """
        try: 
            client = get_calendar()
            if not client:
                return mcp_no_client("Google Calendar")
        
            args = _parse_args(
                {"calendar_id": calendar_id, "event_id": event_id},
                ["calendar_id", "event_id"]
            )
            calendar_id = _clean_id(args.get("calendar_id", calendar_id))
            event_id = _clean_id(args.get("event_id", event_id))
            
            result = _run(get_calendar().eliminar_evento(
                calendar_id=calendar_id, event_id=event_id
            ))
            _record_tool_usage("eliminar_evento")
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error("Google Calendar", "eliminar_evento", str(e))

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

def build_notion_tools(user_id: str, chat_id: Optional[str] = None, db_session=None):
    """
    Factory: genera las 9 tools de Notion vinculadas a un user_id específico.
    Se llama UNA vez al crear NexusAgent(user_id).
    """
    manager = MCPClientManager(user_id=user_id)
    provider_name = "notion"

    def get_notion():
        return manager.get_client(provider_name)
    
    def _record_tool_usage(tool_name: str):
        """Guarda un registro ligero en BD de qué herramienta usó el agente."""
        if not db_session or not chat_id:
            return
        
        # 1. Guardar en la Base de Datos (rol: mcp-tool)
        # Solo guardamos el nombre de la herramienta. ¡Nada de JSONs gigantes!
        mcp_context_str = json.dumps({
            "tool_used": tool_name,
            "provider": provider_name
        })
        
        mcp_msg = Message(chat_id=chat_id, role="mcp-tool", content=mcp_context_str)
        db_session.add(mcp_msg)
        db_session.commit()

    # ----------------------------------------------------------------

    @tool
    def notion_search(query: str) -> str:
        """
        Busca páginas, bases de datos y bloques en Notion del usuario.
        Usa esto cuando el usuario pregunte por contenido general en su Notion.
        Input: query (str) — término de búsqueda.
        """
        try: 
            client = get_notion()
            if not client:
                return mcp_no_client("Notion")
            
            result = _run(get_notion().notion_search(query=query))
            _record_tool_usage("notion_search")
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error("Notion", "notion_search", str(e))
    @tool
    def notion_get_page(page_id: str) -> str:
        """
        Obtiene el contenido completo de una página de Notion por su ID.
        Usa esto cuando ya tienes el page_id y necesitas ver su contenido.
        Input: page_id (str) — ID de la página.
        """
        try:
            client = get_notion()
            if not client:
                return mcp_no_client("Notion")

            result = _run(get_notion().notion_get_page(page_id=page_id))
            _record_tool_usage("notion_get_page")
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error("Notion", "notion_get_page", str(e))

    @tool
    def notion_get_block_children(block_id: str) -> str:
        """
        Obtiene los bloques hijos de una página o bloque de Notion.
        Usa esto para leer el contenido interno de una página.
        Input: block_id (str) — ID del bloque o página.
        """
        try: 
            client = get_notion()
            if not client:
                return mcp_no_client("Notion")
        
            result = _run(get_notion().notion_get_block_children(block_id=block_id))
            _record_tool_usage("notion_get_block_children")
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error("Notion", "notion_get_block_children", str(e))

    @tool
    def notion_create_page(parent_id: str, properties: Optional [str] = None, is_db_parent: bool = True) -> str:
        """
        Crea una nueva página en Notion dentro de una base de datos o página padre.
        Usa esto cuando el usuario quiera crear una tarea, nota, o entrada nueva.
        Input: parent_id (str), properties (str JSON), is_db_parent (bool).
        """
        try: 
            client = get_notion()
            if not client:
                return mcp_no_client("Notion")
        
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
            _record_tool_usage("notion_create_page")
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error("Notion", "notion_create_page", str(e))

    @tool
    def notion_update_page_properties(page_id: str, properties: Optional [str] = None) -> str:
        """
        Actualiza las propiedades de una página existente en Notion.
        Usa esto para marcar tareas como completadas, cambiar status, fechas, etc.
        Input: page_id (str), properties (str JSON con los campos a actualizar).
        """
        try: 
            client = get_notion()
            if not client:
                return mcp_no_client("Notion")
        
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
            _record_tool_usage("notion_update_page_properties")
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error("Notion", "notion_update_page_properties", str(e))

    @tool
    def notion_append_block_children(block_id: str, blocks: Optional [str] = None) -> str:
        """
        Añade contenido (bloques) a una página o bloque existente en Notion.
        Usa esto para agregar texto, listas, o notas a una página ya creada.
        Input: block_id (str), blocks (str JSON — lista de bloques Notion).
        """
        try: 
            client = get_notion()
            if not client:
                return mcp_no_client("Notion")
        
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
            _record_tool_usage("notion_append_block_children")
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error("Notion", "notion_append_block_children", str(e))

    @tool
    def notion_query_database(database_id: str, filter_params: Optional[str] = None) -> str:
        """
        Consulta una base de datos de Notion con filtros opcionales.
        Usa esto para listar tareas, filtrar por status, fecha, prioridad, etc.
        Input: database_id (str), filter_params (str JSON opcional con filtros Notion).
        """
        try: 
            client = get_notion()
            if not client:
                return mcp_no_client("Notion")
        
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
            _record_tool_usage("notion_query_database")
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error("Notion", "notion_query_database", str(e))

    @tool
    def notion_get_database_structure(database_id: str) -> str:
        """
        Obtiene el esquema (estructura de columnas) de una base de datos Notion.
        Usa esto PRIMERO cuando no conoces las propiedades de una DB antes de crear o filtrar.
        Input: database_id (str).
        """
        try: 
            client = get_notion()
            if not client:
                return mcp_no_client("Notion")
        
            result = _run(get_notion().notion_get_database_structure(database_id=database_id))
            _record_tool_usage("notion_get_database_structure")
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error("Notion", "notion_get_database_structure", str(e))

    @tool
    def notion_delete_block(block_id: str) -> str:
        """
        Elimina (archiva) un bloque o página de Notion por su ID.
        Usa esto solo cuando el usuario explícitamente pida eliminar algo.
        Input: block_id (str).
        """
        try:
            client = get_notion()
            if not client:
                return mcp_no_client("Notion")

            result = _run(get_notion().notion_delete_block(block_id=block_id))
            _record_tool_usage("notion_delete_block")
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error("Notion", "notion_delete_block", str(e))

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
# --- GITHUB TOOLS ---    
def build_github_tools(user_id: str, chat_id: Optional[str] = None, db_session=None):
    """
    Factory: Genera las herramientas de GitHub para Koda.
    Incluye protección HITL para acciones de escritura (ramas, commits, PRs).
    """
    manager = MCPClientManager(user_id=user_id)
    provider_name = "github"

    def get_github():
        return manager.get_client("github")
    
    def _record_tool_usage(tool_name: str):
        """Guarda un registro ligero en BD de qué herramienta usó el agente."""
        if not db_session or not chat_id:
            return
        
        # 1. Guardar en la Base de Datos (rol: mcp-tool)
        # Solo guardamos el nombre de la herramienta. ¡Nada de JSONs gigantes!
        mcp_context_str = json.dumps({
            "tool_used": tool_name,
            "provider": provider_name
        })
        
        mcp_msg = Message(chat_id=chat_id, role="mcp-tool", content=mcp_context_str)
        db_session.add(mcp_msg)
        db_session.commit()

    # --- 🟢 ACCIONES DE LECTURA (SAFE) ---

    @tool
    def github_search_repositories(query: str) -> str:
        """
        Searches GitHub for repositories matching the query.
        Input: query (str)
        """
        try: 
            client = get_github()
            if not client:
                return mcp_no_client("GitHub")
            
            result = _run(client.github_search_repositories(query=query))
            _record_tool_usage("github_search_repositories")
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error("GitHub", "github_search_repositories", str(e))

    @tool
    def github_search_code(query: str) -> str:
        """
        Searches GitHub for specific code snippets across repositories.
        Useful to find examples of how a function is used in the wild.
        Input: query (str)
        """
        try: 
            client = get_github()
            if not client:
                return mcp_no_client("GitHub")
            
            result = _run(client.github_search_code(query=query))
            _record_tool_usage("github_search_code")
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error("GitHub", "github_search_code", str(e))

    @tool
    def github_get_file_contents(owner: str, repo: str, path: str, branch: Optional[str] = None) -> str:
        """
        Reads the content of a file from a GitHub repository.
        Input: owner (str), repo (str), path (str), branch (Optional[str])
        """
        try:
            client = get_github()
            if not client:
                return mcp_no_client("GitHub")

            result = _run(client.github_get_file_contents(owner, repo, path, branch))
            _record_tool_usage("github_get_file_contents")
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error("GitHub", "github_get_file_contents", str(e))

    @tool
    def github_get_issue(owner: str, repo: str, issue_number: int) -> str:
        """
        Fetches the details of a specific GitHub issue to understand a bug or task.
        Input: owner (str), repo (str), issue_number (int)
        """
        try:
            client = get_github()
            if not client:
                return mcp_no_client("GitHub")

            result = _run(client.github_get_issue(owner, repo, issue_number))
            _record_tool_usage("github_get_issue")
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error("GitHub", "github_get_issue", str(e))

    @tool
    def github_get_branch_sha(owner: str, repo: str, branch: str = "main") -> str:
        """
        Gets the SHA hash of a branch.
        ALWAYS use this first when you need to create a new branch, as GitHub requires the base SHA.
        Input: owner (str), repo (str), branch (str)
        """
        try:
            client = get_github()
            if not client:
                return mcp_no_client("GitHub")
            
            result = _run(client.github_get_branch_sha(owner, repo, branch))
            _record_tool_usage("github_get_branch_sha")
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error("GitHub", "github_get_branch_sha", str(e))     


    # --- 🔴 ACCIONES DE ESCRITURA (REQUIEREN HITL) *ONLY KODA* ---
    
    # --- TOOLS adicionales para Github MCP 
    @tool
    def github_list_directory(owner: str, repo: str, path: str, branch: Optional[str] = "main") -> str:
        """
        Lists ALL files inside a GitHub directory recursively.
        ALWAYS use this FIRST to know which files to download from a repository folder.
        Returns a flat JSON list with the exact paths of all files (including those in subfolders).
        Input: owner (str), repo (str), path (str), branch (Optional[str])
        """
        try:
            client = get_github()
            if not client:
                return mcp_no_client("GitHub")

            def fetch_dir(current_path: str) -> list:
                all_files = []
                # Llamada usando tu sistema actual (_run)
                result = _run(client.github_get_file_contents(owner, repo, current_path, branch))
                
                # Usamos tu parseador para sacar el string de respuesta
                content_text = _parse_mcp_result(result)
                
                try:
                    items = json.loads(content_text)
                except Exception as parse_err:
                    print(f"Error parsing JSON from GitHub MCP: {parse_err}")
                    return all_files
                
                # Si la ruta era un archivo único, devuelve dict. Si era carpeta, devuelve lista.
                if isinstance(items, dict):
                    items = [items]
                    
                for item in items:
                    if item.get("type") == "file":
                        all_files.append(item["path"])
                    elif item.get("type") == "dir":
                        # ¡Recursividad! Llama a fetch_dir de nuevo para la subcarpeta
                        sub_files = fetch_dir(item["path"])
                        all_files.extend(sub_files)
                        
                return all_files

            # Iniciamos la recursividad desde el path original
            final_files_list = fetch_dir(path)
            
            _record_tool_usage("github_list_directory")
            
            # Devolvemos la lista en formato JSON (string) para que LangGraph/LLM lo lea fácil
            return json.dumps(final_files_list)
            
        except Exception as e:
            return mcp_offline_error("GitHub", "github_list_directory", str(e))
        
    @tool
    def download_external_skill(owner: str, repo: str, path: str, branch: Optional[str] = "main") -> str:
        """
        Downloads a skill directory directly from a GitHub repository and saves it locally.
        ALWAYS use this tool to download or install a skill.
        Input: owner (str), repo (str), path (str), branch (Optional[str])
        """
        try:
            import base64
            gh_client = get_github()
            if not gh_client:
                return mcp_no_client("Github")
            
            # Importamos el manager del MCP FILES
            files_client = manager.get_client("files")
            if not files_client:
                return mcp_no_client("Files")

            # 1. Función recursiva para obtener paths
            def fetch_dir(current_path: str) -> list:
                all_files = []
                result = _run(gh_client.github_get_file_contents(owner, repo, current_path, branch))
                content_text = _parse_mcp_result(result)
                try:
                    items = json.loads(content_text)
                    if isinstance(items, dict): items = [items]
                    for item in items:
                        if item.get("type") == "file":
                            all_files.append(item["path"])
                        elif item.get("type") == "dir":
                            all_files.extend(fetch_dir(item["path"]))
                except Exception:
                    pass
                return all_files

            # 2. Obtenemos la lista de archivos
            files_to_download = fetch_dir(path)
            if not files_to_download:
                return "Error: No se encontraron archivos en la ruta."
            
            print(f"\n Descargando {len(files_to_download)} archivos...")
            
            downloaded = []
            # 3. Python hace el trabajo pesado, rápido y sin truncar
            for file_path in files_to_download:
                print(f" -> Obteniendo: {file_path}")
                gh_res = _run(gh_client.github_get_file_contents(owner, repo, file_path, branch))
                file_content = _parse_mcp_result(gh_res)
                
                content_to_write = file_content
                # Decodificamos el base64 que devuelve GitHub
                try:
                    parsed_json = json.loads(file_content)
                    # A veces GitHub lo devuelve en un array
                    if isinstance(parsed_json, list):
                        parsed_json = parsed_json[0]
                        
                    if isinstance(parsed_json, dict) and "content" in parsed_json:
                        if parsed_json.get("encoding") == "base64":
                            raw_b64 = parsed_json["content"].replace('\n', '')
                            content_to_write = base64.b64decode(raw_b64).decode("utf-8")
                        else:
                            content_to_write = parsed_json["content"]
                except Exception as e:
                    pass 
                
                # Guardamos localmente
                _run(files_client.write_file(file_path=file_path, content=content_to_write))
                downloaded.append(file_path)

            _record_tool_usage("download_external_skill")
            return f"EXITO: Se descargaron correctamente los archivos: {', '.join(downloaded)}"

        except Exception as e:
            return f"ERROR descargando skill: {str(e)}"    
    
    
    return [
        github_search_repositories,
        github_search_code,
        github_get_file_contents,
        github_get_issue,
        github_get_branch_sha,
        github_list_directory,
        download_external_skill
    ]

# --- DEVTOOLS TOOLS ---
def build_devtools_tools(user_id: str, chat_id: Optional[str] = None, db_session=None) -> List[Tool]:
    """
    Factory: genera las tools de Chrome DevTools vinculadas a un user_id.
    Se conecta dinámicamente al servidor MCP para extraer las tools y envuelve
    sus ejecuciones para guardar un historial en la BD.
    """
    manager = MCPClientManager(user_id=user_id)
    provider_name = "devtools"

    def get_devtools_client():
        return manager.get_client(provider_name)
    
    def _record_tool_usage(tool_name: str):
        """Guarda un registro en BD de la herramienta utilizada."""
        if not db_session or not chat_id:
            return
        
        mcp_context_str = json.dumps({
            "tool_used": tool_name,
            "provider": provider_name
        })
        
        mcp_msg = Message(chat_id=chat_id, role="mcp-tool", content=mcp_context_str)
        db_session.add(mcp_msg)
        db_session.commit()

    async def fetch_tools():
        client = get_devtools_client()
        
        # Entramos en el contexto para inicializar la sesión MCP.
        # Esto permite que client.get_langchain_tools() lea el esquema exitosamente.
        async with client:
            tools = await client.get_langchain_tools()
            
            wrapped_tools = []
            for t in tools:
                original_sync = t.func
                original_async = t.coroutine
                
                # Creamos closures para atrapar el nombre e inyectar el logging a la base de datos
                def make_sync_wrapper(name, orig_func):
                    def sync_wrapper(*args, **kwargs):
                        _record_tool_usage(name)
                        return orig_func(*args, **kwargs)
                    return sync_wrapper

                def make_async_wrapper(name, orig_coro):
                    async def async_wrapper(*args, **kwargs):
                        _record_tool_usage(name)
                        return await orig_coro(*args, **kwargs)
                    return async_wrapper

                # Recreamos el StructuredTool para no mutar el objeto original 
                # y mantener la compatibilidad con los validadores de Pydantic
                wrapped_tool = StructuredTool.from_function(
                    func=make_sync_wrapper(t.name, original_sync),
                    coroutine=make_async_wrapper(t.name, original_async) if original_async else None,
                    name=t.name,
                    description=t.description,
                    args_schema=t.args_schema
                )
                wrapped_tools.append(wrapped_tool)
                
            return wrapped_tools

    try:
        # Extraemos todo sincronamente antes de pasárselo al LLM
        return _run(fetch_tools())
    except Exception as e:
        print(f"Error cargando tools de DevTools: {str(e)}")
        return []
    
def build_files_tools(user_id: str, chat_id: Optional[str] = None, db_session=None):
    """
    Factory: genera las herramientas para interactuar con archivos locales (Files MCP).
    Versión limpia SIN HITL, ideal para Nexus y Jarvis.
    """
    manager = MCPClientManager(user_id=user_id)
    provider_name = "files"

    def get_files():
        return manager.get_client(provider_name)
    
    def _record_tool_usage(tool_name: str):
        """Guarda un registro ligero en BD de qué herramienta usó el agente."""
        if not db_session or not chat_id:
            return
        
        # 1. Guardar en la Base de Datos (rol: mcp-tool)
        # Solo guardamos el nombre de la herramienta. ¡Nada de JSONs gigantes!
        mcp_context_str = json.dumps({
            "tool_used": tool_name,
            "provider": provider_name
        })
        
        mcp_msg = Message(chat_id=chat_id, role="mcp-tool", content=mcp_context_str)
        db_session.add(mcp_msg)
        db_session.commit()
    
    # --- FILES MCP TOOLS ---

    @tool
    def list_directory(directory_path: str = ".") -> str:
        """
        Lists all files and folders inside a specific directory.
        Use this to understand the project structure before taking actions.
        Input: directory_path (str)
        """
        try:
            client = get_files()
            if not client:
                return mcp_no_client("Files")
                
            result = _run(client.list_directory(directory_path=directory_path))
            _record_tool_usage("list_directory")
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error("Files", "list_directory", str(e))

    @tool
    def read_file(file_path: str) -> str:
        """
        Reads the full content of a local file in the workspace.
        ALWAYS use this to read 'AGENTS.md' or source code files before editing them.
        Input: file_path (str)
        """
        try:
            client = get_files()
            if not client:
                return mcp_no_client("Files")

            result = _run(client.read_file(file_path=file_path))
            _record_tool_usage("read_file")
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error("Files", "read_file", str(e))

    @tool
    def search_items(query: str, search_type: str = "all") -> str:
        """
        Searches recursively for files or folders matching a specific name inside the ENTIRE project.
        'search_type' can be 'file', 'dir', or 'all'.
        ALWAYS use this tool FIRST if you don't know the exact path of a folder or file!
        """
        try:
            client = get_files()
            if not client:
                return mcp_no_client("Files")

            result = _run(client.search_items(query=query, search_type=search_type))
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error("Files", "search_items", str(e))

    @tool
    def set_workspace(new_absolute_path: str) -> str:
        """
        Changes the root working directory of the project.
        Use this when the user asks to work on a completely different project or path on their computer.
        Input must be an absolute path (e.g. 'C:/Users/Name/Projects/NewApp').
        """
        try:
            client = get_files()
            if not client: 
                return mcp_no_client("Files")
            
            result = _run(client.set_workspace(new_absolute_path=new_absolute_path))
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error("Files", "set_workspace", str(e))

    @tool
    def get_directory_tree(directory_path: str = ".", max_depth: int = 3) -> str:
        """
        Generates a visual map (tree) of a folder and all its subfolders.
        ALWAYS use this tool FIRST when exploring a new folder to understand its structure instantly,
        instead of listing directories one by one.
        """
        try:
            client = get_files()
            if not client: 
                return mcp_no_client("Files")
            
            result = _run(client.get_tree(directory_path=directory_path, max_depth=max_depth))
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error("Files", "get_directory_tree", str(e))

    @tool
    def write_file(file_path: str, content: str, config: RunnableConfig) -> str:
        """
        Creates a new file at the given path with the provided content.
        RESTRICTED: only paths under 'skills/' are allowed.
        Use ONLY for skill-download tasks: writing SKILL.md, assets/*, references/*
        downloaded from a GitHub repo into skills/{skill-name}/.
        Input: file_path (str), content (str)
        """            
        configurable = config.get("configurable", {})
        session_id = configurable.get("session_id")

        if session_id and is_paused(session_id):
            raise NodeInterrupt(f"La sesión {session_id} ha sido pausada.")

        # 1. Path traversal — SIEMPRE
        path_check = validate_path(file_path)
        if not path_check.is_safe:
            return path_check.block_message()

        # 2. Restricción a skills/ — SIEMPRE
        normalized = file_path.replace("\\", "/").lstrip("./")
        if not normalized.startswith("skills/"):
            return (
                f"HITL_BLOCKED: '{file_path}' está fuera de skills/. "
                "Nexus solo puede escribir dentro de skills/."
            )

        # 3. Ejecutar directamente — sin hitl_guard de contenido
        try:
            client = get_files()
            if not client:
                return mcp_no_client("Files")
            
            result = _run(client.write_file(file_path=file_path, content=content))
            _record_tool_usage("write_file")
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error("Files", "write_file", str(e))
        
    @tool
    def list_skills_tool(_: str = "") -> str:
        """
        Lists all available skills found in the skills/ directory.
        Use this to discover what skills are installed in the system.
        """
        try:
            client = get_files()
            if not client:
                return mcp_offline_error("Files")
            
            result = _run(client.list_skills())
            _record_tool_usage("list_skills")
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error("Files", "list_skills_tool", str(e))
        
        

    return [
        list_directory,
        search_items,
        read_file,
        set_workspace,
        get_directory_tree,
        write_file,
        list_skills_tool
    ]