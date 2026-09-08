import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "bts_bot")

# Owner / admin telegram user IDs (comma separated in .env, e.g. OWNER_IDS=123,456)
OWNER_IDS = [int(x) for x in os.getenv("OWNER_IDS", "").split(",") if x.strip().isdigit()]

# Economy tuning
DAILY_REWARD = 200
KILL_MIN_STEAL_PCT = 0.10
KILL_MAX_STEAL_PCT = 0.35
ROB_MIN_STEAL_PCT = 0.05
ROB_MAX_STEAL_PCT = 0.20
PROTECTION_COST = 150
PROTECTION_DURATION_HOURS = 12
STARTING_BALANCE = 300

# Management module
ALL_POWERS = ["ban", "mute", "kick", "warn", "pin", "promote", "title", "res"]
MAX_WARNS = 3  # 3rd warning auto-bans

