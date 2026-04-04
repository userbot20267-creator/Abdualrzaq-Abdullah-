"""
🤖 Telegram AI Content & Auto Publishing Bot
الملف الرئيسي - النسخة المطورة (مع حماية Try-Except للإضافات)
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
    """يتم تنفيذه بعد بدء التطبيقون"""
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
    
    # إضافة أوامر المالك الجديدة لقائمة الأوامر (اختياري)
    commands.extend([
        BotCommand("add_forced", "👑 إضافة قناة إجبارية"),
        BotCommand("list_forced", "📋 عرض قنوات الاشتراك")
    ])

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

    # 1. تسجيل الـ Handlers الأساسية (النظام القديم)
    register_all_handlers(application)
    logger.info("✅ Core handlers registered")

    # 2. محاولة تسجيل الإضافات الجديدة باستخدام try (للحماية)
    try:
        from handlers.bulk_quiz import register_bulk_quiz_handlers
        register_bulk_quiz_handlers(application)
        logger.info("✅ Bulk Quiz handlers registered")
    except Exception as e:
        logger.error(f"⚠️ Failed to load Bulk Quiz: {e}")

    try:
        from handlers.instant_publish import register_instant_publish_handlers
        register_instant_publish_handlers(application)
        logger.info("✅ Instant Publish handlers registered")
    except Exception as e:
        logger.error(f"⚠️ Failed to load Instant Publish: {e}")

    try:
        from handlers.admin_forced import register_admin_forced_handlers
        register_admin_forced_handlers(application)
        logger.info("✅ Admin Forced handlers registered")
    except Exception as e:
        logger.error(f"⚠️ Failed to load Admin Forced: {e}")

    # تشغيل البوت
    logger.info("🚀 Starting bot...")
    application.run_polling(
        allowed_updates=["message", "callback_query", "chat_member"],
        drop_pending_updates=True
    )


if __name__ == "__main__":
    main()
    
