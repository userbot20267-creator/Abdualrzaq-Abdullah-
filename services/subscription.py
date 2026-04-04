"""
🔐 Subscription Service - نظام الاشتراك الإجباري المطور
يتحقق من القنوات الموجودة في Config والقنوات المضافة عبر قاعدة البيانات.
"""

import logging
from telegram import Bot, ChatMember
from config import config
from database import db  # ➕ إضافة: استيراد قاعدة البيانات للتحقق من القنوات الجديدة

logger = logging.getLogger(__name__)


async def check_user_subscription(bot: Bot, user_id: int) -> tuple:
    """
    التحقق من اشتراك المستخدم في جميع القنوات الإجبارية (الثابتة والمضافة)
    Returns: (is_subscribed: bool, missing_channels: list)
    """
    
    # 1. جلب القنوات الثابتة من ملف config.py (نفس منطقك القديم)
    forced_channels = list(config.FORCED_CHANNELS) if config.FORCED_CHANNELS else []

    # 2. ➕ إضافة: جلب القناة الإضافية التي أضفتها أنت عبر البوت (المخزنة في template)
    try:
        # نتحقق مما إذا كان هناك ID قناة مخزن للمالك في قاعدة البيانات
        owner_settings = await db.get_auto_publish_settings(config.OWNER_ID)
        extra_channel = owner_settings.get("template")
        
        # إذا وجدت قناة تبدأ بـ -100 وغير موجودة في القائمة، أضفها
        if extra_channel and str(extra_channel).startswith("-100"):
            if str(extra_channel) not in [str(c) for c in forced_channels]:
                forced_channels.append(extra_channel)
                logger.info(f"🔍 Added extra channel from DB to check: {extra_channel}")
    except Exception as e:
        # في حال عدم وجود إعدادات للمالك بعد، يتخطى الخطوة بهدوء
        logger.debug(f"No dynamic forced channels found: {e}")

    # إذا لم تكن هناك أي قنوات (لا في config ولا في DB)
    if not forced_channels:
        return True, []

    missing = []
    # 3. فحص الاشتراك (نفس منطقك القديم تماماً)
    for channel_id in forced_channels:
        if not channel_id:
            continue
        try:
            channel_id_int = int(channel_id)
            member = await bot.get_chat_member(channel_id_int, user_id)
            
            # التحقق من الحالات التي تمنع المستخدم من المتابعة
            if member.status in [
                ChatMember.LEFT, ChatMember.BANNED, ChatMember.RESTRICTED
            ]:
                try:
                    chat_info = await bot.get_chat(channel_id_int)
                except Exception:
                    chat_info = None
                
                # إضافة القناة الناقصة للقائمة ليتم تنبيه المستخدم
                missing.append({"id": str(channel_id), "info": chat_info})
                
        except Exception as e:
            logger.error(f"Error checking subscription for {channel_id}: {e}")

    # يعيد True إذا كانت القائمة فارغة (أي أن المستخدم مشترك في الكل)
    return len(missing) == 0, missing
    
