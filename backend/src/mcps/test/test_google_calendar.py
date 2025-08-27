import os
import sys
import pytz
import pytest
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone

datetime.now(timezone.utc)

# --- Path Fix ---
current_dir = Path(__file__).resolve().parent
src_dir = current_dir.parent.parent.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

# --- Imports del proyecto ---
from src.mcps.sources.calendar.natural_parser import parse_natural_language_to_event
from src.mcps.sources.calendar.google_calendar import GoogleCalendarConnector
from src.mcps.core.models import Event

load_dotenv()

USUARIO_TEST = os.getenv("USUARIO_TEST")


def connector():
    connector = GoogleCalendarConnector(user_id=USUARIO_TEST)
    connector.authenticate() 
    return connector


def test_calendar_connection(connector):
    """Verifica que se pueda autenticar y construir el servicio."""
    assert connector.service is not None, "Falló la autenticación o construcción del servicio"
    print("✅ Servicio de Google Calendar autenticado correctamente.")


def test_fetch_events_basic(connector):
    """Busca eventos en los últimos 15 días."""
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=15)

    print(f"🔍 Buscando eventos entre {start_date.date()} y {end_date.date()}...")
    events = connector.fetch_events_by_range(start_date, end_date)

    if not events:
        print("⚠️ No se encontraron eventos.")
    else:
        print(f"✅ {len(events)} eventos encontrados:")
        for e in events:
            print(f"📅 {e.title} | {e.start_time} -> {e.end_time}")

""""
#def test_create_event(connector):
    #Crea un evento en un slot libre sin conflictos.
    date = datetime.now(timezone.utc).date()
    free_slots = connector.get_free_slots("primary", date)

    assert free_slots, "❌ No hay espacios libres para testear creación de evento."

    slot = free_slots[0]
    start_time = slot.start_time
    end_time = start_time + timedelta(minutes=30)  # usamos menos del slot

    event = Event(
        title="🧪 Test de evento libre",
        description="Evento creado automáticamente en un slot libre.",
        start_time=start_time,
        end_time=end_time
    )

    response = connector.create_event("primary", event)

    assert not isinstance(response, dict), f"❌ Falló la creación del evento: {response.get('error')}"
    print("✅ Evento de prueba creado correctamente.")


#def test_actualizar_evento(connector):
    #Actualiza un evento específico por ID.
    calendar_id = "primary"
    event_id = "b628ii8c265anhc3jgqa5cj8cc"  # ⚠️ Asegúrate que este ID sea válido

    cambios = {
        "summary": "🛠️ Evento actualizado por MCP-prueba",
        "description": "Esto es un test de actualización",
    }

    result = connector.update_event(calendar_id, event_id, cambios)
    assert not isinstance(result, dict), f"Error al actualizar: {result.get('error')}"
    print(f"✅ Evento actualizado: {result.title} - {result.description}")


#def test_eliminar_evento(connector):
    #Elimina un evento por ID.
    calendar_id = "primary"
    event_id = "b628ii8c265anhc3jgqa5cj8cc"  # ⚠️ Reemplaza por un ID válido

    success = connector.delete_event(calendar_id, event_id)
    assert success, "❌ No se pudo eliminar el evento"
    print("✅ Evento eliminado correctamente.")
"""

def test_filtrar_eventos_por_titulo(connector):
    """Filtra eventos por una palabra clave en el título."""
    calendar_id = "primary"
    keyword = "Publica"
    time_min = datetime.now(timezone.utc).isoformat()

    eventos = connector.filter_events_by_title(calendar_id, keyword, time_min=time_min)
    assert isinstance(eventos, list), "❌ La función no devolvió una lista"

    for ev in eventos:
        print(f"🔎 {ev['summary']} – {ev['start'].get('dateTime', ev['start'].get('date'))}")


def test_resumen_diario(connector):
    """Genera resumen diario."""
    resumen = connector.get_summary("primary", range_type="daily", timezone="America/Lima")
    print(resumen)
    assert isinstance(resumen, str)


def test_resumen_semanal(connector):
    """Genera resumen semanal."""
    resumen = connector.get_summary("primary", range_type="weekly", timezone="America/Lima")
    print(resumen)
    assert isinstance(resumen, str)


def test_conflicto_evento(connector):
    """Verifica si hay conflicto con un nuevo horario."""
    tz = pytz.timezone("America/Lima")
    now = datetime.now(tz)
    start = now + timedelta(hours=1)
    end = start + timedelta(hours=1)

    start_iso = start.isoformat()
    end_iso = end.isoformat()

    tiene_conflicto = connector.has_conflict("primary", start_iso, end_iso)
    print("¿Conflicto?", tiene_conflicto)


def test_suggest_free_slots(connector):
    """Sugiere espacios disponibles en el día actual para un bloque de 30 min."""
    calendar_id = "primary"
    test_date = datetime.now(timezone.utc).date()

    print(f"\n📅 Buscando espacios libres para: {test_date.strftime('%Y-%m-%d')}\n")
    slots = connector.get_free_slots(calendar_id, test_date, duration_minutes=30)

    if not slots:
        print("⚠️ No hay espacios disponibles.")
    else:
        print("✅ Espacios disponibles:")
        for i, (start, end) in enumerate(slots, 1):
            print(f"{i}. {start.strftime('%H:%M')} - {end.strftime('%H:%M')}")


def test_parse_natural_event():
    """Parsea lenguaje natural a un objeto Event."""
    user_input = "Reunión con marketing el viernes a las 3pm durante 1 hora"
    event = parse_natural_language_to_event(user_input)

    if event:
        print("✅ Evento generado:")
        print(f"📌 Título: {event.title}")
        print(f"🕒 Inicio: {event.start_time}")
        print(f"🕓 Fin: {event.end_time}")
    else:
        print("❌ No se pudo generar el evento.")
        


if __name__ == "__main__":
    from app import app as flask_app

    with flask_app.app_context():
        connector_inst = connector()
        test_calendar_connection(connector_inst)
        #test_fetch_events_basic(connector_inst)
        # test_create_event(connector_inst)
        # test_actualizar_evento(connector_inst)
        # test_eliminar_evento(connector_inst)
        test_filtrar_eventos_por_titulo(connector_inst)
        test_resumen_diario(connector_inst)
        test_resumen_semanal(connector_inst)
        test_conflicto_evento(connector_inst)
        test_suggest_free_slots(connector_inst)
        test_parse_natural_event()

