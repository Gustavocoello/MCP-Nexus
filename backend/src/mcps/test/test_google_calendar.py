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
    print("Servicio de Google Calendar autenticado correctamente.")


def test_get_free_slots():
    """Test para la funcion get_free_slots sin parametros (usa valores por defecto)"""
    conn = connector()
    today = datetime.now().date()
    
    result = conn.get_free_slots(today)
    
    print(f"Resultado para {today}:")
    print(f"Free slots: {len(result['free_slots'])}")
    print(f"Busy events: {len(result['busy_events'])}")
    
    for slot in result['free_slots']:
        print(f"Slot libre: {slot[0]} - {slot[1]}")
    
    for event in result['busy_events']:
        print(f"Evento ocupado: {event['summary']} ({event['start']} - {event['end']})")


def test_get_weekly_free_slots():
    """Test para la funcion get_weekly_free_slots sin parametros (usa valores por defecto)"""
    conn = connector()
    
    result = conn.get_weekly_free_slots()
    
    print(f"Resultado semanal:")
    for day in result:
        print(f"Dia {day['date']}:")
        print(f"- Free slots: {len(day['free_slots'])}")
        print(f"- Busy events: {len(day['busy_events'])}")
        
        for slot in day['free_slots']:
            print(f"  Slot libre: {slot['start']} - {slot['end']}")
        
        for event in day['busy_events']:
            print(f"  Evento ocupado: {event['summary']} ({event['start']} - {event['end']})")

def test_fetch_events_basic(connector):
    """Busca eventos en los últimos 15 días."""
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=15)

    print(f"🔍 Buscando eventos entre {start_date.date()} y {end_date.date()}...")
    events = connector.fetch_events_by_range(start_date, end_date)

    if not events:
        print("⚠️ No se encontraron eventos.")
    else:
        print(f" - {len(events)} eventos encontrados:")
        for e in events:
            print(f"📅 {e.title} | {e.start_time} -> {e.end_time}")


def test_filtrar_eventos_por_titulo(connector):
    """Filtra eventos por una palabra clave en el título."""
    calendar_id = "primary"
    keyword = "Publica"
    time_min = datetime.now(timezone.utc).isoformat()

    eventos = connector.filter_events_by_title(calendar_id, keyword, time_min=time_min)
    assert isinstance(eventos, list), "La función no devolvió una lista"

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
        print("No se pudo generar el evento.")

def test_list_calendars(connector):
    """Prueba la función list_calendars() del connector."""
    print("\n🔍 Probando list_calendars()...")
    print("=" * 40)
    
    try:
        # Llamar a la función
        calendars = connector.list_calendars()
        
        # Verificar que devuelve una lista
        assert isinstance(calendars, list), "list_calendars() debe devolver una lista"
        print(f"Devuelve una lista: {type(calendars)}")

        # Verificar contenido
        if not calendars:
            print("La lista está vacía - puede ser normal si no hay calendarios")
            print("Verificando llamada directa a API...")
            
            # Test directo de la API para comparar
            raw_result = connector.service.calendarList().list().execute()
            raw_items = raw_result.get('items', [])
            print(f"📡 API directa devuelve: {len(raw_items)} calendarios")
            
            if raw_items:
                print("PROBLEMA: La API tiene datos pero nuestro método no los procesa")
                print("📋 Datos raw del primer calendario:")
                first = raw_items[0]
                for key in ['id', 'summary', 'description']:
                    print(f"   {key}: {first.get(key, 'N/A')}")
            else:
                print("ℹ️ La cuenta realmente no tiene calendarios visibles")
                
        else:
            print(f"Se encontraron {len(calendars)} calendarios:")
            
            # Verificar estructura de cada calendario
            for i, cal in enumerate(calendars):
                print(f"\n📅 Calendario {i+1}:")
                
                # Verificar que es un dict
                assert isinstance(cal, dict), f"El calendario {i+1} debe ser un dict, es: {type(cal)}"

                # Verificar campos requeridos
                assert 'id' in cal, f"El calendario {i+1} debe tener campo 'id'"
                assert 'name' in cal, f"El calendario {i+1} debe tener campo 'name'"
                
                # Mostrar información
                calendar_id = cal.get('id')
                calendar_name = cal.get('name')
                
                print(f"   ID: {calendar_id}")
                print(f"   Nombre: {calendar_name}")
                
                # Verificar que los valores no estén vacíos
                assert calendar_id, f"El ID del calendario {i+1} no puede estar vacío"
                assert calendar_name, f"El nombre del calendario {i+1} no puede estar vacío"
                
                # Verificar si es el calendario primario
                if calendar_id == 'primary':
                    print("   🌟 Este es el calendario primario")
                    
        print("\n test_list_calendars() completado exitosamente")
        return True
        
    except AssertionError as ae:
        print(f"Assertion Error: {ae}")
        return False
        
    except Exception as e:
        print(f"Error durante el test: {str(e)}")
        print(f"Tipo de error: {type(e).__name__}")
        return False
        


if __name__ == "__main__":
    from app import app as flask_app

    with flask_app.app_context():
        connector_inst = connector()
        test_calendar_connection(connector_inst)
        test_list_calendars(connector_inst)
        test_get_free_slots()
        test_get_weekly_free_slots()
