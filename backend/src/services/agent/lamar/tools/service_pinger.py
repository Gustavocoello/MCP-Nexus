# src/services/agent/lamar/tools/service_pinger.py
import os
import json
import requests as req
from langchain_core.tools import tool
from src.core.time_helper import get_now
from src.database.models.models import PingLog
from src.database.settings.connection import get_db

@tool
def ping_services() -> str:
    """
    Performs a real HTTP ping to all monitored services and saves results to DB.
    Use when Boss asks if services are up, running, or reachable.
    """
    render = os.getenv("RENDER_SERVER", "false").lower() == "true"

    SERVICE_MAP = {
        'localhost:5000': 'jarvis-backend',
        'localhost:8000': 'contabilidad',
        'localhost:8001': 'mcp-calendar',
        'localhost:8002': 'mcp-notion',
        'coello-system-1.onrender.com': 'vite-dashboard',
        'mcp-nexus-spwu.onrender.com': 'mcp-calendar',
        'mcp-nexus.onrender.com': 'jarvis-backend',
    }

    def get_service_name(url: str) -> str:
        import re
        clean = re.sub(r'^https?://', '', url.strip().lower()).split('/')[0]
        return SERVICE_MAP.get(clean, clean)

    targets = [
        os.getenv("TARGET_DEPLOYED1") if render else os.getenv("LOCAL_TARGET1"),
        os.getenv("TARGET_DEPLOYED2") if render else os.getenv("LOCAL_TARGET2"),
        os.getenv("TARGET_DEPLOYED3") if render else os.getenv("LOCAL_TARGET3"),
    ]

    results = []
    for url in targets:
        if not url:
            continue

        service_name = get_service_name(url)
        now = get_now()
        
        try:
            resp = req.get(url, timeout=10)
            status_code = resp.status_code
            log_message = f"{status_code}|ping ok"
        except Exception:
            status_code = 500
            log_message = "500|host down"

        try:
            db = next(get_db())
            new_log = PingLog(
                service=service_name,
                event_type="lamar_ping",
                message=log_message,
                status_code=status_code,
                client_ip="lamar",
                timestamp=now
            )
            db.add(new_log)
            db.commit()
        except Exception as db_e:
            if 'db' in locals(): db.rollback()
            print(f"db error ping ({service_name}): {db_e}")
        finally:
            if 'db' in locals(): db.close()

        alive = status_code in [200, 201]
        results.append(f"{service_name}: {'ok' if alive else 'down'} | {status_code} | {url}")

    return "ping results:\n" + "\n".join(results) if results else "no targets configured"

@tool
def ping_single_service(tool_input: str) -> str:
    """
    Pings a single monitored service by name and saves result to DB.
    Input JSON: {"service_name": "mcp-notion"}
    """
    try:
        parsed = json.loads(tool_input)
        service_name = parsed.get("service_name", "").lower().strip()
    except:
        service_name = tool_input.lower().strip()

    render = os.getenv("RENDER_SERVER", "false").lower() == "true"
    
    SERVICE_URL_MAP = {
        "contabilidad":  os.getenv("TARGET_DEPLOYED1") if render else os.getenv("LOCAL_TARGET1"),
        "mcp-calendar":  os.getenv("TARGET_DEPLOYED2") if render else os.getenv("LOCAL_TARGET2"),
        "mcp-notion":    os.getenv("TARGET_DEPLOYED3") if render else os.getenv("LOCAL_TARGET3"),
        "mcp_github":    os.getenv("TARGET_DEPLOYED5") if render else os.getenv("LOCAL_TARGET5")
    }

    ALIAS_MAP = {
        "notion": "mcp-notion", "mcp-notion": "mcp-notion", "calendar": "mcp-calendar",
        "mcp-calendar": "mcp-calendar", "contabilidad": "contabilidad", "sistema": "contabilidad", "github":"mcp_github", "mcp_github": "mcp_github"
    }

    canonical = ALIAS_MAP.get(service_name)
    if not canonical:
        return f"unknown service '{service_name}'."
    url = SERVICE_URL_MAP.get(canonical)
    if not url:
        return f"url not configured for '{canonical}'."

    try:
        resp = req.get(url, timeout=10)
        status_code = resp.status_code
        log_message = f"{status_code}|ping ok"
    except Exception:
        status_code = 500
        log_message = "500|host down"

    try:
        db = next(get_db())
        new_log = PingLog(
            service=canonical, event_type="lamar_ping", message=log_message,
            status_code=status_code, client_ip="lamar", timestamp=get_now()
        )
        db.add(new_log)
        db.commit()
    except Exception:
        if 'db' in locals(): db.rollback()
    finally:
        if 'db' in locals(): db.close()

    alive = status_code in [200, 201]
    return f"service: {canonical}\nstatus: {'ok' if alive else 'down'}\ncode: {status_code}\nurl: {url}"

def build_service_pinger_tools() -> list:
    return [
        ping_services, 
        ping_single_service
    ]