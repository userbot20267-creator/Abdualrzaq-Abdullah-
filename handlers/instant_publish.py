"""
🚀 Handler: Instant Publish
هذا الملف يستجيب لزر '⚡ نشر فوري' من القائمة الرئيسية.
يقوم بجلب الإعدادات المسبقة والنشر فوراً باستخدام خدمة Publisher.
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters
from database import db
from services.publisher import Publisher
from utils.decorators import check_banned, check_subscription, rate_limit_check

# إعداد السجلات
logger = logging.getLogger(__name__)

@check_banned
@check_subscription
@rate_limit_check
async def handle_instant_publish_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    يتم استدعاء هذه الدالة عند الضغط على زر '⚡ نشر فوري'
    """
    user_id = update.effective_user.id
    message = update.effective_message

    # 1. جلب إعدادات المستخدم والقنوات المرتبطة به
    # نستخدم الدالات الموجودة في ملف database.py الخاص بك
    settings = await db.get_auto_publish_settings(user_id)
    channels = await db.get_user_channels(user_id)

    if not channels:
        return await message.reply_text(
            "📢 لم تقم بإضافة أي قنوات بعد!\n"
            "استخدم زر '📡 قنواتي' لإضافة قناة أولاً."
        )

    # 2. تحديد عدد المنشورات المطلوب نشرها (من إعدادات المستخدم)
    # الافتراضي هو منشور واحد إذا لم يحدد المستخدم عدداً في الإعدادات
    count_to_publish = settings.get('posts_per_day', 1) if settings else 1

    # 3. سحب العناصر المطلوبة من الطابور (Queue)
    queue_items = await db.get_next_in_queue(user_id, count=count_to_publish)

    if not queue_items:
        return await message.reply_text(
            "📭 الطابور (Queue) فارغ حالياً.\n"
            "قم بإضافة محتوى أولاً ليتم نشره."
        )

    # 4. بدء عملية النشر التلقائي
    await message.reply_text(f"⚡ جاري تنفيذ النشر الفوري لـ {len(queue_items)} منشورات في جميع قنواتك...")

    # إنشاء كائن الناشر باستخدام البوت الحالي
    publisher = Publisher(context.bot)
    
    success_log = 0
    fail_log = 0

    for item in queue_items:
        try:
            # استدعاء دالة النشر الأصلية في مشروعك
            # دالة publish_item في ملفك تقوم تلقائياً بـ:
            # - النشر في القنوات
            # - تحديث حالة قاعدة البيانات
            # - تسجيل السجلات (Logs)
            results = await publisher.publish_item(item)
            
            success_log += len(results.get("success", []))
            fail_log += len(results.get("failed", []))
            
        except Exception as e:
            logger.error(f"Error in instant publish loop: {e}")
            fail_log += 1

    # 5. إرسال تقرير موجز بالنتائج
    report = (
        f"🏁 <b>اكتملت عملية النشر الفوري</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"✅ نجاح النشر: `{success_log}`\n"
        f"❌ فشل النشر: `{fail_log}`\n\n"
        f"ℹ️ <i>تم استخدام إعداداتك المسبقة لعدد المنشورات والقنوات.</i>"
    )
    
    await message.reply_text(report, parse_mode="HTML")

def register_instant_publish_handlers(app):
    """
    تسجيل الهاندلر في تطبيق البوت.
    يتم تفعيله فقط عندما يكون نص الرسالة مطابقاً تماماً لزر '⚡ نشر فوري'
    """
    app.add_handler(MessageHandler(
        filters.Text("⚡ نشر فوري") & filters.ChatType.PRIVATE, 
        handle_instant_publish_click
    ))
          
