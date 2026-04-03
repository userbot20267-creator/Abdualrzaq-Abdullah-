"""
📡 Channels Handler - إدارة القنوات
إضافة، حذف، عرض القنوات مع التحقق من صلاحيات البوت
"""

import logging
from telegram import Update, ChatMember
from telegram.ext import (
    ContextTypes, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters
)
from database import db
from utils.keyboards import channels_keyboard
from utils.decorators import check_banned, check_subscription

logger = logging.getLogger(__name__)


@check_banned
@check_subscription
async def add_channel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر /add_channel"""
    await update.message.reply_text(
        "📡 أرسل معرّف القناة أو الـ username:\n\n"
        "• مثال ID: -1001234567890\n"
        "• مثال username: @MyChannel\n\n"
        "⚠️ يجب أن يكون البوت Admin في القناة أولاً!\n\n"
        "أرسل /cancel للإلغاء"
    )
    context.user_data["awaiting"] = "add_channel"


@check_banned
@check_subscription
async def remove_channel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر /remove_channel"""
    user_id = update.effective_user.id
    channels = await db.get_user_channels(user_id)

    if not channels:
        await update.message.reply_text("📡 لا توجد لديك قنوات مسجلة.")
        return

    await update.message.reply_text(
        "📡 اختر القناة لحذفها:",
        reply_markup=channels_keyboard(channels)
    )


@check_banned
@check_subscription
async def list_channels_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر /list_channels"""
    user_id = update.effective_user.id
    channels = await db.get_user_channels(user_id)

    if not channels:
        await update.message.reply_text(
            "📡 لا توجد لديك قنوات.\n"
            "استخدم /add_channel لإضافة قناة."
        )
        return

    text = "📡 <b>قنواتك:</b>\n\n"
    for i, ch in enumerate(channels, 1):
        name = ch.get("channel_name", "Unknown")
        username = ch.get("channel_username", "")
        ch_id = ch.get("channel_id")
        text += f"{i}. <b>{name}</b>"
        if username:
            text += f" (@{username})"
        text += f"\n   🆔 <code>{ch_id}</code>\n\n"

    await update.message.reply_text(
        text, parse_mode="HTML",
        reply_markup=channels_keyboard(channels)
    )


async def handle_channel_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة إدخال القناة"""
    if context.user_data.get("awaiting") != "add_channel":
        return

    text = update.message.text.strip()
    user_id = update.effective_user.id

    if text == "/cancel":
        context.user_data.pop("awaiting", None)
        await update.message.reply_text("❌ تم الإلغاء")
        return

    # محاولة جلب معلومات القناة
    try:
        if text.startswith("@"):
            chat = await context.bot.get_chat(text)
        else:
            chat = await context.bot.get_chat(int(text))

        channel_id = chat.id
        channel_name = chat.title or "Unknown"
        channel_username = chat.username

        # التحقق من أن البوت Admin
        bot_member = await context.bot.get_chat_member(channel_id, context.bot.id)
        if bot_member.status not in [ChatMember.ADMINISTRATOR, ChatMember.OWNER]:
            await update.message.reply_text(
                "⚠️ البوت ليس Admin في هذه القناة!\n"
                "أضف البوت كـ Admin ثم حاول مجدداً."
            )
            return

        # التحقق من صلاحية النشر
        if not getattr(bot_member, 'can_post_messages', True):
            await update.message.reply_text(
                "⚠️ البوت لا يملك صلاحية النشر في القناة!"
            )
            return

        # إضافة القناة
        success = await db.add_channel(
            user_id, channel_id, channel_name, channel_username
        )

        if success:
            await update.message.reply_text(
                f"✅ تم إضافة القناة بنجاح!\n\n"
                f"📡 {channel_name}\n"
                f"🆔 <code>{channel_id}</code>",
                parse_mode="HTML"
            )
        else:
            await update.message.reply_text("❌ فشل في إضافة القناة.")

    except Exception as e:
        logger.error(f"Add channel error: {e}")
        await update.message.reply_text(
            f"❌ خطأ: لم أتمكن من الوصول للقناة.\n"
            f"تأكد من:\n"
            f"• صحة المعرّف\n"
            f"• أن البوت Admin في القناة"
        )

    context.user_data.pop("awaiting", None)


async def channel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة أزرار القنوات"""
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data.startswith("ch_remove_"):
        channel_id = int(data.replace("ch_remove_", ""))
        success = await db.remove_channel(user_id, channel_id)
        if success:
            await query.edit_message_text(f"✅ تم حذف القناة {channel_id}")
        else:
            await query.edit_message_text("❌ فشل في حذف القناة")

    elif data.startswith("ch_info_"):
        channel_id = int(data.replace("ch_info_", ""))
        channel = await db.get_channel(user_id, channel_id)
        if channel:
            await query.answer(
                f"📡 {channel['channel_name']}\n🆔 {channel_id}",
                show_alert=True
            )

    elif data == "ch_add":
        await query.edit_message_text(
            "📡 أرسل معرّف القناة أو الـ username:\n\n"
            "• مثال: -1001234567890\n"
            "• مثال: @MyChannel\n\n"
            "أرسل /cancel للإلغاء"
        )
        context.user_data["awaiting"] = "add_channel"


def register_channel_handlers(app):
    """تسجيل handlers القنوات"""
    app.add_handler(CommandHandler("add_channel", add_channel_command))
    app.add_handler(CommandHandler("remove_channel", remove_channel_command))
    app.add_handler(CommandHandler("list_channels", list_channels_cmd))
    app.add_handler(CallbackQueryHandler(channel_callback, pattern="^ch_"))