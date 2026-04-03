"""
⏰ Schedule Handler - نظام الجدولة
جدولة المنشورات بوقت محدد مع دعم المنطقة الزمنية
"""

import json
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from database import db
from utils.helpers import parse_datetime_with_tz, parse_time_only
from utils.decorators import check_banned, check_subscription

logger = logging.getLogger(__name__)


@check_banned
@check_subscription
async def schedule_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر /schedule"""
    user_id = update.effective_user.id
    user = await db.get_user(user_id)
    settings = await db.get_auto_publish_settings(user_id)

    times = settings.get("publish_times", [])
    if isinstance(times, str):
        times = json.loads(times)

    status = "✅ مفعّل" if settings.get("is_enabled") else "❌ معطّل"

    text = (
        f"⏰ <b>إعدادات الجدولة:</b>\n\n"
        f"🔄 النشر التلقائي: {status}\n"
        f"⏰ أوقات النشر: {', '.join(times) if times else 'لم تُحدد'}\n"
        f"🕐 المنطقة الزمنية: {user.get('timezone', 'Asia/Riyadh')}\n\n"
        f"📌 <b>لجدولة منشور محدد:</b>\n"
        f"اختر منشوراً من الـ Queue واضغط «جدولة»"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 تبديل النشر التلقائي", callback_data="toggle_auto_publish")],
        [InlineKeyboardButton("⏰ تعديل الأوقات", callback_data="edit_publish_times")],
        [InlineKeyboardButton("🕐 تغيير المنطقة الزمنية", callback_data="set_timezone")],
        [InlineKeyboardButton("📋 عرض Queue", callback_data="q_refresh")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
    ])

    await update.message.reply_text(text, parse_mode="HTML", reply_markup=keyboard)


async def schedule_post_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """جدولة منشور محدد"""
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("schedule_"):
        queue_id = int(data.replace("schedule_", ""))
        context.user_data["schedule_queue_id"] = queue_id
        context.user_data["awaiting"] = "schedule_time"

        await query.edit_message_text(
            f"⏰ <b>جدولة المنشور #{queue_id}</b>\n\n"
            f"أرسل الوقت بأحد الصيغ التالية:\n\n"
            f"• وقت فقط (اليوم أو غداً): <code>14:30</code>\n"
            f"• تاريخ ووقت: <code>2025-01-15 14:30</code>\n\n"
            f"أو أرسل /cancel للإلغاء",
            parse_mode="HTML"
        )


async def handle_schedule_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة إدخال وقت الجدولة"""
    if context.user_data.get("awaiting") != "schedule_time":
        return

    text = update.message.text.strip()
    user_id = update.effective_user.id

    if text == "/cancel":
        context.user_data.pop("awaiting", None)
        context.user_data.pop("schedule_queue_id", None)
        await update.message.reply_text("❌ تم الإلغاء")
        return

    queue_id = context.user_data.get("schedule_queue_id")
    if not queue_id:
        context.user_data.pop("awaiting", None)
        return

    user = await db.get_user(user_id)
    timezone = user.get("timezone", "Asia/Riyadh")

    scheduled_dt = None

    # محاولة تحليل التاريخ والوقت
    if " " in text and "-" in text:
        parts = text.split(" ", 1)
        scheduled_dt = parse_datetime_with_tz(parts[0], parts[1], timezone)
    else:
        scheduled_dt = parse_time_only(text, timezone)

    if not scheduled_dt:
        await update.message.reply_text(
            "❌ صيغة غير صحيحة.\n"
            "استخدم: <code>14:30</code> أو <code>2025-01-15 14:30</code>",
            parse_mode="HTML"
        )
        return

    # تحديث الجدولة
    async with db.pool.acquire() as conn:
        await conn.execute(
            "UPDATE queue SET scheduled_at = $1 WHERE id = $2 AND user_id = $3",
            scheduled_dt, queue_id, user_id
        )

    import pytz
    tz = pytz.timezone(timezone)
    local_time = scheduled_dt.astimezone(tz)

    await update.message.reply_text(
        f"✅ تم جدولة المنشور #{queue_id}!\n\n"
        f"⏰ سيتم النشر في: {local_time.strftime('%Y-%m-%d %H:%M')}\n"
        f"🕐 المنطقة الزمنية: {timezone}"
    )

    context.user_data.pop("awaiting", None)
    context.user_data.pop("schedule_queue_id", None)


def register_schedule_handlers(app):
    """تسجيل handlers الجدولة"""
    app.add_handler(CommandHandler("schedule", schedule_command))
    app.add_handler(CallbackQueryHandler(schedule_post_callback, pattern="^schedule_\\d+$"))