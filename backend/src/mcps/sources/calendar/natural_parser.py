import re
from datetime import datetime, timedelta
from typing import Optional
import pytz
import dateparser
from dateparser.search import search_dates
from mcps.core.models import Event

def parse_natural_language_to_event(input_text: str) -> Optional[Event]:
    """
    Parsea un string en lenguaje natural y construye un objeto Event.
    Ej.: "Reunión con marketing el viernes a las 3pm durante 1 hora"
    """
    # 1) Base para relativos: hoy en Lima
    lima_tz = pytz.timezone("America/Lima")
    base_dt = datetime.now(lima_tz)

    settings = {
        "PREFER_DATES_FROM": "future",
        "RETURN_AS_TIMEZONE_AWARE": True,
        "RELATIVE_BASE": base_dt,
        "TO_TIMEZONE": "America/Lima"
    }

    # 2) Intento parse directo
    dt = dateparser.parse(input_text, languages=["es"], settings=settings)

    # 3) Fallback: usar search_dates si parse es None
    if dt is None:
        results = search_dates(input_text, languages=["es"], settings=settings)
        if results and len(results) > 0:
            # results: list of (matched_text, datetime)
            dt = results[0][1]
        else:
            print("⚠️ No se pudo interpretar la fecha y hora.")
            return None

    # 4) Detectar duración (por defecto 1h)
    duration = timedelta(hours=1)
    m = re.search(r"(\d+)\s*(minutos|minuto|horas|hora)", input_text.lower())
    if m:
        n, unit = int(m.group(1)), m.group(2)
        duration = timedelta(hours=n) if "hora" in unit else timedelta(minutes=n)

    # 5) Extraer título (antes de "el", "a las", etc.)
    title = re.split(r"\s+(?:el|a las|mañana|hoy|pasado mañana)\b", input_text, maxsplit=1)[0]
    title = title.strip().capitalize()

    # 6) Construir Event
    return Event(
        title=title,
        description="Evento generado desde texto natural",
        start_time=dt,
        end_time=dt + duration,
        location=None,
        attendees=None
    )
