# src/services/llm/lamar/tools.py
import os
import json
from langchain.tools import tool
from .sentinel import LamarSentinel
from datetime import datetime, timedelta
from src.config.time_helper import get_now
from src.database.models.models import LLMLog, PingLog
from src.database.config.connection import SessionLocal 
from src.services.llm.llm_router import API_PROVIDERS_TO_AGENT

@tool
def report_provider_status(tool_input: str) -> str:
    """
    Records the status of an LLM provider in the database.
    Input must be a JSON string with fields: provider_name, status, details.
    Example: {{"provider_name": "Groq", "status": "OK", "details": "Working fine"}}
    """
    try:
        parsed = json.loads(tool_input)
        provider_name = parsed.get("provider_name", "unknown")
        status = parsed.get("status", "unknown")
        details = parsed.get("details", "no details")
    except (json.JSONDecodeError, AttributeError):
        provider_name = tool_input[:18]
        status = "unknown"
        details = "parse error"

    status_code = 200 if status.lower() == "ok" else 429
    # short message: code|status
    message = f"{status_code}|{details[:50]}"

    session = SessionLocal()
    try:
        new_ping = PingLog(
            service=provider_name[:18],
            event_type="lamar_check",
            message=message,
            status_code=status_code,
            timestamp=get_now()
        )
        session.add(new_ping)
        session.commit()
        return f"Status of {provider_name} saved successfully."
    except Exception as e:
        session.rollback()
        return f"Database error: {str(e)}"
    finally:
        session.close()
@tool
def get_llm_usage_report():
    """Consulta los tokens consumidos en las últimas 24 horas y cierra la sesión."""
    session = SessionLocal()
    try:
        hace_24h = get_now() - timedelta(hours=24)
        logs = session.query(LLMLog).filter(LLMLog.timestamp >= hace_24h).all()
        
        if not logs:
            return "Lamar Report: No hay consumo registrado en las últimas 24h."
        
        # Resumen rápido para el pensamiento de Lamar
        resumen = {}
        for log in logs:
            resumen[log.model_name] = resumen.get(log.model_name, 0) + log.total_tokens
        
        report_str = ", ".join([f"{mod}: {tok} tokens" for mod, tok in resumen.items()])
        return f"Consumo 24h: {report_str}"
    finally:
        session.close()
        
@tool
def trigger_full_system_check():
    """Performs a health check on all 20+ LLM providers."""
    from src.services.llm.llm_router import API_PROVIDERS_TO_AGENT

    sentinel = LamarSentinel(API_PROVIDERS_TO_AGENT)  # already a list, no changes needed
    results = sentinel.test_all_providers(force=True)

    if not results:
        return "Error: Sentinel could not process the providers. Check the list."

    alive = [r for r in results if r['status'].get('alive')]
    errors = [r for r in results if not r['status'].get('alive')]

    return (
        f"Check complete: {len(results)} total. "
        f"Online: {len(alive)} | Offline: {len(errors)}. "
        f"Failed: {[e['name'] for e in errors] if errors else 'None'}"
    )
    
@tool
def test_single_provider(tool_input: str) -> str:
    """
    Tests a single LLM provider by sending a real ping.
    Input must be a JSON string with field: provider_name.
    Example: {{"provider_name": "TNG: DeepSeek R1T2 Chimera"}}
    """
    import json
    from src.services.llm.llm_router import API_PROVIDERS_TO_AGENT

    try:
        parsed = json.loads(tool_input)
        provider_name = parsed.get("provider_name", "")
    except (json.JSONDecodeError, AttributeError):
        provider_name = tool_input.strip()

    # Find the provider in the list
    provider = next((p for p in API_PROVIDERS_TO_AGENT if p["name"] == provider_name), None)

    if not provider:
        return f"Error: Provider '{provider_name}' not found in the list."

    sentinel = LamarSentinel([provider])
    results = sentinel.test_all_providers(force=True)

    if not results:
        return f"Error: Could not test provider '{provider_name}'."

    result = results[0]
    status = result["status"]

    return (
        f"Provider: {provider_name} | "
        f"Alive: {status.get('alive')} | "
        f"Latency: {status.get('latency_ms', 0):.0f}ms | "
        f"Details: {status.get('details', 'N/A')}"
    )

@tool
def get_current_datetime_and_knowledge_info() -> str:
    """
    Returns the current date and time in Ecuador, and information about
    Lamar's knowledge cutoff. Use this when the Boss asks what day it is,
    what time it is, or what Lamar knows about recent events.
    """
    now = get_now()
    
    return (
        f"Current date and time in Ecuador (America/Guayaquil): "
        f"{now.strftime('%A, %B %d, %Y at %H:%M:%S %Z')}. "
        f"Lamar's underlying model (llama-3.3-70b-versatile) has a knowledge cutoff "
        f"of early 2024. Events after that date are unknown unless reported via tools or context. "
        f"For real-time provider status, use the system check tools."
    )

@tool
def diagnose_provider_failure(tool_input: str) -> str:
    """
    Analyzes why a provider failed and suggests a fix.
    Input: JSON with field: provider_name
    Example: {{"provider_name": "Cloudflare: Nodo-Alfa (Llama 3.1)"}}
    """

    try:
        parsed = json.loads(tool_input)
        provider_name = parsed.get("provider_name", "")
    except:
        provider_name = tool_input.strip()

    # Get last 5 logs for this provider
    session = SessionLocal()
    try:
        logs = session.query(PingLog).filter(
            PingLog.service == provider_name
        ).order_by(PingLog.timestamp.desc()).limit(5).all()
    finally:
        session.close()

    if not logs:
        return f"No history found for '{provider_name}'. Never tested or wrong name."

    last = logs[0]
    error_msg = last.message or ""
    code = last.status_code

    # Diagnosis logic
    if code == 200:
        return f"{provider_name} is currently healthy. Last check: {last.timestamp}."

    diagnosis = f"Provider: {provider_name}\nLast status: {code}\nError: {error_msg}\n\n"

    if code == 429:
        diagnosis += (
            "DIAGNOSIS: Rate limit hit (429).\n"
            "CAUSE: Too many requests to this API key.\n"
            "FIX: Nothing to do programmatically. Wait for cooldown to expire. "
            "Consider adding a new API key for this provider in llm_router.py."
        )
    elif "401" in error_msg or "403" in error_msg:
        diagnosis += (
            "DIAGNOSIS: Authentication error (401/403).\n"
            "CAUSE: Invalid or expired API key.\n"
            "FIX: Check the environment variable for this provider's key. "
            "Verify the key is still valid in the provider's dashboard."
        )
    elif "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
        diagnosis += (
            "DIAGNOSIS: Connection timeout.\n"
            "CAUSE: Provider endpoint is too slow or unreachable.\n"
            "FIX: Increase timeout in check_capabilities() or skip this provider temporarily. "
            "Check if the provider has a status page reporting incidents."
        )
    elif "connection" in error_msg.lower() or "network" in error_msg.lower():
        diagnosis += (
            "DIAGNOSIS: Network/connection error.\n"
            "CAUSE: DNS failure, firewall, or provider endpoint is down.\n"
            "FIX: Verify the base_url in API_PROVIDERS_TO_AGENT is correct. "
            "Check if the provider has an active incident."
        )
    elif "404" in error_msg:
        diagnosis += (
            "DIAGNOSIS: Endpoint not found (404).\n"
            "CAUSE: The model name or base_url may be wrong or deprecated.\n"
            "FIX: Check the model string in API_PROVIDERS_TO_AGENT matches "
            "the provider's current available models."
        )
    elif "500" in error_msg or "502" in error_msg or "503" in error_msg:
        diagnosis += (
            "DIAGNOSIS: Provider server error (5xx).\n"
            "CAUSE: The provider's backend is failing, not our fault.\n"
            "FIX: Wait and retry. Provider is likely having an incident. "
            "Check their status page. Cooldown applied automatically for 5 min."
        )
    else:
        diagnosis += (
            f"DIAGNOSIS: Unknown error.\n"
            f"CAUSE: Unrecognized error pattern.\n"
            f"FIX: Review the full error manually: {error_msg}"
        )

    # Pattern: check if it fails consistently
    all_failed = all(l.status_code != 200 for l in logs)
    if all_failed and len(logs) >= 3:
        diagnosis += "\n\nWARNING: This provider has failed consistently in the last 3+ checks. Consider removing it from rotation."

    return diagnosis

@tool
def diagnose_all_failed_providers() -> str:
    """
    Diagnoses ALL failed providers at once and returns a grouped summary.
    Use this when the Boss asks to diagnose or fix all failing providers.
    Never diagnose providers one by one if there are multiple failures.
    """

    session = SessionLocal()
    try:
        report = []
        groups = {"429": [], "401/403": [], "timeout": [], "5xx": [], "unknown": [], "healthy": []}

        for p in API_PROVIDERS_TO_AGENT:
            name = p["name"]
            last = session.query(PingLog).filter(
                PingLog.service == name
            ).order_by(PingLog.timestamp.desc()).first()

            if not last:
                groups["unknown"].append(f"{name}: Never tested")
                continue

            code = last.status_code
            error = last.message or ""

            if code == 200:
                groups["healthy"].append(name)
            elif code == 429:
                groups["429"].append(name)
            elif "401" in error or "403" in error:
                groups["401/403"].append(f"{name}: Bad API key")
            elif "timeout" in error.lower():
                groups["timeout"].append(f"{name}: Endpoint too slow")
            elif code in [500, 502, 503]:
                groups["5xx"].append(f"{name}: Provider server error")
            else:
                groups["unknown"].append(f"{name}: {error[:80]}")

        summary = []

        if groups["healthy"]:
            summary.append(f"HEALTHY ({len(groups['healthy'])}): {', '.join(groups['healthy'])}")

        if groups["429"]:
            summary.append(
                f"RATE LIMITED 429 ({len(groups['429'])}): {', '.join(groups['429'])}\n"
                f"  FIX: Wait for cooldown. Add new API keys in llm_router.py."
            )

        if groups["401/403"]:
            summary.append(
                f"BAD API KEY ({len(groups['401/403'])}): {', '.join(groups['401/403'])}\n"
                f"  FIX: Check and rotate the API keys in your .env file."
            )

        if groups["timeout"]:
            summary.append(
                f"TIMEOUT ({len(groups['timeout'])}): {', '.join(groups['timeout'])}\n"
                f"  FIX: Increase timeout in check_capabilities() or skip these providers."
            )

        if groups["5xx"]:
            summary.append(
                f"SERVER ERROR ({len(groups['5xx'])}): {', '.join(groups['5xx'])}\n"
                f"  FIX: Provider-side issue. Wait and retry later."
            )

        if groups["unknown"]:
            summary.append(
                f"UNKNOWN ERROR ({len(groups['unknown'])}): {', '.join(groups['unknown'])}\n"
                f"  FIX: Review logs manually."
            )

        return "\n\n".join(summary) if summary else "No provider data found in database."

    finally:
        session.close()
        
@tool
def ping_services() -> str:
    """
    Performs a real HTTP ping to all monitored services and saves results to DB.
    Use when Boss asks if services are up, running, or reachable.
    """
    import requests as req

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
        status_code = 0
        log_message = ""

        # same block as keep_alive_jarvis.py, just synchronous
        try:
            resp = req.get(url, timeout=10)
            status_code = resp.status_code
            log_message = f"{status_code}|ping ok"
        except Exception:
            status_code = 500
            log_message = "500|host down"

        db = SessionLocal()
        try:
            new_log = PingLog(
                service=service_name,
                event_type="lamar_ping",       # <-- lamar identifies itself
                message=log_message,
                status_code=status_code,
                client_ip="lamar",
                next_ping_sc=None,
                timestamp=now
            )
            db.add(new_log)
            db.commit()
        except Exception as db_e:
            db.rollback()
            print(f"db error ping ({service_name}): {db_e}")
        finally:
            db.close()

        alive = status_code in [200, 201]
        results.append(
            f"{service_name}: {'ok' if alive else 'down'} | {status_code} | {url}"
        )

    return "ping results:\n" + "\n".join(results) if results else "no targets configured"


@tool
def ping_single_service(tool_input: str) -> str:
    """
    Pings a single monitored service by name and saves result to DB.
    Input must be a JSON string with field: service_name.
    Example: {{"service_name": "mcp-notion"}}
    Accepted names: jarvis-backend, contabilidad, mcp-calendar, mcp-notion
    """
    import json
    import re
    import requests as req

    try:
        parsed = json.loads(tool_input)
        service_name = parsed.get("service_name", "").lower().strip()
    except (json.JSONDecodeError, AttributeError):
        service_name = tool_input.lower().strip()

    render = os.getenv("RENDER_SERVER", "false").lower() == "true"

    # Map aliases to canonical name + url
    SERVICE_URL_MAP = {
        "contabilidad":  os.getenv("TARGET_DEPLOYED1") if render else os.getenv("LOCAL_TARGET1"),
        "mcp-calendar":  os.getenv("TARGET_DEPLOYED2") if render else os.getenv("LOCAL_TARGET2"),
        "mcp-notion":    os.getenv("TARGET_DEPLOYED3") if render else os.getenv("LOCAL_TARGET3"),
    }

    # Normalize aliases to canonical name
    ALIAS_MAP = {
        "notion":           "mcp-notion",
        "mcp-notion":       "mcp-notion",
        "calendar":         "mcp-calendar",
        "mcp-calendar":     "mcp-calendar",
        "google calendar":  "mcp-calendar",
        "contabilidad":     "contabilidad",
        "vite":             "contabilidad",
        "dashboard":        "contabilidad",
        "sistema":          "contabilidad",
    }

    canonical = ALIAS_MAP.get(service_name)
    if not canonical:
        available = ", ".join(ALIAS_MAP.keys())
        return f"unknown service '{service_name}'. available: {available}"

    url = SERVICE_URL_MAP.get(canonical)
    if not url:
        return f"url not configured for '{canonical}'. check your .env file."

    now = get_now()
    status_code = 0

    try:
        resp = req.get(url, timeout=10)
        status_code = resp.status_code
        log_message = f"{status_code}|ping ok"
    except Exception:
        status_code = 500
        log_message = "500|host down"

    db = SessionLocal()
    try:
        new_log = PingLog(
            service=canonical,
            event_type="lamar_ping",
            message=log_message,
            status_code=status_code,
            client_ip="lamar",
            next_ping_sc=None,
            timestamp=now
        )
        db.add(new_log)
        db.commit()
    except Exception as db_e:
        db.rollback()
        print(f"db error ping ({canonical}): {db_e}")
    finally:
        db.close()

    alive = status_code in [200, 201]
    return (
        f"service: {canonical}\n"
        f"status: {'ok' if alive else 'down'}\n"
        f"code: {status_code}\n"
        f"url: {url}"
    )