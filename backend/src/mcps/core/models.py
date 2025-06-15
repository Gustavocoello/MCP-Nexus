from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List


@dataclass
class Event:
    title: str
    description: Optional[str]
    start_time: datetime
    end_time: datetime
    location: Optional[str] = None
    attendees: Optional[List[str]] = None
    source: str = "google_calendar"
    id: Optional[str] = None  # Solo una vez, y al final
