"""
🚀 Handler: Bulk Quiz Addition
هذا الملف مسؤول عن معالجة إضافة مجموعة أسئلة دفعة واحدة من خلال رسالة متعددة الأسطر.
التنسيق المطلوب لكل سطر: /add_quiz الإجابة الصحيحة; نص السؤال; خيار 1; خيار 2; ...
"""

from aiogram import types
from aiogram.dispatcher import Dispatcher
from database import db  # استيراد كائن قاعدة البيانات الأصلي
import logging

# إعداد السجلات لمراقبة العمليات
logger = logging.getLogger(__name__)

async def handle_bulk_quiz(message: types.Message):
    """
    يعالج الرسائل التي تحتوي على أوامر /add_quiz متعددة.
    """
    # 1. تقسيم الرسالة إلى أسطر وتنظيف الفراغات
    lines = [line.strip() for line in message.text.strip().split('\n') if line.strip()]
    
    success_count = 0
    fail_count = 0
    error_details = []

    # التحقق من أن المستخدم ليس محظوراً (اختياري - يعتمد على وجود الدالة في البوت)
    user_id = message.from_user.id
    
    for index, line in enumerate(lines, start=1):
        # التأكد من أن السطر يبدأ بالأمر الصحيح
        if not line.lower().startswith('/add_quiz'):
            continue

        try:
            # استخراج البيانات بعد الأمر /add_quiz
            # نستخدم maxsplit=1 لضمان عدم تقسيم الأمر نفسه
            raw_data = line.split(maxsplit=1)
            if len(raw_data) < 2:
                raise ValueError("السطر فارغ بعد الأمر")

            content = raw_data[1]
            
            # تقسيم المحتوى باستخدام الفاصلة المنقوطة ;
            parts = [p.strip() for p in content.split(';')]

            # التحقق من الحد الأدنى للبيانات (إجابة + سؤال + خيارين)
            if len(parts) < 4:
                raise ValueError("تنسيق ناقص. المطلوب: إجابة;سؤال;خيار1;خيار2")

            correct_answer = parts[0]
            question_text = parts[1]
            options = parts[2:]

            # التحقق من قيود تيليجرام (عدد الخيارات بين 2 و 10)
            if not (2 <= len(options) <= 10):
                raise ValueError(f"عدد الخيارات غير مسموح ({len(options)})")

            # التحقق من وجود الإجابة الصحيحة ضمن قائمة الخيارات
            if correct_answer not in options:
                raise ValueError(f"الإجابة الصحيحة '{correct_answer}' غير موجودة في الخيارات")

            # تجهيز قاموس البيانات بتنسيق JSON (كما يتطلبه ملف database.py الخاص بك)
            quiz_data = {
                "question": question_text,
                "options": options,
                "correct_option_id": options.index(correct_answer),  # تحويل النص لرقم الترتيب
                "type": "quiz"
            }

            # إضافة الكويز إلى الطابور (Queue)
            # دالة add_to_queue في ملفك تعيد ID الصف إذا نجحت
            queue_id = await db.add_to_queue(
                user_id=user_id,
                content_type="quiz",
                content_data=quiz_data,
                priority=0  # أولوية عادية
            )

            if queue_id:
                success_count += 1
            else:
                raise Exception("خطأ أثناء الحفظ في قاعدة البيانات")

        except Exception as e:
            fail_count += 1
            error_details.append(f"السطر {index}: {str(e)}")
            logger.error(f"Error in bulk quiz line {index}: {e}")

    # 2. إرسال تقرير نهائي للمستخدم
    if success_count > 0 or fail_count > 0:
        report = (
            f"📊 **تقرير معالجة الأسئلة الجماعية**\n"
            f"━━━━━━━━━━━━━━━\n"
            f"✅ تم الإضافة للطابور: `{success_count}`\n"
            f"❌ فشل المعالجة: `{fail_count}`\n"
        )

        if error_details:
            report += "\n⚠️ **أمثلة على الأخطاء:**\n"
            # عرض أول 3 أخطاء فقط لتجنب طول الرسالة
            for err in error_details[:3]:
                report += f"• {err}\n"
        
        await message.reply(report, parse_mode="Markdown")

def register_bulk_quiz_handlers(dp: Dispatcher):
    """
    تسجيل الهاندلر في البوت.
    يستهدف الرسائل التي تبدأ بـ /add_quiz وتحتوي على أكثر من سطر.
    """
    dp.register_message_handler(
        handle_bulk_quiz,
        lambda m: m.text and m.text.strip().startswith('/add_quiz') and '\n' in m.text
    )
