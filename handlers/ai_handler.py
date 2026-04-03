"""
🤖 AI Handler - أوامر الذكاء الاصطناعي
توليد، إعادة صياغة، تلخيص، إنشاء Quiz/Poll
"""

import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from database import db
from services.ai_service import ai_service
from utils.helpers import generate_content_hash
from utils.keyboards import post_action_keyboard, ai_menu_keyboard
from utils.decorators import check_banned, check_subscription

logger = logging.getLogger(__name__)


@check_banned
@check_subscription
async def generate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر /generate"""
    args = " ".join(context.args) if context.args else ""
    if args:
        await _do_generate(update, context, args)
    else:
        await update.message.reply_text(
            "🤖 أرسل الموضوع الذي تريد توليد منشور عنه:\n\n"
            "أو أرسل /cancel للإلغاء"
        )
        context.user_data["awaiting"] = "ai_generate"


@check_banned
@check_subscription
async def rewrite_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر /rewrite"""
    await update.message.reply_text(
        "🔄 أرسل النص الذي تريد إعادة صياغته:\n\n"
        "أو أرسل /cancel للإلغاء"
    )
    context.user_data["awaiting"] = "ai_rewrite"


@check_banned
@check_subscription
async def summarize_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر /summarize"""
    await update.message.reply_text(
        "📋 أرسل النص الذي تريد تلخيصه:\n\n"
        "أو أرسل /cancel للإلغاء"
    )
    context.user_data["awaiting"] = "ai_summarize"


async def ai_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة أزرار الذكاء الاصطناعي"""
    query = update.callback_query
    await query.answer()
    data = query.data

    prompts = {
        "ai_generate": "🤖 أرسل الموضوع الذي تريد توليد منشور عنه:",
        "ai_rewrite": "🔄 أرسل النص الذي تريد إعادة صياغته:",
        "ai_summarize": "📋 أرسل النص الذي تريد تلخيصه:",
        "ai_quiz": "❓ أرسل الموضوع لتوليد اختبار Quiz:",
        "ai_poll": "📊 أرسل الموضوع لتوليد استطلاع Poll:"
    }

    if data in prompts:
        await query.edit_message_text(f"{prompts[data]}\n\nأو أرسل /cancel للإلغاء")
        context.user_data["awaiting"] = data


async def handle_ai_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة مدخلات الذكاء الاصطناعي"""
    awaiting = context.user_data.get("awaiting")
    text = update.message.text.strip()

    if text == "/cancel":
        context.user_data.pop("awaiting", None)
        await update.message.reply_text("❌ تم الإلغاء")
        return

    if awaiting == "ai_generate":
        await _do_generate(update, context, text)
    elif awaiting == "ai_rewrite":
        await _do_rewrite(update, context, text)
    elif awaiting == "ai_summarize":
        await _do_summarize(update, context, text)
    elif awaiting == "ai_quiz":
        await _do_ai_quiz(update, context, text)
    elif awaiting == "ai_poll":
        await _do_ai_poll(update, context, text)

    context.user_data.pop("awaiting", None)


async def _do_generate(update: Update, context: ContextTypes.DEFAULT_TYPE, prompt: str):
    """تنفيذ توليد المنشور"""
    user_id = update.effective_user.id
    msg = await update.message.reply_text("⏳ جاري التوليد بالذكاء الاصطناعي...")

    result = await ai_service.generate_post(prompt)
    if not result:
        await msg.edit_text("❌ فشل التوليد. حاول مجدداً.")
        return

    # حفظ في Queue
    content_data = {"text": result, "parse_mode": None}
    content_hash = generate_content_hash(content_data)

    queue_id = await db.add_to_queue(
        user_id=user_id,
        content_type="text",
        content_data=content_data,
        content_hash=content_hash
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ نشر الآن", callback_data=f"publish_{queue_id}"),
         InlineKeyboardButton("⏰ جدولة", callback_data=f"schedule_{queue_id}")],
        [InlineKeyboardButton("🔄 إعادة توليد", callback_data="ai_regenerate"),
         InlineKeyboardButton("✏️ تعديل", callback_data=f"ai_edit_{queue_id}")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
    ])

    # عرض للمستخدم
    await msg.edit_text(
        f"🤖 <b>المنشور المولّد:</b>\n\n"
        f"{result}\n\n"
        f"{'━' * 30}\n"
        f"🆔 #{queue_id} | تم الحفظ في Queue",
        parse_mode="HTML",
        reply_markup=keyboard
    )

    # حفظ الـ prompt لإعادة التوليد
    context.user_data["last_ai_prompt"] = prompt


async def _do_rewrite(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """تنفيذ إعادة الصياغة"""
    user_id = update.effective_user.id
    msg = await update.message.reply_text("⏳ جاري إعادة الصياغة...")

    result = await ai_service.rewrite_text(text)
    if not result:
        await msg.edit_text("❌ فشلت إعادة الصياغة. حاول مجدداً.")
        return

    content_data = {"text": result, "parse_mode": None}
    content_hash = generate_content_hash(content_data)

    queue_id = await db.add_to_queue(
        user_id=user_id,
        content_type="text",
        content_data=content_data,
        content_hash=content_hash
    )

    await msg.edit_text(
        f"🔄 <b>النص بعد إعادة الصياغة:</b>\n\n"
        f"{result}\n\n"
        f"{'━' * 30}\n"
        f"🆔 #{queue_id} | تم الحفظ في Queue",
        parse_mode="HTML",
        reply_markup=post_action_keyboard(queue_id)
    )


async def _do_summarize(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """تنفيذ التلخيص"""
    user_id = update.effective_user.id
    msg = await update.message.reply_text("⏳ جاري التلخيص...")

    result = await ai_service.summarize_text(text)
    if not result:
        await msg.edit_text("❌ فشل التلخيص. حاول مجدداً.")
        return

    content_data = {"text": result, "parse_mode": None}
    content_hash = generate_content_hash(content_data)

    queue_id = await db.add_to_queue(
        user_id=user_id,
        content_type="text",
        content_data=content_data,
        content_hash=content_hash
    )

    await msg.edit_text(
        f"📋 <b>الملخص:</b>\n\n"
        f"{result}\n\n"
        f"{'━' * 30}\n"
        f"🆔 #{queue_id} | تم الحفظ في Queue",
        parse_mode="HTML",
        reply_markup=post_action_keyboard(queue_id)
    )


async def _do_ai_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE, topic: str):
    """توليد Quiz بالذكاء الاصطناعي"""
    user_id = update.effective_user.id
    msg = await update.message.reply_text("⏳ جاري توليد الاختبار...")

    quiz_data = await ai_service.generate_quiz(topic)
    if not quiz_data:
        await msg.edit_text("❌ فشل توليد الاختبار. حاول مجدداً.")
        return

    question = quiz_data.get("question", "")
    options = quiz_data.get("options", [])
    correct_answer = quiz_data.get("correct_answer", "")
    explanation = quiz_data.get("explanation")

    if correct_answer not in options:
        await msg.edit_text("❌ خطأ في بيانات الاختبار المولّد. حاول مجدداً.")
        return

    correct_option_id = options.index(correct_answer)

    content_data = {
        "question": question,
        "options": options,
        "correct_option_id": correct_option_id,
        "correct_answer": correct_answer,
        "explanation": explanation,
        "is_anonymous": True
    }
    content_hash = generate_content_hash(content_data)

    queue_id = await db.add_to_queue(
        user_id=user_id,
        content_type="quiz",
        content_data=content_data,
        content_hash=content_hash
    )

    options_text = "\n".join(
        [f"  {'✅' if i == correct_option_id else '⬜'} {opt}"
         for i, opt in enumerate(options)]
    )

    await msg.edit_text(
        f"✅ <b>اختبار مولّد بالذكاء الاصطناعي:</b>\n\n"
        f"❓ {question}\n\n"
        f"📋 الخيارات:\n{options_text}\n"
        f"{f'💡 {explanation}' if explanation else ''}\n\n"
        f"{'━' * 30}\n"
        f"🆔 #{queue_id} | تم الحفظ في Queue",
        parse_mode="HTML",
        reply_markup=post_action_keyboard(queue_id)
    )


async def _do_ai_poll(update: Update, context: ContextTypes.DEFAULT_TYPE, topic: str):
    """توليد Poll بالذكاء الاصطناعي"""
    user_id = update.effective_user.id
    msg = await update.message.reply_text("⏳ جاري توليد الاستطلاع...")

    poll_data = await ai_service.generate_poll(topic)
    if not poll_data:
        await msg.edit_text("❌ فشل توليد الاستطلاع. حاول مجدداً.")
        return

    question = poll_data.get("question", "")
    options = poll_data.get("options", [])

    content_data = {
        "question": question,
        "options": options,
        "multiple_answers": False,
        "is_anonymous": True
    }
    content_hash = generate_content_hash(content_data)

    queue_id = await db.add_to_queue(
        user_id=user_id,
        content_type="poll",
        content_data=content_data,
        content_hash=content_hash
    )

    options_text = "\n".join([f"  ⬜ {opt}" for opt in options])

    await msg.edit_text(
        f"✅ <b>استطلاع مولّد بالذكاء الاصطناعي:</b>\n\n"
        f"📊 {question}\n\n"
        f"📋 الخيارات:\n{options_text}\n\n"
        f"{'━' * 30}\n"
        f"🆔 #{queue_id} | تم الحفظ في Queue",
        parse_mode="HTML",
        reply_markup=post_action_keyboard(queue_id)
    )


async def ai_regenerate_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إعادة التوليد"""
    query = update.callback_query
    await query.answer()

    prompt = context.user_data.get("last_ai_prompt")
    if not prompt:
        await query.edit_message_text("❌ لا يوجد موضوع سابق. استخدم /generate")
        return

    await query.edit_message_text("⏳ جاري إعادة التوليد...")
    result = await ai_service.generate_post(prompt)
    if not result:
        await query.edit_message_text("❌ فشل. حاول مجدداً.")
        return

    user_id = query.from_user.id
    content_data = {"text": result, "parse_mode": None}
    content_hash = generate_content_hash(content_data)

    queue_id = await db.add_to_queue(
        user_id=user_id,
        content_type="text",
        content_data=content_data,
        content_hash=content_hash
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ نشر الآن", callback_data=f"publish_{queue_id}"),
         InlineKeyboardButton("⏰ جدولة", callback_data=f"schedule_{queue_id}")],
        [InlineKeyboardButton("🔄 إعادة توليد", callback_data="ai_regenerate")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
    ])

    await query.edit_message_text(
        f"🤖 <b>المنشور المولّد (جديد):</b>\n\n"
        f"{result}\n\n"
        f"{'━' * 30}\n"
        f"🆔 #{queue_id}",
        parse_mode="HTML",
        reply_markup=keyboard
    )


def register_ai_handlers(app):
    """تسجيل handlers الذكاء الاصطناعي"""
    app.add_handler(CommandHandler("generate", generate_command))
    app.add_handler(CommandHandler("rewrite", rewrite_command))
    app.add_handler(CommandHandler("summarize", summarize_command))
    app.add_handler(CallbackQueryHandler(ai_callback, pattern="^ai_(generate|rewrite|summarize|quiz|poll)$"))
    app.add_handler(CallbackQueryHandler(ai_regenerate_callback, pattern="^ai_regenerate$"))