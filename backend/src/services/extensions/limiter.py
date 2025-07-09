from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os 
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL")


limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=REDIS_URL,
    strategy="fixed-window",
    default_limits=["900 per day", "500 per hour"]
)
