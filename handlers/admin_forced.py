"""
👑 Admin Forced Channel Handler
إدارة قنوات الاشتراك الإجباري من داخل البوت (للمالك فقط)
يتم تخزين القناة الإضافية في قاعدة البيانات لضمان استمرارها بعد إعادة التشغيل.
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from config import config
from database import db

# إعداد السجلات لتتبع العمليات
logger = logging.getLogger(__name__)

async def add_forced_channel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    أمر إضافة قناة اشتراك إجباري جديدة ديناميكياً
    الاستخدام: /add_forced -100123456789
    """
    user_id = update.effective_user.id

    # 1. التحقق من أن المستخدم هو صاحب البوت (Owner)
    if user_id != config.OWNER_ID:
        return await update.message.reply_text("🚫 هذا الأمر مخصص لمالك البوت فقط.")

    # 2. التأكد من إرسال معرف القناة (ID)
    if not context.args:
        return await update.message.reply_text(
            "⚠️ يرجى إرسال معرف القناة مع الأمر.\n"
            "مثال: `/add_forced -100123456789`",
            parse_mode="Markdown"
        )

    channel_input = context.args[0]

    try:
        # التأكد أن المدخل هو معرف قناة صالح (يبدأ بـ -100)
        if not channel_input.startswith("-100"):
            return await update.message.reply_text("❌ خطأ: معرف القناة يجب أن يبدأ بـ -100")
        
        target_id = int(channel_input)
        
        # 3. محاولة جلب معلومات القناة للتأكد أن البوت مشرف فيها
        chat = await context.bot.get_chat(target_id)
        
        # 4. حفظ القناة في قاعدة البيانات
        # نستخدم دالة تحديث الإعدادات الموجودة في ملف database.py الخاص بك
        # سنقوم بتخزين معرف القناة في حقل 'template' الخاص بحساب المالك (Owner)
        await db.update_auto_publish_settings(
            user_id=config.OWNER_ID, 
            template=str(target_id)
        )
        
        await update.message.reply_text(
            f"✅ <b>تم تفعيل الاشتراك الإجباري الجديد!</b>\n\n"
            f"📢 القناة: <b>{chat.title}</b>\n"
            f"🆔 المعرف: <code>{target_id}</code>\n\n"
            f"سيتم الآن مطالبة جميع المستخدمين بالاشتراك في هذه القناة فوراً.",
            parse_mode="HTML"
        )
        
        logger.info(f"Owner {user_id} added a new dynamic forced channel: {target_id}")

    except ValueError:
        await update.message.reply_text("❌ خطأ: يجب أن يكون المعرف عبارة عن أرقام فقط.")
    except Exception as e:
        logger.error(f"Error in add_forced: {e}")
        await update.message.reply_text(
            f"❌ حدث خطأ: تأكد أن البوت موجود في القناة ومشرف فيها.\n\n"
            f"التفاصيل: <code>{str(e)}</code>",
            parse_mode="HTML"
        )

async def list_forced_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض قائمة قنوات الاشتراك الإجباري الحالية"""
    if update.effective_user.id != config.OWNER_ID:
        return

    # جلب القنوات الثابتة من ملف config
    static_channels = config.FORCED_CHANNELS if config.FORCED_CHANNELS else []
    
    # جلب القناة الديناميكية من قاعدة البيانات
    settings = await db.get_auto_publish_settings(config.OWNER_ID)
    dynamic_channel = settings.get("template")

    text = "📋 <b>قنوات الاشتراك الإجباري النشطة:</b>\n\n"
    
    if static_channels:
        text += "📌 <b>قنوات ثابتة (من الملف):</b>\n"
        for ch in static_channels:
            text += f"└ <code>{ch}</code>\n"
    
    if dynamic_channel and dynamic_channel.startswith("-100"):
        text += f"\n➕ <b>قناة مضافة (من البوت):</b>\n└ <code>{dynamic_channel}</code>\n"
    elif not static_channels:
        text += "❌ لا توجد قنوات مضافة حالياً."

    await update.message.reply_text(text, parse_mode="HTML")

def register_admin_forced_handlers(app):
    """ربط الأوامر بالتطبيق"""
    app.add_handler(CommandHandler("add_forced", add_forced_channel_command))
    app.add_handler(CommandHandler("list_forced", list_forced_channels))
        
