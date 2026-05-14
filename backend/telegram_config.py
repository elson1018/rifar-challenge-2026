import os
from dotenv import load_dotenv

load_dotenv()

# Telegram credentials (loaded from .env — never hardcoded)
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")

# Alert thresholds (in meters)
WARNING_LEVEL = 3.0   # ⚠️ Yellow — elevated risk
DANGER_LEVEL  = 4.0   # 🚨 Red   — flooding imminent

# Anti-spam: minimum minutes between repeated alerts at the same level
COOLDOWN_MINUTES = 30
