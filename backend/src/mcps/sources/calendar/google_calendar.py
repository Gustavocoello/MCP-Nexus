import os
import sys
from dotenv import load_dotenv
import pytz
from pathlib import Path
from typing import Optional, Union, List, Tuple
from dateutil.parser import parse as parse_dt
from datetime import datetime, timezone, timedelta

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.exceptions import RefreshError
from googleapiclient.discovery import build
from sqlalchemy import all_

try: # Para el app.py
    from src.mcps.core.models import Event
except ImportError: # Para el MCP inspector
    from mcps.core.models import Event
    
# --- Fix Paths ---
current_dir = Path(__file__).resolve().parent
backend_dir = current_dir.parent.parent.parent.parent
sys.path.insert(0, str(backend_dir))

from src.services.auth.token_crypto import decrypt_token, encrypt_token
from src.database.models import UserToken
from extensions import db

load_dotenv()
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

# Ruta al archivo de credenciales y token
CREDENTIALS_PATH = Path("D:/Personal/Documentos/Work/Python/AI agent/AI/mcp-nexus/mcp-scratch/backend/src/config/credentials/credentials_google_calendar.json")
# Scopes necesarios para acceder al calendario
SCOPES = ["https://www.googleapis.com/auth/calendar"]
SCOPES_READONLY = ["https://www.googleapis.com/auth/calendar.readonly"]
SCOPES_WRITE = ["https://www.googleapis.com/auth/calendar.events"]

load_dotenv()

# Seguridad para evitar que el LLM selecione fechas muy futuras o pasadas
def validate_range(start: datetime, end: datetime):
    if start > end:
        raise ValueError("La fecha de inicio no puede ser posterior a la de fin.")
    if (end - start).days > 670: # Rango máximo de 2 año
            raise ValueError("El rango de fechas no puede ser mayor a 1 año.")

def ensure_aware(dt):
    if isinstance(dt, str):
        dt = parse_dt(dt)  # Convierte str a datetime con tz si es posible
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

class GoogleCalendarConnector:
    def __init__(self, user_id=None):
        if not user_id:
            raise ValueError("Falta el user_id (obligatorio en producción)")
        self.user_id = user_id
        self.creds = None

    def authenticate(self):
        """
        Autenticación OAuth2 con Google Calendar API.
        Guarda/recupera token para evitar autenticación repetida.
        Elimnar el tokens si se quiere forzar una nueva autenticación.
        """
        token_entry = UserToken.query.filter_by(user_id=self.user_id, provider="google_calendar").first()
        if not token_entry:
            raise Exception("🔐 No se encontró token para este usuario. ¿Autenticó con Google?")

        access_token = decrypt_token(token_entry.access_token)
        refresh_token = decrypt_token(token_entry.refresh_token) if token_entry.refresh_token else None

        # Construye el objeto de credenciales
        creds = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=os.getenv("GOOGLE_CLIENT_ID"),
            client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
            scopes=[
                "https://www.googleapis.com/auth/calendar",
                "https://www.googleapis.com/auth/calendar.readonly",
                "openid", "email", "profile"
            ]
        )

        # Si está expirado pero tiene refresh_token, refresca
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())

            # 🛡️ Opcional: actualiza el nuevo access_token en base de datos
            token_entry.access_token = encrypt_token(creds.token)
            token_entry.expires_at = datetime.utcnow() + creds.expiry if creds.expiry else None
            db.session.commit()

        self.creds = creds
        self.service = build("calendar", "v3", credentials=self.creds)
        return self.service
    # ============= OBTENCIÓN DE EVENTOS POR RANGO FECHAS ===============
    def get_events_by_range(self, calendar_id: str, start: Union[str, datetime], end: Union[str, datetime]):
        if isinstance(start, str):
            start = datetime.fromisoformat(start)
        if isinstance(end, str):
            end = datetime.fromisoformat(end)

        start_rfc3339 = start.isoformat() + "Z"
        end_rfc3339 = end.isoformat() + "Z"

        events_result = (
            self.service.events()
            .list(
                calendarId=calendar_id,
                timeMin=start_rfc3339,
                timeMax=end_rfc3339,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        events = events_result.get("items", [])
        return [self._to_event_object(e) for e in events]
    
    from datetime import datetime
    
    # ============= OBTENCIÓN DE EVENTOS =============
    def fetch_events_by_range(self, start_date=None, end_date=None, calendar_ids=None):
        """
        Devuelve eventos de uno o varios calendarios en un rango de fechas arbitrario.
        """
        if not start_date:
            start_date = datetime.datetime.utcnow()
        if not end_date:
            end_date = start_date + datetime.timedelta(days=30)

        time_min = start_date.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        time_max = end_date.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


        events_total = []

        # Obtener la lista de calendarios a consultar
        if calendar_ids is None:
            calendars_result = self.service.calendarList().list().execute()
            calendar_ids = [c["id"] for c in calendars_result.get("items", [])]

        for cal_id in calendar_ids:
            try:
                events_result = (
                    self.service.events()
                    .list(
                        calendarId=cal_id,
                        timeMin=time_min,
                        timeMax=time_max,
                        singleEvents=True,
                        orderBy="startTime",
                    )
                    .execute()
                )
                for event in events_result.get("items", []):
                    event_obj = self._to_event_object(event)
                    event_obj.source = cal_id
                    events_total.append(event_obj)
            except Exception as e:
                print(f"⚠️ Error al obtener eventos de '{cal_id}': {e}")

        return events_total
    
    # ============= CONVERSIÓN DE EVENTOS =============
    def _to_event_object(self, event_data) -> Event:
        raw_start = event_data.get("start", {}).get("dateTime") \
                    or event_data.get("start", {}).get("date")
        raw_end   = event_data.get("end",   {}).get("dateTime") \
                    or event_data.get("end",   {}).get("date")

        # parse devuelve un datetime timezone-aware si la cadena tiene offset
        start_dt = parse_dt(raw_start)
        end_dt   = parse_dt(raw_end)

        return Event(
            id=event_data.get("id"),
            title=event_data.get("summary", "Sin título"),
            description=event_data.get("description", ""),
            location=event_data.get("location", ""),
            start_time=start_dt,
            end_time=end_dt,
            source="google_calendar"
        )
    
    # ============= CREACIÓN DE EVENTOS =============
    def create_event(self, calendar_id: str, event: Event) -> Union[Event, dict]:
        """
        Crea un evento en el calendario especificado.

        Args:
            calendar_id (str): ID del calendario destino.
            event (Event): Objeto Event con título, descripción, fechas, etc.

        Returns:
            Event | dict: Objeto Event con los datos confirmados por Google,
                        o un dict con el error en caso de fallo.
        """
        start_time_iso = event.start_time.isoformat()
        end_time_iso = event.end_time.isoformat()

        
        if self.has_conflict(calendar_id, start_time_iso, end_time_iso):
            return {"error": "Conflicto de horarios: ya existe un evento en este rango."}
        try:
            event_body = {
                "summary": event.title,
                "description": event.description,
                "start": {
                    "dateTime": event.start_time.isoformat(),
                    "timeZone": "UTC"
                },
                "end": {
                    "dateTime": event.end_time.isoformat(),
                    "timeZone": "UTC"
                },
            }

            created_event = self.service.events().insert(
                calendarId=calendar_id,
                body=event_body
            ).execute()

            return Event(
                id=created_event.get("id"),
                title=created_event.get("summary", event.title),
                description=created_event.get("description", event.description),
                start_time=event.start_time,
                end_time=event.end_time,
                location=created_event.get("location", event.location),
                attendees=[a["email"] for a in created_event.get("attendees", [])] if created_event.get("attendees") else None,
                source="google_calendar"
            )

        except Exception as error:
            print(f"Error al crear el evento: {error}")
            return {"error": str(error)}
        
        
    # ============= ACTUALIZACIÓN DE EVENTOS =============
    def update_event(self, calendar_id: str, event_id: str, updated_fields: dict) -> Union[Event, dict]:
        """
        Actualiza campos específicos de un evento existente.

        Args:
            calendar_id (str): ID del calendario donde está el evento.
            event_id (str): ID del evento a actualizar.
            updated_fields (dict): Diccionario con campos a modificar.

        Returns:
            Event | dict: Evento actualizado o dict con error.
        """
        try:
            # Obtener el evento actual
            existing_event = self.service.events().get(calendarId=calendar_id, eventId=event_id).execute()

            # Actualizar los campos deseados
            for key, value in updated_fields.items():
                if key in ["start", "end"]:
                    existing_event[key] = {
                        "dateTime": value.isoformat(),
                        "timeZone": "UTC"
                    }
                else:
                    existing_event[key] = value

            # Enviar actualización
            updated = self.service.events().update(
                calendarId=calendar_id,
                eventId=event_id,
                body=existing_event
            ).execute()

            return self._to_event_object(updated)

        except Exception as e:
            print(f"❌ Error al actualizar el evento: {e}")
            return {"error": str(e)}


    # ============= BORRADO DE EVENTOS =============
    def delete_event(self, calendar_id: str, event_id: str) -> bool:
        """
        Elimina un evento del calendario.

        Args:
            calendar_id (str): ID del calendario.
            event_id (str): ID del evento a eliminar.

        Returns:
            bool: True si se eliminó correctamente, False si falló.
        """
        try:
            self.service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
            print(f"🗑️ Evento eliminado: {event_id}")
            return True
        except Exception as e:
            print(f"❌ Error al eliminar el evento: {e}")
            return False


    # ============= FILTRAR POR TITULO Y FECHA =============
    def filter_events_by_title(
        self,
        calendar_id: str,
        keyword: str,
        time_min: str = None,
        time_max: str = None,
        max_results: int = 100
    ) -> list:
        """
        Filtra eventos que contienen una palabra clave en el título.

        Args:
            calendar_id (str): ID del calendario.
            keyword (str): Palabra clave a buscar en el título.
            time_min (str): Fecha mínima en formato RFC3339 (opcional).
            time_max (str): Fecha máxima en formato RFC3339 (opcional).
            max_results (int): Máximo de resultados a retornar.

        Returns:
            list: Lista de eventos que coinciden.
        """
        try:
            query = {
                "calendarId": calendar_id,
                "maxResults": max_results,
                "singleEvents": True,
                "orderBy": "startTime",
            }
            if time_min:
                query["timeMin"] = time_min
            if time_max:
                query["timeMax"] = time_max

            results = self.service.events().list(**query).execute()
            events = results.get("items", [])
            
            filtered = [
                event for event in events
                if keyword.lower() in event.get("summary", "").lower()
            ]
            return filtered
        except Exception as e:
            print(f"❌ Error al filtrar eventos: {e}")
            return []
        
    # ============= RESUMEN DE EVENTOS =============
    def list_calendars(self) -> List[dict]:
        if not hasattr(self, "service"):
            self.authenticate()
        try:
            calendars = self.service.calendarList().list().execute()
            return [
                {"id": c["id"], "name": c.get("summary", "Sin nombre")}
                for c in calendars.get("items", [])
            ]
        except Exception as e:
            print(f"Error al listar calendarios: {e}")
            return []

    def get_summary(self, calendar_id=None, range_type: str = "daily", timezone: str = "UTC") -> str:
        """
        Genera un resumen de eventos para hoy o la semana.

        Args:
            calendar_id (str): ID del calendario.
            range_type (str): 'daily' o 'weekly'.
            timezone (str): Zona horaria (ej. 'America/Lima').

        Returns:
            str: Resumen textual de los eventos.
        """
        if not hasattr(self, "service"):
            self.authenticate()
        try:
            tz = pytz.timezone(timezone)
            now = datetime.now(tz)
            
            if range_type == "daily":
                start = tz.localize(datetime(now.year, now.month, now.day))
                end = start + timedelta(days=1)
                title = f"🗓️ Resumen de eventos para hoy ({start.strftime('%d/%m/%Y')}):"
            elif range_type == "weekly":
                start = tz.localize(datetime(now.year, now.month, now.day)) - timedelta(days=now.weekday())
                end = start + timedelta(days=7)
                title = f"📅 Resumen de eventos para la semana ({start.strftime('%d/%m')} - {end.strftime('%d/%m')}):"
            else:
                return "⚠️ Tipo de resumen no válido. Usa 'daily' o 'weekly'."
            
            if calendar_id is None or calendar_id == "":
                calendar_ids = [c["id"] for c in self.list_calendars()]
                if not calendar_ids:
                    return f"{title}\n\n⚠️ No se encontraron calendarios disponibles."
            else:
                calendar_ids = [calendar_id]
            
            all_summaries = []
            for cid in calendar_ids:
                try:
                    time_min = start.isoformat()
                    time_max = end.isoformat()

                    events = self.service.events().list(
                        calendarId=cid,
                        timeMin=time_min,
                        timeMax=time_max,
                        singleEvents=True,
                        orderBy="startTime"
                    ).execute().get("items", [])

                    if not events:
                        all_summaries.append(f"📅 [{cid}] Sin eventos.")
                        continue
                    
                    lines = []
                    for ev in events:
                        start_time = ev["start"].get("dateTime", ev["start"].get("date"))
                        parsed_start = datetime.fromisoformat(start_time).astimezone(tz)
                        hora = parsed_start.strftime('%H:%M')
                        fecha = parsed_start.strftime('%d/%m/%Y')
                        summary = ev.get("summary", "Sin título")
                        location = ev.get("location", "")
                        loc_str = f" en {location}" if location else ""
                        lines.append(f"• {fecha} a las {hora}: {summary}{loc_str}")
                        
                    summary = f"📅 [{cid}] {range_type.capitalize()} Summary:\n" + "\n".join(lines)
                        
                    all_summaries.append(summary)
                except Exception as e:
                    all_summaries.append(f"⚠️ Error al obtener eventos del calendario '{cid}': {e}")

            return title + "\n\n" + "\n".join(all_summaries)

        except Exception as e:
            return f"Error al generar el resumen: {e}"
    
    # ============= DETECCION DE CONFLICTOS =============
    def has_conflict(self, calendar_id: str, start_time: str, end_time: str) -> bool:
        """
        Verifica si hay conflictos con eventos existentes en el rango dado.

        Args:
            calendar_id (str): ID del calendario.
            start_time (str): Fecha/hora de inicio en formato RFC3339.
            end_time (str): Fecha/hora de fin en formato RFC3339.

        Returns:
            bool: True si hay conflicto, False si el rango está libre.
        """
        try:
            events_result = self.service.events().list(
                calendarId=calendar_id,
                timeMin=start_time,
                timeMax=end_time,
                singleEvents=True,
                orderBy="startTime"
            ).execute()

            events = events_result.get("items", [])

            return len(events) > 0

        except Exception as e:
            print(f"Error al verificar conflicto: {e}")
            return False
    
    # ============= ESPACIO DISPONIBLE ENTRE EVENTOS =============
    def get_free_slots(self, calendar_id: str, date: datetime.date, duration_minutes: int = 60) -> list:
        """
        Devuelve slots libres para un día específico, solo hoy y futuro.
        """
        now_utc       = datetime.now(timezone.utc)
        today_utc     = now_utc.date()

        # Fechas pasadas => vaciar
        if date < today_utc:
            print("⚠️ El día solicitado ya pasó.")
            return []

        # Si es hoy, arrancás desde ahora; si es futuro, desde medianoche UTC
        if date == today_utc:
            current = now_utc
        else:
            current = datetime.combine(date, datetime.min.time()).replace(tzinfo=timezone.utc)

        end_of_day = datetime.combine(date, datetime.max.time()).replace(tzinfo=timezone.utc)

        events = sorted(
            self.fetch_events_by_range(current, end_of_day),
            key=lambda e: e.start_time
        )

        free_slots = []

        for event in events:
            event_start = ensure_aware(event.start_time)
            # Si cabe un slot antes del inicio del evento
            if current + timedelta(minutes=duration_minutes) <= event_start:
                free_slots.append((current, event_start))
            # Avanzamos al final del evento para seguir buscando
            current = max(current, ensure_aware(event.end_time))

        # Slot entre el último evento y el fin del día
        if current + timedelta(minutes=duration_minutes) <= end_of_day:
            free_slots.append((current, end_of_day))

        return free_slots
