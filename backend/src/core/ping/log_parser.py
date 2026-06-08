import re
from typing import Optional, Dict

SERVICE_MAP = {
    'localhost:5000': 'jarvis-backend',
    'localhost:8000': 'contabilidad',
    'localhost:8001': 'mcp-calendar',
    'localhost:8002': 'mcp-notion',
    'localhost:8003': 'mcp-notion', # Ajustado a tu puerto real
    'mcp-nexus-spwu.onrender.com': 'mcp-calendar',
    'mcp-nexus.onrender.com': 'jarvis-backend',
    'coello-system-1.onrender.com': 'vite-dashboard'
}

def map_service_name(service: str) -> str:
    if not service: return "unknown"
    clean = re.sub(r'^https?://', '', service.strip().lower()).split('/')[0]
    return SERVICE_MAP.get(clean, clean)

def extract_service_name(url: str) -> str:
    clean = re.sub(r'^https?://', '', url.strip())
    return clean.split('/')[0].lower()

def clean_log_message(raw: str) -> str:
    if not raw: return ""
    cleaned = (
        raw.replace("→", "->").replace("ÔåÆ", "->").replace("â†’", "->")
           .replace("├│", "ó").replace("Ã³", "ó").replace("Ã¡", "á")
           .replace("Ã©", "é").replace("Ã­", "í").replace("Ãº", "ú")
    )
    cleaned = re.sub(r'^\[.*?\]\s*', '', cleaned).strip()
    return cleaned

def parse_ping_log(log_message: str) -> Optional[Dict]:
    log_message = clean_log_message(log_message)
    
    # ===============================
    # 1. Con next_ping
    # ===============================
    pattern_outgoing_next = r'(\d+)\s+Ping a\s+(https?://[\w.:/-]+).*?\|\s*next_ping\s*=\s*(\d+)s'
    match = re.search(pattern_outgoing_next, log_message, re.IGNORECASE)
    if match:
        status_code, url, seconds = match.groups()
        service_name = map_service_name(extract_service_name(url))
        return {
            'service': service_name,
            'event_type': 'outgoing_ping',
            'status_code': int(status_code),
            'next_ping_sc': int(seconds),
            'message': f'Ping exitoso a {service_name}'
        }
        
    # ===============================
    # 2. Ping saliente sin next_ping
    # ===============================
    pattern_outgoing = r'(\d+)\s+Ping a\s+(https?://[\w.:/-]+)'
    match = re.search(pattern_outgoing, log_message, re.IGNORECASE)
    if match:
        status_code_str, url = match.groups()
        service_name = map_service_name(extract_service_name(url))
        return {
            'service': service_name,
            'event_type': 'outgoing_ping',
            'status_code': int(status_code_str),
            'message': f'Ping exitoso a {service_name}'
        }

    # ===============================
    # 3. Pong recibido
    # ===============================
    pattern_incoming = r'\[PONG recibido\]\s+desde\s+(https?://[\w.:/-]+)'
    match = re.search(pattern_incoming, log_message, re.IGNORECASE)
    if match:
        url = match.group(1)
        service_name = map_service_name(extract_service_name(url))
        return {
            'service': service_name,
            'event_type': 'incoming_pong',
            'status_code': 200,
            'message': f'Pong recibido de {service_name}'
        }
        
    # ===============================
    # 4. Próximo ping
    # ===============================
    pattern_next_ping = r'\bPróximo ping en\s+(\d+)s'
    match = re.search(pattern_next_ping, log_message, re.IGNORECASE)
    if match:
        seconds = int(match.group(1))
        return {
            'service': 'unknown',
            'event_type': 'next_ping_countdown',
            'next_ping_seconds': seconds,
            'message': f'Próximo ping en {seconds}s'
        }
    return None

def parse_ping_log_v1(log_message: str) -> Optional[Dict]:
    log_message = clean_log_message(log_message)
    
    # Esta Regex es la clave:
    # 1. (\d+) -> Captura el código (200, 503, etc.)
    # 2. .*? -> Salta palabras como "OK en", "Ping a", "Error en"
    # 3. (https?://[\w.:/-]+) -> Captura la URL completa
    # 4. .*?next_ping\s*=\s*(\d+)s -> Captura los segundos
    pattern = r'(\d+)\s+.*?\s+(https?://[\w.:/-]+).*?next_ping\s*=\s*(\d+)s'
    
    match = re.search(pattern, log_message, re.IGNORECASE)
    
    if match:
        status_code, full_url, seconds = match.groups()
        
        # Extraemos el host (ej: localhost:8000) de la URL completa
        service_host = extract_service_name(full_url)
        
        # Mapeamos al nombre bonito (ej: contabilidad)
        service_name = map_service_name(service_host)
        
        # Clasificamos el evento
        e_type = "outgoing_ping" if int(status_code) < 400 else "connection_error"
        
        return {
            'service': service_name,
            'event_type': e_type,
            'status_code': int(status_code),
            'next_ping_sc': int(seconds),
            'message': log_message # Mantenemos el mensaje original limpio
        }
    
    return None