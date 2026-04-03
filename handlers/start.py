"""
🏠 Start Handler - أوامر البداية والمساعدة والإعدادات
"""

import logging
from telegram import Update
from telegram.ext import (
    ContextTypes, CommandHandler, CallbackQueryHandler,
    ConversationHandler, MessageHandler, filters
)
from database import db
from config import config
from utils.keyboards import (
    main_menu_keyboard, settings_keyboard,
    content_type_keyboard, ai_menu_keyboard
)
from utils.decorators import check_banned, check_subscription

logger = logging.getLogger(__name__)

# حالات المحادثة
SET_TIMEZONE, SET_DAILY_LIMIT = range(2)


@check_subscription
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر /start"""
    user = update.effective_user
    db_user = await db.get_or_create_user(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name
    )

    if db_user.get("is_banned"):
        await update.message.reply_text("⛔ حسابك محظور. تواصل مع المالك.")
        return

    welcome = (
        f"مرحباً {user.first_name}! 👋\n\n"
        f"🤖 أنا بوت إدارة المحتوى والنشر التلقائي.\n\n"
        f"📌 ما يمكنني فعله:\n"
        f"• إدارة قنواتك المتعددة\n"
        f"• إنشاء ونشر المحتوى تلقائياً\n"
        f"• جدولة المنشورات\n"
        f"• توليد محتوى بالذكاء الاصطناعي\n"
        f"• إنشاء اختبارات Quiz واستطلاعات Poll\n\n"
        f"📖 اضغط /help لعرض جميع الأوامر"
    )
    await update.message.reply_text(welcome, reply_markup=main_menu_keyboard())


@check_banned
@check_subscription
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر /help"""
    help_text = (
        "📖 <b>قائمة الأوامر:</b>\n\n"
        "🏠 <b>عام:</b>\n"
        "/start - البداية\n"
        "/help - المساعدة\n"
        "/stats - إحصائياتي\n\n"
        "📡 <b>القنوات:</b>\n"
        "/add_channel - إضافة قناة\n"
        "/remove_channel - حذف قناة\n"
        "/list_channels - عرض قنواتي\n\n"
        "📝 <b>المحتوى:</b>\n"
        "أرسل أي محتوى (نص/صورة/فيديو/صوت/ملف) مباشرة\n"
        "/add_quiz - إضافة اختبار\n"
        "/add_poll - إضافة استطلاع\n\n"
        "🤖 <b>الذكاء الاصطناعي:</b>\n"
        "/generate [الموضوع] - توليد منشور\n"
        "/rewrite - إعادة صياغة\n"
        "/summarize - تلخيص\n\n"
        "📋 <b>الـ Queue:</b>\n"
        "/queue - عرض المحتوى المنتظر\n"
        "/post_now [العدد] - نشر فوري\n\n"
        "⏰ <b>الجدولة:</b>\n"
        "/schedule - إعدادات الجدولة\n\n"
        "⚙️ <b>الإعدادات:</b>\n"
        "/settings - إعداداتي\n"
    )

    if update.effective_user.id == config.OWNER_ID:
        help_text += (
            "\n\n👑 <b>أوامر المالك:</b>\n"
            "/admin - لوحة التحكم\n"
        )

    await update.message.reply_text(help_text, parse_mode="HTML")


@check_banned
@check_subscription
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر /stats"""
    user_id = update.effective_user.id
    stats = await db.get_user_stats(user_id)
    user = await db.get_user(user_id)

    text = (
        f"📊 <b>إحصائياتك:</b>\n\n"
        f"✅ المنشورات اليوم: {stats['today_published']}/{user['daily_limit']}\n"
        f"📈 إجمالي المنشورات: {stats['total_published']}\n"
        f"⏳ في الانتظار (Queue): {stats['pending_queue']}\n"
        f"📡 القنوات النشطة: {stats['active_channels']}\n"
        f"❌ المنشورات الفاشلة: {stats['failed_posts']}\n"
        f"🕐 المنطقة الزمنية: {user.get('timezone', 'Asia/Riyadh')}"
    )
    await update.message.reply_text(text, parse_mode="HTML")


@check_banned
async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر /settings"""
    await update.message.reply_text(
        "⚙️ <b>الإعدادات:</b>",
        parse_mode="HTML",
        reply_markup=settings_keyboard()
    )


async def settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة أزرار الإعدادات"""
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "set_timezone":
        await query.edit_message_text(
            "🕐 أرسل المنطقة الزمنية:\n"
            "مثال: Asia/Riyadh, Europe/London, America/New_York\n\n"
            "أو أرسل /cancel للإلغاء"
        )
        context.user_data["awaiting"] = "timezone"

    elif data == "set_daily_limit":
        await query.edit_message_text(
            "📊 أرسل الحد اليومي للنشر (رقم):\n"
            "أو أرسل /cancel للإلغاء"
        )
        context.user_data["awaiting"] = "daily_limit"

    elif data == "set_auto_publish":
        settings = await db.get_auto_publish_settings(query.from_user.id)
        status = "✅ مفعّل" if settings.get("is_enabled") else "❌ معطّل"
        times = settings.get("publish_times", [])
        if isinstance(times, str):
            import json
            times = json.loads(times)

        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "🔄 تبديل الحالة",
                callback_data="toggle_auto_publish"
            )],
            [InlineKeyboardButton(
                "⏰ تعديل الأوقات",
                callback_data="edit_publish_times"
            )],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_settings")]
        ])
        await query.edit_message_text(
            f"🔄 <b>النشر التلقائي:</b>\n\n"
            f"الحالة: {status}\n"
            f"الأوقات: {', '.join(times) if times else 'لم تُحدد'}\n",
            parse_mode="HTML",
            reply_markup=keyboard
        )

    elif data == "set_template":
        await query.edit_message_text(
            "📝 أرسل قالب النشر.\n"
            "يمكنك استخدام {content} كمكان للمحتوى.\n\n"
            "مثال:\n"
            "📌 {content}\n\n"
            "━━━━━━━━━━━\n"
            "📡 @YourChannel\n\n"
            "أو أرسل /cancel للإلغاء"
        )
        context.user_data["awaiting"] = "template"

    elif data == "back_settings":
        await query.edit_message_text(
            "⚙️ <b>الإعدادات:</b>",
            parse_mode="HTML",
            reply_markup=settings_keyboard()
        )

    elif data == "toggle_auto_publish":
        user_id = query.from_user.id
        settings = await db.get_auto_publish_settings(user_id)
        new_state = not settings.get("is_enabled", False)
        await db.update_auto_publish_settings(user_id, is_enabled=new_state)
        status = "✅ مفعّل" if new_state else "❌ معطّل"
        await query.edit_message_text(f"🔄 النشر التلقائي الآن: {status}")

    elif data == "edit_publish_times":
        await query.edit_message_text(
            "⏰ أرسل أوقات النشر مفصولة بفاصلة:\n"
            "مثال: 08:00, 12:00, 18:00, 21:00\n\n"
            "أو أرسل /cancel للإلغاء"
        )
        context.user_data["awaiting"] = "publish_times"

    elif data == "check_subscription":
        from services.subscription import check_user_subscription
        is_sub, missing = await check_user_subscription(
            context.bot, query.from_user.id
        )
        if is_sub:
            await query.edit_message_text("✅ تم التحقق بنجاح! أرسل /start")
        else:
            await query.answer("❌ لم تنضم بعد لجميع القنوات", show_alert=True)

    elif data == "back_main":
        await query.edit_message_text("🏠 القائمة الرئيسية")


async def handle_settings_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة مدخلات الإعدادات"""
    awaiting = context.user_data.get("awaiting")
    if not awaiting:
        return

    user_id = update.effective_user.id
    text = update.message.text.strip()

    if text == "/cancel":
        context.user_data.pop("awaiting", None)
        await update.message.reply_text("❌ تم الإلغاء", reply_markup=main_menu_keyboard())
        return

    if awaiting == "timezone":
        import pytz
        if text in pytz.all_timezones:
            await db.update_user_timezone(user_id, text)
            await update.message.reply_text(
                f"✅ تم تحديث المنطقة الزمنية إلى: {text}",
                reply_markup=main_menu_keyboard()
            )
        else:
            await update.message.reply_text("❌ منطقة زمنية غير صحيحة. حاول مجدداً.")
            return
        context.user_data.pop("awaiting", None)

    elif awaiting == "daily_limit":
        try:
            limit = int(text)
            if 1 <= limit <= 1000:
                await db.update_user_daily_limit(user_id, limit)
                await update.message.reply_text(
                    f"✅ تم تحديث الحد اليومي إلى: {limit}",
                    reply_markup=main_menu_keyboard()
                )
            else:
                await update.message.reply_text("❌ الرقم يجب أن يكون بين 1 و 1000")
                return
        except ValueError:
            await update.message.reply_text("❌ أرسل رقماً صحيحاً")
            return
        context.user_data.pop("awaiting", None)

    elif awaiting == "publish_times":
        times = [t.strip() for t in text.split(",")]
        valid_times = []
        for t in times:
            try:
                parts = t.split(":")
                h, m = int(parts[0]), int(parts[1])
                if 0 <= h <= 23 and 0 <= m <= 59:
                    valid_times.append(f"{h:02d}:{m:02d}")
            except (ValueError, IndexError):
                pass
        if valid_times:
            await db.update_auto_publish_settings(user_id, publish_times=valid_times)
            await update.message.reply_text(
                f"✅ تم تحديث أوقات النشر:\n{', '.join(valid_times)}",
                reply_markup=main_menu_keyboard()
            )
        else:
            await update.message.reply_text("❌ صيغة غير صحيحة. مثال: 08:00, 12:00")
            return
        context.user_data.pop("awaiting", None)

    elif awaiting == "template":
        await db.update_auto_publish_settings(user_id, template=text)
        await update.message.reply_text(
            "✅ تم حفظ قالب النشر!",
            reply_markup=main_menu_keyboard()
        )
        context.user_data.pop("awaiting", None)


# === معالجة أزرار القائمة الرئيسية ===
async def handle_main_menu_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة أزرار القائمة الرئيسية (ReplyKeyboard)"""
    text = update.message.text

    if text == "📝 إنشاء محتوى":
        await update.message.reply_text(
            "📝 اختر نوع المحتوى:",
            reply_markup=content_type_keyboard()
        )
    elif text == "🤖 الذكاء الاصطناعي":
        await update.message.reply_text(
            "🤖 اختر خدمة الذكاء الاصطناعي:",
            reply_markup=ai_menu_keyboard()
        )
    elif text == "📋 Queue":
        from handlers.queue_handler import show_queue
        await show_queue(update, context)
    elif text == "📡 قنواتي":
        from handlers.channels import list_channels_cmd
        await list_channels_cmd(update, context)
    elif text == "⏰ الجدولة":
        from handlers.schedule import schedule_command
        await schedule_command(update, context)
    elif text == "📊 إحصائياتي":
        await stats_command(update, context)
    elif text == "⚡ نشر فوري":
        from handlers.post_now import post_now_command
        await post_now_command(update, context)
    elif text == "⚙️ الإعدادات":
        await update.message.reply_text(
            "⚙️ <b>الإعدادات:</b>",
            parse_mode="HTML",
            reply_markup=settings_keyboard()
        )


def register_start_handlers(app):
    """تسجيل handlers البداية"""
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("settings", settings_command))
    app.add_handler(CallbackQueryHandler(settings_callback,
        pattern="^(set_|toggle_|edit_|back_settings|check_subscription|back_main)"))
    # أزرار القائمة الرئيسية
    app.add_handler(MessageHandler(
        filters.Regex("^(📝 إنشاء محتوى|🤖 الذكاء الاصطناعي|📋 Queue|📡 قنواتي|⏰ الجدولة|📊 إحصائياتي|⚡ نشر فوري|⚙️ الإعدادات)$"),
        handle_main_menu_buttons
    ))