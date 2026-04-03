"""
🤖 Telegram AI Content & Auto Publishing Bot
الملف الرئيسي - نقطة البداية
"""

import logging
import asyncio
from telegram.ext import Application
from config import config
from database import db
from handlers import register_all_handlers
from services.scheduler_service import SchedulerService

# ===== إعداد الـ Logging =====
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# تقليل logs المكتبات الخارجية
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("apscheduler").setLevel(logging.WARNING)


async def post_init(application: Application):
    """يتم تنفيذه بعد بدء التطبيق"""
    # الاتصال بقاعدة البيانات
    await db.connect()
    logger.info("✅ Database connected")

    # تشغيل الـ Scheduler
    scheduler = SchedulerService(application.bot)
    scheduler.start()
    application.bot_data["scheduler"] = scheduler
    logger.info("✅ Scheduler started")

    # تعيين أوامر البوت
    from telegram import BotCommand
    commands = [
        BotCommand("start", "🏠 البداية"),
        BotCommand("help", "📖 المساعدة"),
        BotCommand("add_channel", "📡 إضافة قناة"),
        BotCommand("remove_channel", "❌ حذف قناة"),
        BotCommand("list_channels", "📋 عرض القنوات"),
        BotCommand("generate", "🤖 توليد منشور AI"),
        BotCommand("rewrite", "🔄 إعادة صياغة"),
        BotCommand("summarize", "📋 تلخيص"),
        BotCommand("add_quiz", "❓ إضافة اختبار"),
        BotCommand("add_poll", "📊 إضافة استطلاع"),
        BotCommand("queue", "📋 عرض Queue"),
        BotCommand("post_now", "⚡ نشر فوري"),
        BotCommand("schedule", "⏰ الجدولة"),
        BotCommand("stats", "📊 إحصائياتي"),
        BotCommand("settings", "⚙️ الإعدادات"),
    ]
    await application.bot.set_my_commands(commands)
    logger.info("✅ Bot commands set")

    bot_info = await application.bot.get_me()
    logger.info(f"🤖 Bot started: @{bot_info.username}")


async def post_shutdown(application: Application):
    """يتم تنفيذه عند إيقاف التطبيق"""
    scheduler = application.bot_data.get("scheduler")
    if scheduler:
        scheduler.stop()
    await db.disconnect()
    logger.info("👋 Bot stopped gracefully")


def main():
    """الدالة الرئيسية"""
    if not config.BOT_TOKEN:
        logger.error("❌ BOT_TOKEN is not set!")
        return

    if not config.DATABASE_URL:
        logger.error("❌ DATABASE_URL is not set!")
        return

    # إنشاء التطبيق
    application = (
        Application.builder()
        .token(config.BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    # تسجيل جميع الـ Handlers
    register_all_handlers(application)
    logger.info("✅ All handlers registered")

    # تشغيل البوت
    logger.info("🚀 Starting bot...")
    application.run_polling(
        allowed_updates=[
            "message", "callback_query", "chat_member"
        ],
        drop_pending_updates=True
    )


if __name__ == "__main__":
    main()