"""
📋 Queue Handler - إدارة الـ Queue
عرض، حذف، مسح المحتوى المنتظر
"""

import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from database import db
from utils.helpers import format_queue_item
from utils.keyboards import queue_keyboard, confirm_keyboard
from utils.decorators import check_banned, check_subscription

logger = logging.getLogger(__name__)


@check_banned
@check_subscription
async def queue_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر /queue"""
    await show_queue(update, context)


async def show_queue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض محتويات الـ Queue"""
    user_id = update.effective_user.id
    items = await db.get_pending_queue(user_id, limit=20)
    total = await db.get_queue_count(user_id)

    if not items:
        text = (
            "📋 <b>الـ Queue فارغ!</b>\n\n"
            "أرسل أي محتوى (نص/صورة/فيديو...) لإضافته.\n"
            "أو استخدم /generate لتوليد محتوى بالذكاء الاصطناعي."
        )
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.edit_message_text(text, parse_mode="HTML")
        else:
            await update.message.reply_text(text, parse_mode="HTML")
        return

    text = f"📋 <b>الـ Queue ({total} عنصر):</b>\n\n"
    for item in items[:10]:
        text += format_queue_item(item) + "\n\n"

    if total > 10:
        text += f"... و {total - 10} عناصر أخرى"

    keyboard = queue_keyboard(items)

    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.edit_message_text(
            text, parse_mode="HTML", reply_markup=keyboard
        )
    else:
        await update.message.reply_text(
            text, parse_mode="HTML", reply_markup=keyboard
        )


async def queue_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة أزرار الـ Queue"""
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data == "q_refresh":
        items = await db.get_pending_queue(user_id, limit=20)
        total = await db.get_queue_count(user_id)
        if not items:
            await query.edit_message_text("📋 الـ Queue فارغ!")
            return
        text = f"📋 <b>الـ Queue ({total} عنصر):</b>\n\n"
        for item in items[:10]:
            text += format_queue_item(item) + "\n\n"
        await query.edit_message_text(
            text, parse_mode="HTML",
            reply_markup=queue_keyboard(items)
        )

    elif data.startswith("q_del_"):
        queue_id = int(data.replace("q_del_", ""))
        success = await db.delete_from_queue(queue_id, user_id)
        if success:
            await query.answer("✅ تم الحذف", show_alert=True)
            # تحديث العرض
            items = await db.get_pending_queue(user_id, limit=20)
            total = await db.get_queue_count(user_id)
            if not items:
                await query.edit_message_text("📋 الـ Queue فارغ الآن!")
            else:
                text = f"📋 <b>الـ Queue ({total} عنصر):</b>\n\n"
                for item in items[:10]:
                    text += format_queue_item(item) + "\n\n"
                await query.edit_message_text(
                    text, parse_mode="HTML",
                    reply_markup=queue_keyboard(items)
                )
        else:
            await query.answer("❌ فشل الحذف", show_alert=True)

    elif data.startswith("q_view_"):
        queue_id = int(data.replace("q_view_", ""))
        items = await db.get_pending_queue(user_id, limit=100)
        item = next((i for i in items if i["id"] == queue_id), None)
        if item:
            detail = format_queue_item(item)
            content_data = item["content_data"]
            if isinstance(content_data, str):
                content_data = json.loads(content_data)

            if item["content_type"] == "text":
                detail += f"\n\n📝 <b>المحتوى الكامل:</b>\n{content_data.get('text', '')[:1000]}"
            elif item["content_type"] == "quiz":
                detail += f"\n\n❓ <b>السؤال:</b> {content_data.get('question', '')}"
                opts = content_data.get("options", [])
                correct_id = content_data.get("correct_option_id", 0)
                for i, opt in enumerate(opts):
                    marker = "✅" if i == correct_id else "⬜"
                    detail += f"\n  {marker} {opt}"
            elif item["content_type"] == "poll":
                detail += f"\n\n📊 <b>السؤال:</b> {content_data.get('question', '')}"
                for opt in content_data.get("options", []):
                    detail += f"\n  ⬜ {opt}"

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("⚡ نشر", callback_data=f"publish_{queue_id}"),
                 InlineKeyboardButton("⏰ جدولة", callback_data=f"schedule_{queue_id}")],
                [InlineKeyboardButton("❌ حذف", callback_data=f"q_del_{queue_id}"),
                 InlineKeyboardButton("🔙 رجوع", callback_data="q_refresh")]
            ])
            await query.edit_message_text(
                detail, parse_mode="HTML", reply_markup=keyboard
            )
        else:
            await query.answer("❌ العنصر غير موجود", show_alert=True)

    elif data == "q_clear":
        await query.edit_message_text(
            "⚠️ هل أنت متأكد من مسح كل الـ Queue؟",
            reply_markup=confirm_keyboard("clear_queue")
        )

    elif data == "confirm_clear_queue":
        count = await db.clear_user_queue(user_id)
        await query.edit_message_text(f"🗑️ تم مسح {count} عنصر من الـ Queue!")

    elif data == "cancel":
        await query.edit_message_text("❌ تم الإلغاء")


def register_queue_handlers(app):
    """تسجيل handlers الـ Queue"""
    app.add_handler(CommandHandler("queue", queue_command))
    app.add_handler(CallbackQueryHandler(queue_callback,
        pattern="^(q_|confirm_clear_queue|cancel)"))