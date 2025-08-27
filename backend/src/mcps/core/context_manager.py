#backend/src/mcps/core/context_manager.py
import os
from typing import List
from datetime import datetime
from src.mcps.core.models import Event
from src.mcps.sources.calendar.google_calendar import GoogleCalendarConnector

class ContextManager:
    def __init__(self, user_id: str = None, calendar: bool = True):
        if calendar:
            if not user_id:
                raise ValueError("Debe proporcionar un user_id para el calendario.")
            self.calendar_client = GoogleCalendarConnector(user_id)
        else:
            self.calendar_client = None
        self.user_context = {}

    def fetch_events(self, start_date: datetime, end_date: datetime) -> List[Event]:
        """
        Obtiene eventos del calendario en el rango especificado.
        """
        if not self.calendar_client:
            return []
        return self.calendar_client.fetch_events_by_range(start_date, end_date)

    def create_event(self, event: Event) -> dict:
        """
        Crea un evento en el calendario.
        """
        return self.calendar_client.create_event(event)

    def update_event(self, event_id: str, updates: dict) -> dict:
        """
        Actualiza un evento en el calendario.
        """
        return self.calendar_client.update_event(event_id, updates)

    def delete_event(self, event_id: str) -> bool:
        """
        Elimina un evento del calendario.
        """
        return self.calendar_client.delete_event(event_id)

    def get_conflicts(self, start: datetime, end: datetime) -> List[Event]:
        """
        Obtiene eventos que se superponen con el rango dado.
        """
        return self.calendar_client.get_conflicting_events(start, end)

    def parse_natural_input(self, text: str) -> Event:
        """
        Utiliza el cliente de calendario para interpretar
        """
        return self.calendar_client.parse_natural_language(text)

    def get_free_slots(self, start: datetime, end: datetime, duration_minutes: int) -> List[tuple]:
        """
        Obtiene los espacios libres en el calendario.
        """
        return self.calendar_client.get_available_slots(start, end, duration_minutes)
    
    def get_daily_summary(self, calendar_id: str = None, timezone: str = "UTC") -> str:
        """
        Obtiene un resumen diario de eventos. Si no se especifica calendar_id, trae todos los calendarios.
        """
        return self.calendar_client.get_summary(calendar_id=calendar_id, range_type="daily", timezone=timezone)

    def get_weekly_summary(self, calendar_id: str = None, timezone: str = "UTC") -> str:
        """
        Obtiene un resumen semanal de eventos. Si no se especifica calendar_id, trae todos los calendarios.
        """
        return self.calendar_client.get_summary(calendar_id=calendar_id, range_type="weekly", timezone=timezone)

    def list_calendars(self) -> List[str]:
        """
        Lista los calendarios disponibles.
        """
        return self.calendar_client.list_calendars()
    
    def set_working_directory(self, user_id: str, path: str):
        # Validaciones  - mcp prompt
        if not os.path.exists(path):
            raise ValueError(f"Ruta inválida: {path}")
        self.user_contexts[user_id] = {"working_dir": path}

    def get_working_directory(self, user_id: str) -> str:
        return self.user_contexts.get(user_id, {}).get("working_dir", "")
    

    # Futuro: agregar más fuentes
    # def fetch_files(self, ...): ...
    # def fetch_database_records(self, ...): ...
    # def get_context_summary(self): -> dict: ...
