"""
⚙️ Configuration - إعدادات المشروع
جميع الإعدادات تُقرأ من Environment Variables
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # ===== Telegram Bot =====
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    OWNER_ID = int(os.getenv("OWNER_ID", "0"))

    # ===== Database =====
    DATABASE_URL = os.getenv("DATABASE_URL")

    # ===== OpenRouter AI =====
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
    AI_MODEL = os.getenv("AI_MODEL", "openai/gpt-4o-mini")

    # ===== Rate Limits =====
    DEFAULT_DAILY_LIMIT = int(os.getenv("DEFAULT_DAILY_LIMIT", "50"))
    DEFAULT_CHANNEL_LIMIT = int(os.getenv("DEFAULT_CHANNEL_LIMIT", "20"))

    # ===== Forced Subscription Channels =====
    # مثال: "-1001234567890,-1009876543210"
    FORCED_CHANNELS = [
        ch.strip() for ch in os.getenv("FORCED_CHANNELS", "").split(",")
        if ch.strip()
    ]

    # ===== Timezone =====
    DEFAULT_TIMEZONE = os.getenv("DEFAULT_TIMEZONE", "Asia/Riyadh")

    # ===== Scheduler =====
    SCHEDULER_INTERVAL_MINUTES = int(os.getenv("SCHEDULER_INTERVAL", "1"))


config = Config()