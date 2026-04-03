"""
⏰ Scheduler Service - خدمة الجدولة والنشر التلقائي
تستخدم APScheduler لتشغيل المهام في أوقات محددة
"""

import logging
from datetime import datetime, timedelta
import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from telegram import Bot
from database import db
from services.publisher import Publisher
from config import config

logger = logging.getLogger(__name__)


class SchedulerService:
    """خدمة الجدولة الرئيسية"""

    def __init__(self, bot: Bot):
        self.bot = bot
        self.publisher = Publisher(bot)
        self.scheduler = AsyncIOScheduler(timezone=pytz.utc)

    def start(self):
        """تشغيل الـ Scheduler"""
        # فحص المنشورات المجدولة كل دقيقة
        self.scheduler.add_job(
            self._check_scheduled_posts,
            IntervalTrigger(minutes=config.SCHEDULER_INTERVAL_MINUTES),
            id="check_scheduled",
            replace_existing=True
        )

        # فحص النشر التلقائي كل دقيقة
        self.scheduler.add_job(
            self._check_auto_publish,
            IntervalTrigger(minutes=1),
            id="check_auto_publish",
            replace_existing=True
        )

        # إعادة تعيين العداد اليومي عند منتصف الليل
        self.scheduler.add_job(
            self._reset_daily_counters,
            CronTrigger(hour=0, minute=0, timezone=pytz.utc),
            id="reset_counters",
            replace_existing=True
        )

        self.scheduler.start()
        logger.info("⏰ Scheduler started successfully")

    def stop(self):
        """إيقاف الـ Scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("⏰ Scheduler stopped")

    async def _check_scheduled_posts(self):
        """فحص ونشر المنشورات المجدولة"""
        try:
            now = datetime.now(pytz.utc)
            posts = await db.get_scheduled_posts(now)

            for post in posts:
                if post.get("is_banned"):
                    continue

                # التحقق من الحد اليومي
                count = await db.get_user_post_count_today(post["user_id"])
                user = await db.get_user(post["user_id"])
                if user and count >= user["daily_limit"]:
                    logger.info(
                        f"User {post['user_id']} reached daily limit, "
                        f"skipping post #{post['id']}"
                    )
                    continue

                results = await self.publisher.publish_item(post)

                # إشعار المستخدم
                success_count = len(results["success"])
                fail_count = len(results["failed"])

                if success_count > 0:
                    try:
                        await self.bot.send_message(
                            chat_id=post["user_id"],
                            text=f"✅ تم نشر المنشور #{post['id']} بنجاح!\n"
                                 f"📡 القنوات: {success_count} ناجح"
                                 f"{f' | {fail_count} فاشل' if fail_count > 0 else ''}"
                        )
                    except Exception:
                        pass

        except Exception as e:
            logger.error(f"Scheduler check error: {e}")

    async def _check_auto_publish(self):
        """فحص وتنفيذ النشر التلقائي"""
        try:
            users = await db.get_all_users()
            now = datetime.now(pytz.utc)

            for user in users:
                if user["is_banned"]:
                    continue

                settings = await db.get_auto_publish_settings(user["telegram_id"])
                if not settings or not settings.get("is_enabled"):
                    continue

                publish_times = settings.get("publish_times", [])
                if isinstance(publish_times, str):
                    import json
                    publish_times = json.loads(publish_times)

                user_tz = pytz.timezone(user.get("timezone", "Asia/Riyadh"))
                user_now = now.astimezone(user_tz)
                current_time = user_now.strftime("%H:%M")

                if current_time in publish_times:
                    # التحقق من الحد
                    count = await db.get_user_post_count_today(user["telegram_id"])
                    if count >= user["daily_limit"]:
                        continue

                    # جلب منشور من الـ Queue
                    items = await db.get_next_in_queue(user["telegram_id"], 1)
                    if items:
                        await self.publisher.publish_item(items[0])
                        try:
                            await self.bot.send_message(
                                chat_id=user["telegram_id"],
                                text=f"🤖 تم النشر التلقائي للمنشور #{items[0]['id']}"
                            )
                        except Exception:
                            pass

        except Exception as e:
            logger.error(f"Auto publish check error: {e}")

    async def _reset_daily_counters(self):
        """إعادة تعيين العدادات اليومية"""
        try:
            async with db.pool.acquire() as conn:
                await conn.execute(
                    "UPDATE users SET posts_today = 0, last_post_date = CURRENT_DATE"
                )
            logger.info("🔄 Daily counters reset")
        except Exception as e:
            logger.error(f"Reset counters error: {e}")
