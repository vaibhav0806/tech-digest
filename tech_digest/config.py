import os
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATABASE_PATH = os.environ.get("DATABASE_PATH", str(_PROJECT_ROOT / "data" / "products.db"))
SCRAPE_SECRET = os.environ.get("SCRAPE_SECRET", "")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHANNEL_ID", os.environ.get("TELEGRAM_CHAT_ID", ""))
SESSION_COOKIE = "session_id"
SESSION_MAX_AGE = 365 * 24 * 60 * 60  # 1 year
