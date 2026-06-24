# src/services/agent/lamar/tools/llm_monitor.py
import json
from langchain_core.tools import tool
from src.core.time_helper import get_now
from src.database.models.models import PingLog
from src.database.settings.connection import get_db
from src.services.llm.chat.llm_router import API_PROVIDERS_TO_AGENT
from src.services.agent.lamar.tools.sentinel import LamarSentinel

@tool
def trigger_full_system_check() -> str:
    """Performs a health check on all 20+ LLM providers."""
    sentinel = LamarSentinel(API_PROVIDERS_TO_AGENT)
    results = sentinel.test_all_providers(force=True)

    if not results:
        return "Error: Sentinel could not process the providers."
    alive = [r for r in results if r['status'].get('alive')]
    errors = [r for r in results if not r['status'].get('alive')]
    return (f"Check complete: {len(results)} total. "
            f"Online: {len(alive)} | Offline: {len(errors)}.")

@tool
def test_single_provider(tool_input: str) -> str:
    """Tests a single LLM provider. Input JSON: {"provider_name": "Groq"}"""
    try:
        parsed = json.loads(tool_input)
        provider_name = parsed.get("provider_name", "")
    except:
        provider_name = tool_input.strip()

    provider = next((p for p in API_PROVIDERS_TO_AGENT if p["name"] == provider_name), None)
    if not provider:
        return f"Error: Provider '{provider_name}' not found."

    sentinel = LamarSentinel([provider])
    results = sentinel.test_all_providers(force=True)
    if not results: return f"Error testing '{provider_name}'."
    
    status = results[0]["status"]
    return f"Provider: {provider_name} | Alive: {status.get('alive')} | Details: {status.get('details')}"

@tool
def diagnose_provider_failure(tool_input: str) -> str:
    """Analyzes why a provider failed. Input JSON: {"provider_name": "Groq"}"""
    try:
        parsed = json.loads(tool_input)
        provider_name = parsed.get("provider_name", "")
    except:
        provider_name = tool_input.strip()

    try:
        db = next(get_db())
        logs = db.query(PingLog).filter(PingLog.service == provider_name).order_by(PingLog.timestamp.desc()).limit(5).all()
    except Exception as e:
        return f"DB Error: {str(e)}"
    finally:
        if 'db' in locals(): db.close()

    if not logs: return f"No history found for '{provider_name}'."
    
    last = logs[0]
    if last.status_code == 200:
        return f"{provider_name} is currently healthy."
        
    error_msg = last.message or ""
    if last.status_code == 429:
        return f"DIAGNOSIS: Rate limit hit (429) for {provider_name}. FIX: Wait for cooldown."
    elif "401" in error_msg or "403" in error_msg:
        return f"DIAGNOSIS: Auth error (401/403) for {provider_name}. FIX: Check API Key."
    elif "timeout" in error_msg.lower():
        return f"DIAGNOSIS: Timeout. Endpoint unreachable."
    
    return f"DIAGNOSIS: {last.status_code}. Details: {error_msg}"

@tool
def diagnose_all_failed_providers() -> str:
    """Diagnoses ALL failed providers at once."""
    try:
        db = next(get_db())
        groups = {"429": [], "401/403": [], "timeout": [], "5xx": [], "healthy": []}

        for p in API_PROVIDERS_TO_AGENT:
            name = p["name"]
            last = db.query(PingLog).filter(PingLog.service == name).order_by(PingLog.timestamp.desc()).first()
            if not last: continue
            
            code, error = last.status_code, last.message or ""
            if code == 200: groups["healthy"].append(name)
            elif code == 429: groups["429"].append(name)
            elif "401" in error or "403" in error: groups["401/403"].append(name)
            elif "timeout" in error.lower(): groups["timeout"].append(name)
            elif code in [500, 502, 503]: groups["5xx"].append(name)

        summary = []
        for g_name, items in groups.items():
            if items: summary.append(f"{g_name.upper()} ({len(items)}): {', '.join(items)}")
        
        return "\n".join(summary) if summary else "No data."
    except Exception as e:
        return f"DB Error: {str(e)}"
    finally:
        if 'db' in locals(): db.close()

def build_llm_monitor_tools(user_id: str, client_type: str = "web") -> list:
    return [
        trigger_full_system_check,
        test_single_provider,
        diagnose_provider_failure,
        diagnose_all_failed_providers
    ]