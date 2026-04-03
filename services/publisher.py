"""
📡 Publisher Service - خدمة النشر في القنوات
يدعم جميع أنواع المحتوى: نص، صورة، فيديو، صوت، ملف، Quiz، Poll
"""

import json
import logging
from telegram import Bot
from telegram.constants import ParseMode
from database import db

logger = logging.getLogger(__name__)


class Publisher:
    """خدمة النشر الرئيسية"""

    def __init__(self, bot: Bot):
        self.bot = bot

    async def publish_item(self, queue_item: dict, channel_ids: list = None) -> dict:
        """
        نشر عنصر من الـ Queue إلى القنوات المحددة
        Returns: {"success": [...], "failed": [...]}
        """
        user_id = queue_item["user_id"]
        content_type = queue_item["content_type"]
        content_data = queue_item["content_data"]
        if isinstance(content_data, str):
            content_data = json.loads(content_data)
        queue_id = queue_item["id"]

        # تحديد القنوات المستهدفة
        if channel_ids:
            target_channels = channel_ids
        elif queue_item.get("target_channels"):
            tc = queue_item["target_channels"]
            if isinstance(tc, str):
                tc = json.loads(tc)
            target_channels = tc
        else:
            # كل قنوات المستخدم
            channels = await db.get_user_channels(user_id)
            target_channels = [ch["channel_id"] for ch in channels]

        if not target_channels:
            return {"success": [], "failed": [{"error": "لا توجد قنوات"}]}

        results = {"success": [], "failed": []}

        for ch_id in target_channels:
            try:
                await self._send_to_channel(ch_id, content_type, content_data)
                results["success"].append(ch_id)
                await db.add_publish_log(
                    user_id, queue_id, ch_id, content_type, "success"
                )
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Failed to publish to {ch_id}: {error_msg}")
                results["failed"].append({"channel_id": ch_id, "error": error_msg})
                await db.add_publish_log(
                    user_id, queue_id, ch_id, content_type, "failed", error_msg
                )

        # تحديث حالة العنصر
        if results["success"]:
            await db.mark_as_published(queue_id)
            await db.increment_post_count(user_id)
        elif results["failed"]:
            await db.mark_as_failed(queue_id, results["failed"][0].get("error"))

        return results

    async def _send_to_channel(self, channel_id: int, content_type: str,
                                data: dict):
        """إرسال محتوى إلى قناة محددة"""

        if content_type == "text":
            await self.bot.send_message(
                chat_id=channel_id,
                text=data["text"],
                parse_mode=ParseMode.HTML if data.get("parse_mode") == "HTML"
                    else ParseMode.MARKDOWN_V2 if data.get("parse_mode") == "MARKDOWN"
                    else None,
                disable_web_page_preview=data.get("disable_preview", False)
            )

        elif content_type == "photo":
            await self.bot.send_photo(
                chat_id=channel_id,
                photo=data["file_id"],
                caption=data.get("caption"),
                parse_mode=ParseMode.HTML if data.get("parse_mode") == "HTML" else None
            )

        elif content_type == "video":
            await self.bot.send_video(
                chat_id=channel_id,
                video=data["file_id"],
                caption=data.get("caption"),
                parse_mode=ParseMode.HTML if data.get("parse_mode") == "HTML" else None
            )

        elif content_type == "audio":
            await self.bot.send_audio(
                chat_id=channel_id,
                audio=data["file_id"],
                caption=data.get("caption"),
                parse_mode=ParseMode.HTML if data.get("parse_mode") == "HTML" else None
            )

        elif content_type == "document":
            await self.bot.send_document(
                chat_id=channel_id,
                document=data["file_id"],
                caption=data.get("caption"),
                parse_mode=ParseMode.HTML if data.get("parse_mode") == "HTML" else None
            )

        elif content_type == "quiz":
            options = data["options"]
            correct_idx = data["correct_option_id"]
            await self.bot.send_poll(
                chat_id=channel_id,
                question=data["question"],
                options=options,
                type="quiz",
                correct_option_id=correct_idx,
                explanation=data.get("explanation"),
                is_anonymous=data.get("is_anonymous", True)
            )

        elif content_type == "poll":
            await self.bot.send_poll(
                chat_id=channel_id,
                question=data["question"],
                options=data["options"],
                type="regular",
                allows_multiple_answers=data.get("multiple_answers", False),
                is_anonymous=data.get("is_anonymous", True)
            )

        else:
            raise ValueError(f"Unsupported content type: {content_type}")
