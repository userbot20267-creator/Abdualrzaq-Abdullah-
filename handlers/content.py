"""
📝 Content Handler - إدارة المحتوى
يدعم: نص، صور، فيديو، صوت، ملفات
يخزن كل المحتوى في Queue لحين النشر
"""

import json
import logging
from telegram import Update
from telegram.ext import (
    ContextTypes, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters
)
from database import db
from utils.helpers import generate_content_hash
from utils.keyboards import (
    post_action_keyboard, channel_select_keyboard
)
from utils.decorators import check_banned, check_subscription

logger = logging.getLogger(__name__)


@check_banned
@check_subscription
async def handle_text_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة محتوى نصي"""
    # تجاهل الأوامر والأزرار
    if update.message.text.startswith("/"):
        return
    # تجاهل أزرار القائمة
    menu_buttons = [
        "📝 إنشاء محتوى", "🤖 الذكاء الاصطناعي", "📋 Queue",
        "📡 قنواتي", "⏰ الجدولة", "📊 إحصائياتي", "⚡ نشر فوري", "⚙️ الإعدادات"
    ]
    if update.message.text in menu_buttons:
        return

    # تحقق من حالة الانتظار
    awaiting = context.user_data.get("awaiting")
    if awaiting:
        if awaiting == "add_channel":
            from handlers.channels import handle_channel_input
            await handle_channel_input(update, context)
            return
        elif awaiting in ("timezone", "daily_limit", "publish_times", "template"):
            from handlers.start import handle_settings_input
            await handle_settings_input(update, context)
            return
        elif awaiting in ("ai_generate", "ai_rewrite", "ai_summarize",
                          "ai_quiz", "ai_poll"):
            from handlers.ai_handler import handle_ai_input
            await handle_ai_input(update, context)
            return
        elif awaiting == "schedule_time":
            from handlers.schedule import handle_schedule_input
            await handle_schedule_input(update, context)
            return

    user_id = update.effective_user.id
    text = update.message.text

    content_data = {"text": text, "parse_mode": None}
    content_hash = generate_content_hash(content_data)

    queue_id = await db.add_to_queue(
        user_id=user_id,
        content_type="text",
        content_data=content_data,
        content_hash=content_hash
    )

    if queue_id == -1:
        await update.message.reply_text("⚠️ هذا المحتوى موجود مسبقاً في الـ Queue!")
        return

    await update.message.reply_text(
        f"✅ تم إضافة النص للـ Queue!\n"
        f"🆔 رقم المنشور: #{queue_id}",
        reply_markup=post_action_keyboard(queue_id)
    )


@check_banned
@check_subscription
async def handle_photo_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الصور"""
    user_id = update.effective_user.id
    photo = update.message.photo[-1]  # أعلى جودة
    caption = update.message.caption or ""

    content_data = {
        "file_id": photo.file_id,
        "file_unique_id": photo.file_unique_id,
        "caption": caption,
        "parse_mode": "HTML"
    }
    content_hash = generate_content_hash(
        {"file_unique_id": photo.file_unique_id, "caption": caption}
    )

    queue_id = await db.add_to_queue(
        user_id=user_id,
        content_type="photo",
        content_data=content_data,
        content_hash=content_hash
    )

    if queue_id == -1:
        await update.message.reply_text("⚠️ هذا المحتوى موجود مسبقاً!")
        return

    await update.message.reply_text(
        f"✅ تم إضافة الصورة للـ Queue!\n"
        f"🆔 #{queue_id}",
        reply_markup=post_action_keyboard(queue_id)
    )


@check_banned
@check_subscription
async def handle_video_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الفيديو"""
    user_id = update.effective_user.id
    video = update.message.video
    caption = update.message.caption or ""

    content_data = {
        "file_id": video.file_id,
        "file_unique_id": video.file_unique_id,
        "caption": caption,
        "parse_mode": "HTML"
    }
    content_hash = generate_content_hash(
        {"file_unique_id": video.file_unique_id, "caption": caption}
    )

    queue_id = await db.add_to_queue(
        user_id=user_id,
        content_type="video",
        content_data=content_data,
        content_hash=content_hash
    )

    if queue_id == -1:
        await update.message.reply_text("⚠️ هذا المحتوى موجود مسبقاً!")
        return

    await update.message.reply_text(
        f"✅ تم إضافة الفيديو للـ Queue!\n"
        f"🆔 #{queue_id}",
        reply_markup=post_action_keyboard(queue_id)
    )


@check_banned
@check_subscription
async def handle_audio_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الصوت"""
    user_id = update.effective_user.id
    audio = update.message.audio
    caption = update.message.caption or ""

    content_data = {
        "file_id": audio.file_id,
        "file_unique_id": audio.file_unique_id,
        "caption": caption,
        "parse_mode": "HTML"
    }
    content_hash = generate_content_hash(
        {"file_unique_id": audio.file_unique_id, "caption": caption}
    )

    queue_id = await db.add_to_queue(
        user_id=user_id,
        content_type="audio",
        content_data=content_data,
        content_hash=content_hash
    )

    if queue_id == -1:
        await update.message.reply_text("⚠️ هذا المحتوى موجود مسبقاً!")
        return

    await update.message.reply_text(
        f"✅ تم إضافة الصوت للـ Queue!\n"
        f"🆔 #{queue_id}",
        reply_markup=post_action_keyboard(queue_id)
    )


@check_banned
@check_subscription
async def handle_document_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الملفات"""
    user_id = update.effective_user.id
    document = update.message.document
    caption = update.message.caption or ""

    content_data = {
        "file_id": document.file_id,
        "file_unique_id": document.file_unique_id,
        "file_name": document.file_name,
        "caption": caption,
        "parse_mode": "HTML"
    }
    content_hash = generate_content_hash(
        {"file_unique_id": document.file_unique_id, "caption": caption}
    )

    queue_id = await db.add_to_queue(
        user_id=user_id,
        content_type="document",
        content_data=content_data,
        content_hash=content_hash
    )

    if queue_id == -1:
        await update.message.reply_text("⚠️ هذا المحتوى موجود مسبقاً!")
        return

    await update.message.reply_text(
        f"✅ تم إضافة الملف للـ Queue!\n"
        f"🆔 #{queue_id}",
        reply_markup=post_action_keyboard(queue_id)
    )


async def content_type_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة اختيار نوع المحتوى"""
    query = update.callback_query
    await query.answer()
    data = query.data

    prompts = {
        "content_text": "📝 أرسل النص الذي تريد نشره:",
        "content_photo": "🖼️ أرسل الصورة (مع caption اختياري):",
        "content_video": "🎬 أرسل الفيديو (مع caption اختياري):",
        "content_audio": "🎵 أرسل الملف الصوتي (مع caption اختياري):",
        "content_document": "📎 أرسل الملف (مع caption اختياري):",
        "content_quiz": (
            "❓ أرسل الاختبار بالصيغة التالية:\n\n"
            "/add_quiz الإجابة الصحيحة; السؤال; الخيار1; الخيار2; الخيار3; الخيار4"
        ),
        "content_poll": (
            "📊 أرسل الاستطلاع بالصيغة:\n\n"
            "/add_poll السؤال; الخيار1; الخيار2; الخيار3"
        )
    }

    if data in prompts:
        await query.edit_message_text(prompts[data])


def register_content_handlers(app):
    """تسجيل handlers المحتوى"""
    app.add_handler(CallbackQueryHandler(content_type_callback, pattern="^content_"))
    # ترتيب مهم: الوسائط أولاً ثم النص آخراً
    app.add_handler(MessageHandler(filters.PHOTO & filters.ChatType.PRIVATE, handle_photo_content))
    app.add_handler(MessageHandler(filters.VIDEO & filters.ChatType.PRIVATE, handle_video_content))
    app.add_handler(MessageHandler(filters.AUDIO & filters.ChatType.PRIVATE, handle_audio_content))
    app.add_handler(MessageHandler(
        filters.Document.ALL & filters.ChatType.PRIVATE, handle_document_content
    ))
    # النص آخر شيء (يعمل كـ fallback)
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE,
        handle_text_content
    ))