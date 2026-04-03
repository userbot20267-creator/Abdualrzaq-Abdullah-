"""
🔐 Subscription Service - نظام الاشتراك الإجباري
"""

import logging
from telegram import Bot, ChatMember
from config import config

logger = logging.getLogger(__name__)


async def check_user_subscription(bot: Bot, user_id: int) -> tuple:
    """
    التحقق من اشتراك المستخدم في جميع القنوات الإجبارية
    Returns: (is_subscribed: bool, missing_channels: list)
    """
    if not config.FORCED_CHANNELS:
        return True, []

    missing = []
    for channel_id in config.FORCED_CHANNELS:
        if not channel_id:
            continue
        try:
            channel_id_int = int(channel_id)
            member = await bot.get_chat_member(channel_id_int, user_id)
            if member.status in [
                ChatMember.LEFT, ChatMember.BANNED, ChatMember.RESTRICTED
            ]:
                try:
                    chat_info = await bot.get_chat(channel_id_int)
                except Exception:
                    chat_info = None
                missing.append({"id": channel_id, "info": chat_info})
        except Exception as e:
            logger.error(f"Error checking subscription for {channel_id}: {e}")

    return len(missing) == 0, missing