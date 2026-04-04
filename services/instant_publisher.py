import asyncio
from datetime import datetime

# 🔹 استيراد من النظام الحالي (لا نعدلها)
from services.publisher import publish_content
from utils.subscription_wrapper import check_subscription_wrapper
from utils.rate_limiter import check_rate_limit

# 🔹 هذه سنربطها مع DB لاحقاً (أو موجودة عندك)
# عدلها حسب مشروعك
from database import get_user_channels, get_user_post_limit, get_user_queue_posts


async def instant_publish(user_id, bot):
    """
    ⚡ تنفيذ النشر الفوري باستخدام إعدادات المستخدم
    """

    results = {
        "success": [],
        "failed": [],
        "total": 0
    }

    try:
        # =========================================================
        # 1️⃣ التحقق من الاشتراك
        # =========================================================
        is_subscribed = await check_subscription_wrapper(user_id, bot)

        if not is_subscribed:
            return {"error": "❌ يجب الاشتراك في القنوات الإجبارية أولاً"}

        # =========================================================
        # 2️⃣ جلب إعدادات المستخدم
        # =========================================================
        channels = await get_user_channels(user_id)
        post_limit = await get_user_post_limit(user_id)

        if not channels:
            return {"error": "⚠️ لم تقم بإضافة قنوات للنشر"}

        if not post_limit:
            return {"error": "⚠️ لم يتم تحديد عدد المنشورات"}

        # =========================================================
        # 3️⃣ التحقق من الحد اليومي
        # =========================================================
        allowed = await check_rate_limit(user_id, post_limit)

        if not allowed:
            return {"error": "🚫 تجاوزت الحد اليومي للنشر"}

        # =========================================================
        # 4️⃣ جلب المحتوى من Queue
        # =========================================================
        posts = await get_user_queue_posts(user_id, limit=post_limit)

        if not posts:
            return {"error": "📭 لا يوجد محتوى في Queue"}

        # =========================================================
        # 5️⃣ النشر
        # =========================================================
        for post in posts:

            for channel in channels:
                try:
                    # نشر باستخدام publisher (يدعم نص/صورة/فيديو)
                    await publish_content(bot, channel, post)

                    results["success"].append(channel)
                    results["total"] += 1

                    await asyncio.sleep(0.7)  # حماية من الحظر

                except Exception as e:
                    results["failed"].append({
                        "channel": channel,
                        "error": str(e)
                    })

        # =========================================================
        # 6️⃣ إزالة المنشورات من Queue بعد النشر
        # =========================================================
        try:
            from database import delete_post_from_queue

            for post in posts:
                await delete_post_from_queue(post["id"])

        except Exception as e:
            print(f"[WARNING] Queue cleanup failed: {e}")

        return results

    except Exception as e:
        print(f"[CRITICAL] instant_publish: {e}")
        return {"error": "❌ حدث خطأ داخلي أثناء النشر"}
