"""
🛡️ Decorators - حماية وتحقق من الصلاحيات
"""

import functools
import logging
from telegram import Update
from telegram.ext import ContextTypes
from config import config

logger = logging.getLogger(__name__)


def owner_only(func):
    """فقط المالك يمكنه استخدام هذا الأمر"""
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id != config.OWNER_ID:
            await update.message.reply_text("⛔ هذا الأمر متاح فقط لمالك البوت.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper


def check_banned(func):
    """التحقق من أن المستخدم غير محظور"""
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        from database import db
        user_id = update.effective_user.id
        if await db.is_user_banned(user_id):
            await update.effective_message.reply_text(
                "⛔ حسابك محظور. تواصل مع مالك البوت."
            )
            return
        return await func(update, context, *args, **kwargs)
    return wrapper


def check_subscription(func):
    """التحقق من الاشتراك الإجباري"""
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        from services.subscription import check_user_subscription
        user_id = update.effective_user.id

        # المالك معفى
        if user_id == config.OWNER_ID:
            return await func(update, context, *args, **kwargs)

        is_subscribed, missing = await check_user_subscription(
            context.bot, user_id
        )
        if not is_subscribed:
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            keyboard = []
            for ch in missing:
                ch_info = ch.get("info")
                title = ch_info.title if ch_info else f"القناة {ch['id']}"
                username = ch_info.username if ch_info and ch_info.username else None
                if username:
                    keyboard.append([InlineKeyboardButton(
                        f"📌 {title}",
                        url=f"https://t.me/{username}"
                    )])
                else:
                    keyboard.append([InlineKeyboardButton(
                        f"📌 {title}",
                        url=f"https://t.me/c/{str(ch['id'])[4:]}"
                    )])
            keyboard.append([InlineKeyboardButton(
                "✅ تحقق", callback_data="check_subscription"
            )])
            await update.effective_message.reply_text(
                "⚠️ يجب عليك الانضمام للقنوات التالية أولاً:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
        return await func(update, context, *args, **kwargs)
    return wrapper


def rate_limit_check(func):
    """التحقق من حد النشر اليومي"""
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        from database import db
        user_id = update.effective_user.id
        user = await db.get_user(user_id)
        if not user:
            return await func(update, context, *args, **kwargs)

        count = await db.get_user_post_count_today(user_id)
        limit = user["daily_limit"]
        if count >= limit:
            await update.effective_message.reply_text(
                f"⚠️ وصلت للحد اليومي ({limit} منشور).\n"
                f"حاول غداً أو تواصل مع المالك لزيادة الحد."
            )
            return
        return await func(update, context, *args, **kwargs)
    return wrapper