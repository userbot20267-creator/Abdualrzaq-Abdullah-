"""
🤖 AI Service - خدمة الذكاء الاصطناعي عبر OpenRouter
"""

import aiohttp
import json
import logging
from config import config

logger = logging.getLogger(__name__)


class AIService:
    """خدمة OpenRouter للذكاء الاصطناعي"""

    def __init__(self):
        self.api_key = config.OPENROUTER_API_KEY
        self.base_url = config.OPENROUTER_BASE_URL
        self.model = config.AI_MODEL

    async def _request(self, messages: list, max_tokens: int = 2000) -> str:
        """إرسال طلب لـ OpenRouter"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://telegram-bot.app",
            "X-Title": "Telegram AI Bot"
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.7
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data["choices"][0]["message"]["content"]
                    else:
                        error = await response.text()
                        logger.error(f"AI API Error {response.status}: {error}")
                        return None
        except Exception as e:
            logger.error(f"AI Request Error: {e}")
            return None

    async def generate_post(self, prompt: str, style: str = None) -> str:
        """توليد منشور"""
        system = (
            "أنت كاتب محتوى محترف لقنوات تليجرام. "
            "اكتب منشوراً جذاباً ومنسقاً بالإيموجي. "
            "اجعل المنشور مختصراً وقوياً."
        )
        if style:
            system += f"\nالأسلوب المطلوب: {style}"

        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": f"اكتب منشوراً عن: {prompt}"}
        ]
        return await self._request(messages)

    async def rewrite_text(self, text: str) -> str:
        """إعادة صياغة نص"""
        messages = [
            {"role": "system", "content":
                "أعد صياغة النص التالي بأسلوب جديد ومحسّن مع الحفاظ على المعنى. "
                "استخدم إيموجي مناسبة وتنسيق جذاب."},
            {"role": "user", "content": text}
        ]
        return await self._request(messages)

    async def summarize_text(self, text: str) -> str:
        """تلخيص نص"""
        messages = [
            {"role": "system", "content":
                "لخّص النص التالي بشكل مختصر ومفيد مع الحفاظ على النقاط الرئيسية."},
            {"role": "user", "content": text}
        ]
        return await self._request(messages)

    async def generate_quiz(self, topic: str) -> dict:
        """توليد اختبار Quiz"""
        messages = [
            {"role": "system", "content":
                "أنشئ سؤال اختبار (Quiz) عن الموضوع المحدد. "
                "أرجع النتيجة بصيغة JSON فقط بدون أي نص إضافي:\n"
                '{"question": "نص السؤال", "options": ["خيار1", "خيار2", "خيار3", "خيار4"], '
                '"correct_answer": "الإجابة الصحيحة", "explanation": "شرح مختصر"}'},
            {"role": "user", "content": f"الموضوع: {topic}"}
        ]
        result = await self._request(messages)
        if result:
            try:
                # تنظيف النص من markdown
                cleaned = result.strip()
                if cleaned.startswith("```"):
                    cleaned = cleaned.split("\n", 1)[1]
                    cleaned = cleaned.rsplit("```", 1)[0]
                return json.loads(cleaned)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse quiz JSON: {result}")
                return None
        return None

    async def generate_poll(self, topic: str) -> dict:
        """توليد استطلاع Poll"""
        messages = [
            {"role": "system", "content":
                "أنشئ سؤال استطلاع رأي عن الموضوع المحدد. "
                "أرجع النتيجة بصيغة JSON فقط بدون أي نص إضافي:\n"
                '{"question": "نص السؤال", "options": ["خيار1", "خيار2", "خيار3", "خيار4"]}'},
            {"role": "user", "content": f"الموضوع: {topic}"}
        ]
        result = await self._request(messages)
        if result:
            try:
                cleaned = result.strip()
                if cleaned.startswith("```"):
                    cleaned = cleaned.split("\n", 1)[1]
                    cleaned = cleaned.rsplit("```", 1)[0]
                return json.loads(cleaned)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse poll JSON: {result}")
                return None
        return None


# Singleton instance
ai_service = AIService()