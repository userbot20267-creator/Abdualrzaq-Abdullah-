"""
❓ Quiz & Poll Handler - نظام الاختبارات والاستطلاعات
"""

import json
import logging
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from database import db
from utils.helpers import generate_content_hash
from utils.keyboards import post_action_keyboard
from utils.decorators import check_banned, check_subscription

logger = logging.getLogger(__name__)


@check_banned
@check_subscription
async def add_quiz_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    أمر /add_quiz
    الصيغة: /add_quiz الإجابة الصحيحة; السؤال; الخيار1; الخيار2; الخيار3; الخيار4
    """
    user_id = update.effective_user.id
    full_text = update.message.text

    # حذف الأمر /add_quiz
    raw = full_text.replace("/add_quiz", "", 1).strip()

    if not raw:
        await update.message.reply_text(
            "❓ <b>صيغة إضافة اختبار Quiz:</b>\n\n"
            "<code>/add_quiz الإجابة الصحيحة; السؤال; الخيار1; الخيار2; الخيار3; الخيار4</code>\n\n"
            "📌 <b>القواعد:</b>\n"
            "• العنصر الأول: الإجابة الصحيحة\n"
            "• العنصر الثاني: نص السؤال\n"
            "• باقي العناصر: الخيارات (2 إلى 10)\n"
            "• الإجابة الصحيحة يجب أن تكون ضمن الخيارات\n"
            "• الفاصل بين العناصر: فاصلة منقوطة ;\n\n"
            "📝 <b>مثال:</b>\n"
            "<code>/add_quiz باريس; ما هي عاصمة فرنسا؟; لندن; باريس; برلين; مدريد</code>",
            parse_mode="HTML"
        )
        return

    # تقسيم النص بالفاصلة المنقوطة
    parts = [p.strip() for p in raw.split(";")]

    # إزالة العناصر الفارغة
    parts = [p for p in parts if p]

    # التحقق: على الأقل 4 عناصر (إجابة + سؤال + خيارين)
    if len(parts) < 4:
        await update.message.reply_text(
            "❌ <b>خطأ:</b> يجب أن يكون هناك على الأقل 4 عناصر:\n"
            "إجابة صحيحة + سؤال + خيارين على الأقل\n\n"
            f"أنت أرسلت {len(parts)} عناصر فقط.",
            parse_mode="HTML"
        )
        return

    # استخراج البيانات
    correct_answer = parts[0].strip()
    question = parts[1].strip()
    options = [p.strip() for p in parts[2:]]

    # التحقق: عدد الخيارات بين 2 و 10
    if len(options) < 2:
        await update.message.reply_text(
            "❌ يجب أن يكون هناك خيارين على الأقل!"
        )
        return

    if len(options) > 10:
        await update.message.reply_text(
            "❌ الحد الأقصى للخيارات هو 10!"
        )
        return

    # التحقق: الإجابة الصحيحة موجودة ضمن الخيارات
    if correct_answer not in options:
        await update.message.reply_text(
            f"❌ <b>خطأ:</b> الإجابة الصحيحة «{correct_answer}» غير موجودة ضمن الخيارات!\n\n"
            f"📋 الخيارات المتاحة:\n" +
            "\n".join([f"  • {opt}" for opt in options]),
            parse_mode="HTML"
        )
        return

    # التحقق: عدم تكرار الإجابة الصحيحة في الخيارات
    count = options.count(correct_answer)
    if count > 1:
        await update.message.reply_text(
            f"❌ <b>خطأ:</b> الإجابة الصحيحة «{correct_answer}» مكررة {count} مرات في الخيارات!\n"
            "يجب أن تظهر مرة واحدة فقط.",
            parse_mode="HTML"
        )
        return

    # التحقق من عدم تكرار أي خيار
    if len(options) != len(set(options)):
        await update.message.reply_text(
            "❌ <b>خطأ:</b> توجد خيارات مكررة! كل خيار يجب أن يكون فريداً.",
            parse_mode="HTML"
        )
        return

    # تحديد index الإجابة الصحيحة
    correct_option_id = options.index(correct_answer)

    # بناء بيانات المحتوى
    content_data = {
        "question": question,
        "options": options,
        "correct_option_id": correct_option_id,
        "correct_answer": correct_answer,
        "explanation": None,
        "is_anonymous": True
    }
    content_hash = generate_content_hash(content_data)

    # إضافة للـ Queue
    queue_id = await db.add_to_queue(
        user_id=user_id,
        content_type="quiz",
        content_data=content_data,
        content_hash=content_hash
    )

    if queue_id == -1:
        await update.message.reply_text("⚠️ هذا الاختبار موجود مسبقاً في الـ Queue!")
        return

    # عرض ملخص
    options_text = "\n".join(
        [f"  {'✅' if i == correct_option_id else '⬜'} {opt}"
         for i, opt in enumerate(options)]
    )

    await update.message.reply_text(
        f"✅ <b>تم إضافة الاختبار للـ Queue!</b>\n\n"
        f"🆔 #{queue_id}\n"
        f"❓ <b>السؤال:</b> {question}\n\n"
        f"📋 <b>الخيارات:</b>\n{options_text}\n\n"
        f"✅ <b>الإجابة الصحيحة:</b> {correct_answer}",
        parse_mode="HTML",
        reply_markup=post_action_keyboard(queue_id)
    )


@check_banned
@check_subscription
async def add_poll_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    أمر /add_poll
    الصيغة: /add_poll السؤال; الخيار1; الخيار2; الخيار3
    """
    user_id = update.effective_user.id
    full_text = update.message.text

    raw = full_text.replace("/add_poll", "", 1).strip()

    if not raw:
        await update.message.reply_text(
            "📊 <b>صيغة إضافة استطلاع Poll:</b>\n\n"
            "<code>/add_poll السؤال; الخيار1; الخيار2; الخيار3; الخيار4</code>\n\n"
            "📌 <b>القواعد:</b>\n"
            "• العنصر الأول: نص السؤال\n"
            "• باقي العناصر: الخيارات (2 إلى 10)\n"
            "• الفاصل: فاصلة منقوطة ;\n\n"
            "📝 <b>مثال:</b>\n"
            "<code>/add_poll ما هو لونك المفضل؟; أحمر; أزرق; أخضر; أصفر</code>",
            parse_mode="HTML"
        )
        return

    parts = [p.strip() for p in raw.split(";")]
    parts = [p for p in parts if p]

    # التحقق: على الأقل 3 عناصر (سؤال + خيارين)
    if len(parts) < 3:
        await update.message.reply_text(
            "❌ يجب أن يكون هناك سؤال + خيارين على الأقل!"
        )
        return

    question = parts[0].strip()
    options = [p.strip() for p in parts[1:]]

    if len(options) < 2:
        await update.message.reply_text("❌ يجب أن يكون هناك خيارين على الأقل!")
        return

    if len(options) > 10:
        await update.message.reply_text("❌ الحد الأقصى للخيارات هو 10!")
        return

    # التحقق من عدم التكرار
    if len(options) != len(set(options)):
        await update.message.reply_text(
            "❌ توجد خيارات مكررة! كل خيار يجب أن يكون فريداً."
        )
        return

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

    if queue_id == -1:
        await update.message.reply_text("⚠️ هذا الاستطلاع موجود مسبقاً!")
        return

    options_text = "\n".join([f"  ⬜ {opt}" for opt in options])

    await update.message.reply_text(
        f"✅ <b>تم إضافة الاستطلاع للـ Queue!</b>\n\n"
        f"🆔 #{queue_id}\n"
        f"📊 <b>السؤال:</b> {question}\n\n"
        f"📋 <b>الخيارات:</b>\n{options_text}",
        parse_mode="HTML",
        reply_markup=post_action_keyboard(queue_id)
    )


def register_quiz_poll_handlers(app):
    """تسجيل handlers الاختبارات والاستطلاعات"""
    app.add_handler(CommandHandler("add_quiz", add_quiz_command))
    app.add_handler(CommandHandler("add_poll", add_poll_command))