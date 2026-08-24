import os
from dotenv import load_dotenv
load_dotenv()

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
BOT_NAME = os.getenv("BOT_NAME", "حارس")
BOT_CHANNEL = os.getenv("BOT_CHANNEL", "")
DEV_GROUP_ID = int(os.getenv("DEV_GROUP_ID", "0") or 0)

PREFIXES = ("/", "!", "#")
