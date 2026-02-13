import re
import spacy

# Cargar modelos una sola vez (lazy loading)
_nlp = None

def get_nlp():
    global _nlp
    if _nlp is None:
        _nlp = spacy.load("es_core_news_sm")
    return _nlp

def build_memory_context(memories):
    """Construye el contexto de memoria como string legible para el LLM."""
    return "\n".join(f"{m.key}: {m.value}" for m in memories)


def extract_memory_from_text(text):
    """Extrae posibles memorias explícitas del texto del usuario."""
    patterns = [
    r"(?i)recuerda que[:]? (.+)",   # (?i) para case insensitive y [:]? para aceptar o no ":"
    r"(?i)guarda esto[:]? (.+)",
    r"(?i)recuerda[:]? (.+)",
    r"(?i)importante[:]? (.+)",
    r"(?i)me gusta[:]? (.+)",
    r"(?i)prefiero[:]? (.+)"
    ]
    memories = []
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            memories.append(match.group(1).strip())
    return memories


def calculate_priority(memory_text):
    """Asigna una prioridad heurística a la memoria según su contenido."""
    priority_keywords = {
        "urgente": 10,
        "importante": 8,
        "nunca": 7,
        "siempre": 7,
        "odio": 6,
        "gusta": 5,
        "prefiero": 5
    }

    priority = 3  # Por defecto
    text_clean = re.sub(r"[^\w\s]", "", memory_text.lower())

    for keyword, score in priority_keywords.items():
        if keyword in text_clean:
            priority = max(priority, score)

    if "!" in memory_text:
        priority += 2

    return min(priority, 10)


def extract_entities(text):
    """Extrae entidades nombradas del texto."""
    nlp = get_nlp()
    doc = nlp(text)
    return [(ent.text, ent.label_, ent.start_char, ent.end_char) for ent in doc.ents]


def classify_memory(memory_text):
    """Clasificación heurística ligera sin modelos pesados."""
    text = memory_text.lower()

    if any(kw in text for kw in ["me gusta", "prefiero", "odio", "encanta"]):
        return "preferencia"
    elif any(kw in text for kw in ["nació", "vive", "es", "trabaja"]):
        return "persona"
    elif any(kw in text for kw in ["el", "la", "un", "una", "es", "son", "fue", "estuvo"]):
        return "hecho"
    elif any(kw in text for kw in ["evento", "concierto", "reunión", "cumpleaños"]):
        return "evento"
    else:
        return "hecho"  # fallback
