"""
👑 Admin Handler - لوحة تحكم المالك
إدارة المستخدمين، الإحصائيات، التحكم الكامل
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters
)
from database import db
from config import config
from utils.keyboards import admin_menu_keyboard, user_action_keyboard
from utils.decorators import owner_only

logger = logging.getLogger(__name__)


@owner_only
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر /admin"""
    stats = await db.get_global_stats()

    text = (
        f"👑 <b>لوحة تحكم المالك</b>\n\n"
        f"📊 <b>إحصائيات سريعة:</b>\n"
        f"👥 المستخدمين: {stats['total_users']} (نشط: {stats['active_users']})\n"
        f"📡 القنوات: {stats['total_channels']}\n"
        f"📈 إجمالي المنشورات: {stats['total_published']}\n"
        f"📅 منشورات اليوم: {stats['today_published']}\n"
        f"⏳ في الانتظار: {stats['total_pending']}"
    )

    await update.message.reply_text(
        text, parse_mode="HTML",
        reply_markup=admin_menu_keyboard()
    )


async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة أزرار لوحة المالك"""
    query = update.callback_query

    # التحقق من أنه المالك
    if query.from_user.id != config.OWNER_ID:
        await query.answer("⛔ غير مصرح", show_alert=True)
        return

    await query.answer()
    data = query.data

    if data == "admin_users":
        users = await db.get_all_users()
        if not users:
            await query.edit_message_text("👥 لا يوجد مستخدمين.")
            return

        text = "👥 <b>المستخدمين:</b>\n\n"
        keyboard = []
        for u in users[:20]:
            status = "🔒" if u["is_banned"] else "✅"
            name = u.get("first_name", "Unknown")
            username = f"@{u['username']}" if u.get("username") else ""
            text += f"{status} {name} {username} | <code>{u['telegram_id']}</code>\n"
            keyboard.append([InlineKeyboardButton(
                f"{status} {name} ({u['telegram_id']})",
                callback_data=f"admin_user_{u['telegram_id']}"
            )])

        keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="admin_back")])
        await query.edit_message_text(
            text, parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data == "admin_stats":
        stats = await db.get_global_stats()
        text = (
            f"📊 <b>الإحصائيات التفصيلية:</b>\n\n"
            f"👥 إجمالي المستخدمين: {stats['total_users']}\n"
            f"✅ مستخدمين نشطين: {stats['active_users']}\n"
            f"🔒 محظورين: {stats['total_users'] - stats['active_users']}\n\n"
            f"📡 القنوات النشطة: {stats['total_channels']}\n\n"
            f"📈 إجمالي المنشورات: {stats['total_published']}\n"
            f"📅 منشورات اليوم: {stats['today_published']}\n"
            f"⏳ في الانتظار: {stats['total_pending']}"
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 رجوع", callback_data="admin_back")]
        ])
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=keyboard)

    elif data == "admin_search":
        await query.edit_message_text(
            "🔍 أرسل Telegram ID للمستخدم:\n\nأو /cancel للإلغاء"
        )
        context.user_data["awaiting"] = "admin_search"

    elif data.startswith("admin_user_"):
        tid = int(data.replace("admin_user_", ""))
        user = await db.get_user(tid)
        if not user:
            await query.answer("❌ المستخدم غير موجود", show_alert=True)
            return

        stats = await db.get_user_stats(tid)
        channels = await db.get_user_channels(tid)

        text = (
            f"👤 <b>معلومات المستخدم:</b>\n\n"
            f"📛 الاسم: {user.get('first_name', 'Unknown')}\n"
            f"👤 Username: @{user.get('username', 'N/A')}\n"
            f"🆔 ID: <code>{tid}</code>\n"
            f"🔒 محظور: {'نعم' if user['is_banned'] else 'لا'}\n"
            f"📊 الحد اليومي: {user['daily_limit']}\n"
            f"🕐 المنطقة: {user.get('timezone', 'N/A')}\n\n"
            f"📈 الإحصائيات:\n"
            f"  ✅ إجمالي المنشورات: {stats['total_published']}\n"
            f"  📅 اليوم: {stats['today_published']}\n"
            f"  ⏳ في الانتظار: {stats['pending_queue']}\n"
            f"  📡 القنوات: {stats['active_channels']}"
        )

        await query.edit_message_text(
            text, parse_mode="HTML",
            reply_markup=user_action_keyboard(tid, user["is_banned"])
        )

    elif data.startswith("admin_ban_"):
        tid = int(data.replace("admin_ban_", ""))
        await db.set_user_banned(tid, True)
        await query.answer("✅ تم حظر المستخدم", show_alert=True)
        # تحديث العرض
        user = await db.get_user(tid)
        if user:
            await query.edit_message_text(
                f"🔒 تم حظر المستخدم {tid}",
                reply_markup=user_action_keyboard(tid, True)
            )

    elif data.startswith("admin_unban_"):
        tid = int(data.replace("admin_unban_", ""))
        await db.set_user_banned(tid, False)
        await query.answer("✅ تم إلغاء حظر المستخدم", show_alert=True)
        user = await db.get_user(tid)
        if user:
            await query.edit_message_text(
                f"🔓 تم إلغاء حظر المستخدم {tid}",
                reply_markup=user_action_keyboard(tid, False)
            )

    elif data.startswith("admin_uch_"):
        tid = int(data.replace("admin_uch_", ""))
        channels = await db.get_user_channels(tid)
        if not channels:
            await query.answer("لا توجد قنوات", show_alert=True)
            return
        text = f"📡 <b>قنوات المستخدم {tid}:</b>\n\n"
        for ch in channels:
            text += f"• {ch['channel_name']} ({ch['channel_id']})\n"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 رجوع", callback_data=f"admin_user_{tid}")]
        ])
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=keyboard)

    elif data.startswith("admin_uq_"):
        tid = int(data.replace("admin_uq_", ""))
        items = await db.get_pending_queue(tid, limit=10)
        total = await db.get_queue_count(tid)
        if not items:
            await query.answer("Queue فارغ", show_alert=True)
            return
        from utils.helpers import format_queue_item
        text = f"📋 <b>Queue المستخدم {tid} ({total}):</b>\n\n"
        for item in items:
            text += format_queue_item(item) + "\n\n"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 رجوع", callback_data=f"admin_user_{tid}")]
        ])
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=keyboard)

    elif data.startswith("admin_ust_"):
        tid = int(data.replace("admin_ust_", ""))
        stats = await db.get_user_stats(tid)
        text = (
            f"📊 <b>إحصائيات المستخدم {tid}:</b>\n\n"
            f"✅ إجمالي: {stats['total_published']}\n"
            f"📅 اليوم: {stats['today_published']}\n"
            f"⏳ منتظر: {stats['pending_queue']}\n"
            f"📡 القنوات: {stats['active_channels']}\n"
            f"❌ فاشل: {stats['failed_posts']}"
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 رجوع", callback_data=f"admin_user_{tid}")]
        ])
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=keyboard)

    elif data == "admin_back":
        stats = await db.get_global_stats()
        text = (
            f"👑 <b>لوحة تحكم المالك</b>\n\n"
            f"👥 المستخدمين: {stats['total_users']}\n"
            f"📡 القنوات: {stats['total_channels']}\n"
            f"📈 المنشورات: {stats['total_published']}\n"
            f"⏳ في الانتظار: {stats['total_pending']}"
        )
        await query.edit_message_text(
            text, parse_mode="HTML",
            reply_markup=admin_menu_keyboard()
        )

    elif data == "admin_queue":
        # عرض Queue عام
        stats = await db.get_global_stats()
        text = (
            f"📋 <b>الـ Queue العام:</b>\n\n"
            f"⏳ إجمالي المنتظر: {stats['total_pending']}"
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 رجوع", callback_data="admin_back")]
        ])
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=keyboard)


async def admin_search_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة بحث المالك عن مستخدم"""
    if context.user_data.get("awaiting") != "admin_search":
        return
    if update.effective_user.id != config.OWNER_ID:
        return

    text = update.message.text.strip()
    if text == "/cancel":
        context.user_data.pop("awaiting", None)
        await update.message.reply_text("❌ تم الإلغاء")
        return

    try:
        tid = int(text)
        user = await db.get_user(tid)
        if user:
            stats = await db.get_user_stats(tid)
            reply = (
                f"👤 <b>{user.get('first_name', 'Unknown')}</b>\n"
                f"🆔 <code>{tid}</code>\n"
                f"🔒 محظور: {'نعم' if user['is_banned'] else 'لا'}\n"
                f"📈 المنشورات: {stats['total_published']}"
            )
            await update.message.reply_text(
                reply, parse_mode="HTML",
                reply_markup=user_action_keyboard(tid, user["is_banned"])
            )
        else:
            await update.message.reply_text("❌ المستخدم غير موجود.")
    except ValueError:
        await update.message.reply_text("❌ أرسل رقم ID صحيح.")

    context.user_data.pop("awaiting", None)


def register_admin_handlers(app):
    """تسجيل handlers لوحة المالك"""
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CallbackQueryHandler(admin_callback, pattern="^admin_"))