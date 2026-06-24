import re
from pathlib import Path
from src.core.logging import get_logger

logger = get_logger("security_guard")

# ==========================================
# 1. PATH SECURITY PATTERNS (File System)
# ==========================================
# Translated from TypeScript SENSITIVE_PATH_PATTERNS
SENSITIVE_PATH_PATTERNS = [
    re.compile(r"(^|/)\.ssh(/|$)"),
    re.compile(r"(^|/)\.credentials(/|$)"),
    re.compile(r"(^|/)library/keychains(/|$)"),
    re.compile(r"(^|/)\.aws/credentials$"),
    re.compile(r"(^|/)\.config/gh/hosts\.ya?ml$"),
    re.compile(r"(^|/)secrets(/|$)"),
    re.compile(r"(^|/)\.env(?:$|[./_-])"),  # Matches .env, .env.local, .env-test
    re.compile(r"\.(pem|key|p12|pfx)$", re.IGNORECASE)  # Certificates and private keys
]

def evaluate_file_security(file_path: str) -> bool:
    """
    Evaluates if a given path is safe to read/write/modify.
    Returns True if safe, False if blocked by security policies.
    """
    try:
        # Convert path to POSIX string (uses '/' even on Windows) for reliable regex matching
        path_str = Path(file_path).as_posix().lower()
        
        for pattern in SENSITIVE_PATH_PATTERNS:
            if pattern.search(path_str):
                logger.warning(f"[SECURITY GUARD] Blocked access to sensitive path: {file_path}")
                return False
                
        return True
    except Exception as e:
        logger.error(f"[SECURITY GUARD] Error parsing path {file_path}: {str(e)}")
        return False # Fail-safe: Block if we can't parse it

# ==========================================
# 2. COMMAND SECURITY PATTERNS (Bash / CLI)
# ==========================================
# Translated from TypeScript DENIED_BASH_PATTERNS (Hard Deny)
DENIED_BASH_PATTERNS = [
    re.compile(r"\brm\s+-rf\s+(?:/(?:\s|$)|~(/|\s|$)|[$]HOME(/|\s|$)|\.\.?(?:\s|$))"),
    re.compile(r"\bgit\s+reset\s+--hard\b"),
    re.compile(r"\bgit\s+clean\b(?=[^\n]*(?:-[^\n]*f|--force))(?=[^\n]*(?:-[^\n]*d|--directories))"),
    re.compile(r"\bgit(?:\s+--?\S+(?:\s+[^-\s]\S*)?)*\s+push\b(?=[^\n]*\s--force(?:-with-lease)?\b)"),
    re.compile(r"\bgit(?:\s+--?\S+(?:\s+[^-\s]\S*)?)*\s+push\b(?=[^\n]*\s-[^\s-]*f)"),
    re.compile(r"\bchmod\s+-R\s+[0-7]*7[0-7]*\b"),
    re.compile(r"\bchown\s+-R\b"),
    re.compile(r"\b(reboot|shutdown|halt|poweroff)\b"),
    re.compile(r"mkfs\b"),
    re.compile(r"dd\s+if=")
]

# Translated from TypeScript CONFIRM_BASH_PATTERNS (Requires HITL)
CONFIRM_BASH_PATTERNS = [
    re.compile(r"\bgit\s+push\b"),
    re.compile(r"\bgit\s+rebase\b"),
    re.compile(r"\bgit\s+branch\s+(?:-[a-zA-Z]*D[a-zA-Z]*|--delete\b[^\n]*--force\b)"),
    re.compile(r"\bnpm\s+publish\b"),
    re.compile(r"\bpi\s+remove\b"),
    # Base de datos (SQL rules)
    re.compile(r"DROP\s+TABLE", re.IGNORECASE),
    re.compile(r"DROP\s+DATABASE", re.IGNORECASE),
    re.compile(r"TRUNCATE\s+TABLE", re.IGNORECASE),
    re.compile(r"DELETE\s+FROM\s+\w+\s*(?!WHERE)", re.IGNORECASE)
]

def evaluate_command_security(command: str) -> tuple[str, str | None]:
    """
    Evaluates a shell command. 
    Returns a tuple: (status, matched_pattern)
      - status: "BLOCK", "CONFIRM", or "ALLOW"
      - matched_pattern: The exact regex string that was matched (or None if ALLOW)
    """
    cmd_str = command.strip()
    
    # 1. Check Hard Deny
    for pattern in DENIED_BASH_PATTERNS:
        match = pattern.search(cmd_str)
        if match:
            matched_text = match.group(0)
            logger.warning(f"[SECURITY GUARD] Destructive command blocked: {command}")
            return "BLOCK", matched_text
            
    # 2. Check HITL Confirm
    for pattern in CONFIRM_BASH_PATTERNS:
        match = pattern.search(cmd_str)
        if match:
            matched_text = match.group(0)
            logger.info(f"[SECURITY GUARD] Command requires HITL approval: {command}")
            return "CONFIRM", matched_text
            
    return "ALLOW", None