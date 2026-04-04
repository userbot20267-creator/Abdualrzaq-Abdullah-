"""
👑 Admin Forced Channel Handler
إدارة قنوات الاشتراك الإجباري من داخل البوت (للمالك فقط)
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from config import config
from database import db

# إعداد السجلات
logger = logging.getLogger(__name__)

async def add_forced_channel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    أمر إضافة قناة اشتراك إجباري جديدة
    الاستخدام: /add_forced -100123456789
    """
    user_id = update.effective_user.id

    # 1. التحقق من أن المستخدم هو صاحب البوت (Owner)
    if user_id != config.OWNER_ID:
        return await update.message.reply_text("🚫 هذا الأمر مخصص لمالك البوت فقط.")

    # 2. التأكد من إرسال ID القناة
    if not context.args:
        return await update.message.reply_text(
            "⚠️ يرجى إرسال معرف القناة مع الأمر.\n"
            "مثال: `/add_forced -100123456789`",
            parse_mode="Markdown"
        )

    channel_id = context.args[0]

    try:
        # التأكد أن المدخل رقمي (ID)
        target_id = int(channel_id)
        
        # 3. محاولة جلب معلومات القناة للتأكد أن البوت موجود فيها
        chat = await context.bot.get_chat(target_id)
        
        # 4. حفظ القناة في قاعدة البيانات
        # سنستخدم دالة حفظ الإعدادات العامة (موجودة في معظم نسخ البوت)
        # إذا لم تكن موجودة، سنقوم بتخزينها في جدول الإعدادات
        await db.update_bot_settings({"extra_forced_channel": str(target_id)})
        
        await update.message.reply_text(
            f"✅ تم إضافة القناة بنجاح!\n"
            f"📢 الاسم: <b>{chat.title}</b>\n"
            f"🆔 المعرف: <code>{target_id}</code>\n\n"
            f"سيتم الآن مطالبة المستخدمين بالاشتراك فيها بالإضافة لقنوات الـ Config.",
            parse_mode="HTML"
        )

    except ValueError:
        await update.message.reply_text("❌ خطأ: يجب أن يكون معرف القناة رقماً يبدأ بـ -100")
    except Exception as e:
        logger.error(f"Error adding forced channel: {e}")
        await update.message.reply_text(f"❌ حدث خطأ: تأكد أن البوت مشرف في القناة.\nالتفاصيل: {str(e)}")

async def list_forced_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض القنوات الإجبارية الحالية (الثابتة والمضافة)"""
    if update.effective_user.id != config.OWNER_ID: return

    static = config.FORCED_CHANNELS
    # جلب الإضافية من القاعدة
    settings = await db.get_bot_settings()
    extra = settings.get("extra_forced_channel", "لا يوجد")

    text = (
        "📋 <b>قنوات الاشتراك الإجباري الحالية:</b>\n\n"
        f"📌 من ملف Config: <code>{static}</code>\n"
        f"➕ مضافة من البوت: <code>{extra}</code>\n"
    )
    await update.message.reply_text(text, parse_mode="HTML")

def register_admin_forced_handlers(app):
    """تسجيل الأوامر في البوت"""
    app.add_handler(CommandHandler("add_forced", add_forced_channel_command))
    app.add_handler(CommandHandler("list_forced", list_forced_channels))
  
