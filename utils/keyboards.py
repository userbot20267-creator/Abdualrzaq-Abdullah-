"""
⌨️ Keyboards - لوحات المفاتيح للبوت
"""

from telegram import (
    InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton
)


def main_menu_keyboard():
    """القائمة الرئيسية"""
    keyboard = [
        [KeyboardButton("📝 إنشاء محتوى"), KeyboardButton("🤖 الذكاء الاصطناعي")],
        [KeyboardButton("📋 Queue"), KeyboardButton("📡 قنواتي")],
        [KeyboardButton("⏰ الجدولة"), KeyboardButton("📊 إحصائياتي")],
        [KeyboardButton("⚡ نشر فوري"), KeyboardButton("⚙️ الإعدادات")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def admin_menu_keyboard():
    """قائمة المالك"""
    keyboard = [
        [InlineKeyboardButton("👥 المستخدمين", callback_data="admin_users"),
         InlineKeyboardButton("📊 الإحصائيات", callback_data="admin_stats")],
        [InlineKeyboardButton("🔍 بحث مستخدم", callback_data="admin_search"),
         InlineKeyboardButton("📋 Queue عام", callback_data="admin_queue")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="admin_back")]
    ]
    return InlineKeyboardMarkup(keyboard)


def content_type_keyboard():
    """اختيار نوع المحتوى"""
    keyboard = [
        [InlineKeyboardButton("📝 نص", callback_data="content_text"),
         InlineKeyboardButton("🖼️ صورة", callback_data="content_photo")],
        [InlineKeyboardButton("🎬 فيديو", callback_data="content_video"),
         InlineKeyboardButton("🎵 صوت", callback_data="content_audio")],
        [InlineKeyboardButton("📎 ملف", callback_data="content_document"),
         InlineKeyboardButton("❓ اختبار Quiz", callback_data="content_quiz")],
        [InlineKeyboardButton("📊 استطلاع Poll", callback_data="content_poll")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
    ]
    return InlineKeyboardMarkup(keyboard)


def ai_menu_keyboard():
    """قائمة الذكاء الاصطناعي"""
    keyboard = [
        [InlineKeyboardButton("✍️ توليد منشور", callback_data="ai_generate"),
         InlineKeyboardButton("🔄 إعادة صياغة", callback_data="ai_rewrite")],
        [InlineKeyboardButton("📋 تلخيص", callback_data="ai_summarize")],
        [InlineKeyboardButton("❓ توليد Quiz", callback_data="ai_quiz"),
         InlineKeyboardButton("📊 توليد Poll", callback_data="ai_poll")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
    ]
    return InlineKeyboardMarkup(keyboard)


def channels_keyboard(channels: list):
    """عرض قنوات المستخدم مع أزرار حذف"""
    keyboard = []
    for ch in channels:
        name = ch.get("channel_name", "Unknown")
        ch_id = ch.get("channel_id")
        keyboard.append([
            InlineKeyboardButton(f"📡 {name}", callback_data=f"ch_info_{ch_id}"),
            InlineKeyboardButton("❌", callback_data=f"ch_remove_{ch_id}")
        ])
    keyboard.append([InlineKeyboardButton("➕ إضافة قناة", callback_data="ch_add")])
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)


def queue_keyboard(queue_items: list):
    """عرض عناصر الـ Queue"""
    keyboard = []
    for item in queue_items[:10]:
        qid = item["id"]
        ctype = item["content_type"]
        emoji = {"text": "📝", "photo": "🖼️", "video": "🎬",
                 "audio": "🎵", "document": "📎",
                 "quiz": "❓", "poll": "📊"}.get(ctype, "📌")
        keyboard.append([
            InlineKeyboardButton(f"{emoji} #{qid} {ctype}", callback_data=f"q_view_{qid}"),
            InlineKeyboardButton("❌", callback_data=f"q_del_{qid}")
        ])
    keyboard.append([
        InlineKeyboardButton("🗑️ مسح الكل", callback_data="q_clear"),
        InlineKeyboardButton("🔄 تحديث", callback_data="q_refresh")
    ])
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)


def confirm_keyboard(action: str):
    """تأكيد العملية"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ تأكيد", callback_data=f"confirm_{action}"),
         InlineKeyboardButton("❌ إلغاء", callback_data="cancel")]
    ])


def channel_select_keyboard(channels: list, prefix: str = "select_ch"):
    """اختيار قنوات للنشر"""
    keyboard = []
    for ch in channels:
        name = ch.get("channel_name", "Unknown")
        ch_id = ch.get("channel_id")
        keyboard.append([
            InlineKeyboardButton(f"📡 {name}", callback_data=f"{prefix}_{ch_id}")
        ])
    keyboard.append([
        InlineKeyboardButton("📡 جميع القنوات", callback_data=f"{prefix}_all")
    ])
    keyboard.append([InlineKeyboardButton("🔙 إلغاء", callback_data="cancel")])
    return InlineKeyboardMarkup(keyboard)


def post_action_keyboard(queue_id: int):
    """أزرار بعد إضافة المحتوى للـ Queue"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚡ نشر الآن", callback_data=f"publish_{queue_id}"),
         InlineKeyboardButton("⏰ جدولة", callback_data=f"schedule_{queue_id}")],
        [InlineKeyboardButton("📋 عرض Queue", callback_data="q_refresh"),
         InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
    ])


def settings_keyboard():
    """إعدادات المستخدم"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🕐 المنطقة الزمنية", callback_data="set_timezone"),
         InlineKeyboardButton("📊 حد النشر اليومي", callback_data="set_daily_limit")],
        [InlineKeyboardButton("🔄 النشر التلقائي", callback_data="set_auto_publish"),
         InlineKeyboardButton("📝 قالب النشر", callback_data="set_template")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
    ])


def user_action_keyboard(telegram_id: int, is_banned: bool):
    """أزرار إدارة مستخدم (للمالك)"""
    ban_text = "🔓 إلغاء الحظر" if is_banned else "🔒 حظر"
    ban_data = f"admin_unban_{telegram_id}" if is_banned else f"admin_ban_{telegram_id}"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(ban_text, callback_data=ban_data),
         InlineKeyboardButton("📡 قنواته", callback_data=f"admin_uch_{telegram_id}")],
        [InlineKeyboardButton("📋 Queue", callback_data=f"admin_uq_{telegram_id}"),
         InlineKeyboardButton("📊 إحصائيات", callback_data=f"admin_ust_{telegram_id}")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="admin_users")]
    ])