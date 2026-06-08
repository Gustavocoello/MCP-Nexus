import pytz
from datetime import datetime

TIMEZONE = pytz.timezone('America/Guayaquil')

def get_now():
    """Devuelve la hora actual de Ecuador con información de zona horaria."""
    return datetime.now(TIMEZONE)