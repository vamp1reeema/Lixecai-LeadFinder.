import json
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "state.sqlite"

def required_secret(name):
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Не задан GitHub Secret: {name}")
    return value

with (BASE_DIR / "settings.json").open(encoding="utf-8") as f:
    SETTINGS = json.load(f)

BOT_TOKEN = required_secret("BOT_TOKEN")
BOT_CHAT_ID = required_secret("BOT_CHAT_ID")
