"""
⚡ Post Now Handler - النشر الفوري
نشر محتوى من الـ Queue مباشرة
"""

import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from database import db
from services.publisher import Publisher
from utils.keyboards import channel_select_keyboard
from utils.decorators import check_banned, check_subscription, rate_limit_check

logger = logging.getLogger(__name__)


@check_banned
@check_subscription
@rate_limit_check
async def post_now_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر /post_now [العدد]"""
    user_id = update.effective_user.id

    # تحديد العدد
    count = 1
    if context.args:
        try:
            count = int(context.args[0])
            count = max(1, min(count, 20))  # بين 1 و 20
        except ValueError:
            pass

    # جلب العناصر
    items = await db.get_next_in_queue(user_id, count)

    if not items:
        await update.message.reply_text(
            "📋 الـ Queue فارغ! لا يوجد محتوى للنشر.\n"
            "أضف محتوى أولاً."
        )
        return

    # جلب القنوات
    channels = await db.get_user_channels(user_id)
    if not channels:
        await update.message.reply_text(
            "📡 لا توجد قنوات! أضف قناة أولاً.\n"
            "استخدم /add_channel"
        )
        return

    # حفظ العناصر المطلوب نشرها
    context.user_data["post_now_items"] = [item["id"] for item in items]

    text = (
        f"⚡ <b>نشر فوري:</b>\n\n"
        f"📋 عدد المنشورات: {len(items)}\n"
        f"📡 اختر القنوات للنشر:"
    )

    await update.message.reply_text(
        text, parse_mode="HTML",
        reply_markup=channel_select_keyboard(channels, "postnow")
    )


async def post_now_channel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """اختيار قناة للنشر الفوري"""
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    item_ids = context.user_data.get("post_now_items", [])
    if not item_ids:
        await query.edit_message_text("❌ لا توجد عناصر للنشر.")
        return

    if data.startswith("postnow_"):
        channel_part = data.replace("postnow_", "")

        if channel_part == "all":
            channels = await db.get_user_channels(user_id)
            channel_ids = [ch["channel_id"] for ch in channels]
        else:
            channel_ids = [int(channel_part)]

        await query.edit_message_text("⏳ جاري النشر...")

        publisher = Publisher(context.bot)
        total_success = 0
        total_fail = 0

        for qid in item_ids:
            items = await db.get_pending_queue(user_id, limit=100)
            item = next((i for i in items if i["id"] == qid), None)
            if not item:
                continue

            # التحقق من الحد اليومي
            count = await db.get_user_post_count_today(user_id)
            user = await db.get_user(user_id)
            if count >= user["daily_limit"]:
                await query.edit_message_text(
                    f"⚠️ وصلت للحد اليومي!\n"
                    f"تم نشر {total_success} من {len(item_ids)} منشور."
                )
                break

            results = await publisher.publish_item(item, channel_ids)
            total_success += len(results["success"])
            total_fail += len(results["failed"])

        report = (
            f"⚡ <b>تقرير النشر الفوري:</b>\n\n"
            f"✅ ناجح: {total_success}\n"
            f"❌ فاشل: {total_fail}\n"
            f"📋 المنشورات: {len(item_ids)}"
        )
        await query.edit_message_text(report, parse_mode="HTML")
        context.user_data.pop("post_now_items", None)


async def publish_single_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نشر منشور واحد فوراً"""
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data.startswith("publish_"):
        queue_id = int(data.replace("publish_", ""))
        channels = await db.get_user_channels(user_id)

        if not channels:
            await query.edit_message_text(
                "📡 لا توجد قنوات! استخدم /add_channel"
            )
            return

        # حفظ الـ queue_id
        context.user_data["publish_single_id"] = queue_id

        await query.edit_message_text(
            f"📡 اختر القناة لنشر المنشور #{queue_id}:",
            reply_markup=channel_select_keyboard(channels, "pubch")
        )


async def publish_channel_select_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """اختيار قناة لنشر منشور واحد"""
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    queue_id = context.user_data.get("publish_single_id")
    if not queue_id:
        await query.edit_message_text("❌ خطأ. حاول مجدداً.")
        return

    if data.startswith("pubch_"):
        channel_part = data.replace("pubch_", "")

        if channel_part == "all":
            channels = await db.get_user_channels(user_id)
            channel_ids = [ch["channel_id"] for ch in channels]
        else:
            channel_ids = [int(channel_part)]

        await query.edit_message_text("⏳ جاري النشر...")

        # جلب العنصر
        items = await db.get_pending_queue(user_id, limit=100)
        item = next((i for i in items if i["id"] == queue_id), None)

        if not item:
            await query.edit_message_text("❌ المنشور غير موجود أو تم نشره مسبقاً.")
            return

        # التحقق من الحد
        count = await db.get_user_post_count_today(user_id)
        user = await db.get_user(user_id)
        if count >= user["daily_limit"]:
            await query.edit_message_text("⚠️ وصلت للحد اليومي!")
            return

        publisher = Publisher(context.bot)
        results = await publisher.publish_item(item, channel_ids)

        success = len(results["success"])
        failed = len(results["failed"])

        text = f"⚡ <b>نتيجة النشر #{queue_id}:</b>\n\n"
        text += f"✅ ناجح: {success} قناة\n"
        if failed > 0:
            text += f"❌ فاشل: {failed} قناة\n"
            for f_item in results["failed"]:
                text += f"  ↳ {f_item.get('error', 'Unknown')[:50]}\n"

        await query.edit_message_text(text, parse_mode="HTML")
        context.user_data.pop("publish_single_id", None)


def register_post_now_handlers(app):
    """تسجيل handlers النشر الفوري"""
    app.add_handler(CommandHandler("post_now", post_now_command))
    app.add_handler(CallbackQueryHandler(post_now_channel_callback, pattern="^postnow_"))
    app.add_handler(CallbackQueryHandler(publish_single_callback, pattern="^publish_\\d+$"))
    app.add_handler(CallbackQueryHandler(publish_channel_select_callback, pattern="^pubch_"))