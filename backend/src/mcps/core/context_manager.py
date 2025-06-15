from typing import List
from datetime import datetime
from mcps.core.models import Event
from mcps.sources.calendar.google_calendar import GoogleCalendarConnector

class ContextManager:
    def __init__(self, calendar: bool = True):
        self.calendar_client = GoogleCalendarConnector() if calendar else None

    def fetch_events(self, start_date: datetime, end_date: datetime) -> List[Event]:
        """
        Devuelve eventos de calendario entre dos fechas.
        Escalable a múltiples fuentes en el futuro.
        """
        events = []
        if self.calendar_client:
            events.extend(self.calendar_client.fetch_events_by_range(start_date, end_date))
        return events

    # Futuro: agregar más fuentes
    # def fetch_files(self, ...): ...
    # def fetch_database_records(self, ...): ...
    # def get_context_summary(self): -> dict: ...
