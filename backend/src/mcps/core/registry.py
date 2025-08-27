#backend/src/mcps/core/registry.py
from mcps.sources.calendar.google_calendar import GoogleCalendar, GoogleCalendarConnector
from mcps.sources.files.local_file_explorer import LocalFileExplorer


class SourceRegistry:
    def __init__(self):
        self.sources = {
            "calendar": GoogleCalendarConnector(),
            "local_files": LocalFileExplorer()
            # luego: "notion": NotionClient(), "db": PostgresConnector()
        }

    def get_source(self, name: str):
        return self.sources.get(name)
