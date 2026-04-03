"""
🔧 Helpers - دوال مساعدة عامة
"""

import hashlib
import json
from datetime import datetime
import pytz


def generate_content_hash(content_data: dict) -> str:
    """توليد hash فريد للمحتوى لمنع التكرار"""
    raw = json.dumps(content_data, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()


def parse_datetime_with_tz(date_str: str, time_str: str,
                            timezone: str = "Asia/Riyadh") -> datetime:
    """تحويل تاريخ ووقت نصي إلى datetime مع timezone"""
    try:
        tz = pytz.timezone(timezone)
        dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        return tz.localize(dt).astimezone(pytz.utc)
    except Exception:
        return None


def parse_time_only(time_str: str, timezone: str = "Asia/Riyadh") -> datetime:
    """تحويل وقت فقط إلى datetime اليوم"""
    try:
        tz = pytz.timezone(timezone)
        now = datetime.now(tz)
        hour, minute = map(int, time_str.strip().split(":"))
        dt = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if dt < now:
            from datetime import timedelta
            dt += timedelta(days=1)
        return dt.astimezone(pytz.utc)
    except Exception:
        return None


def format_queue_item(item: dict) -> str:
    """تنسيق عنصر من الـ Queue لعرضه"""
    content_type = item["content_type"]
    data = item["content_data"] if isinstance(item["content_data"], dict) \
        else json.loads(item["content_data"])
    status = item["status"]
    scheduled = item.get("scheduled_at")

    type_emoji = {
        "text": "📝", "photo": "🖼️", "video": "🎬",
        "audio": "🎵", "document": "📎", "quiz": "❓", "poll": "📊"
    }
    emoji = type_emoji.get(content_type, "📌")

    text = f"{emoji} #{item['id']} | {content_type.upper()}"
    if status == "pending":
        text += " | ⏳ بانتظار النشر"
    elif status == "published":
        text += " | ✅ تم النشر"
    elif status == "failed":
        text += " | ❌ فشل"

    if scheduled:
        text += f"\n⏰ مجدول: {scheduled.strftime('%Y-%m-%d %H:%M')}"

    # عرض مقتطف من المحتوى
    if content_type == "text":
        preview = data.get("text", "")[:80]
        text += f"\n💬 {preview}..."
    elif content_type == "quiz":
        text += f"\n❓ {data.get('question', '')[:60]}..."
    elif content_type == "poll":
        text += f"\n📊 {data.get('question', '')[:60]}..."
    elif content_type in ("photo", "video", "audio", "document"):
        caption = data.get("caption", "")
        if caption:
            text += f"\n💬 {caption[:60]}..."

    return text


def truncate_text(text: str, max_length: int = 4096) -> str:
    """اقتطاع النص إذا تجاوز الحد"""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."