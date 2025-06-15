from mcps.sources.calendar.google_calendar import GoogleCalendar

class SourceRegistry:
    def __init__(self):
        self.sources = {
            "calendar": GoogleCalendar()
            # luego: "notion": NotionClient(), "db": PostgresConnector()
        }

    def get_source(self, name: str):
        return self.sources.get(name)
