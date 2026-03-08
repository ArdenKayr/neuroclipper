import logging
import json
import httpx
from core.config import settings
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class SmartLLMService:
    def __init__(self):
        self.api_key = settings.OPENROUTER_API_KEY
        self.model = settings.OPENROUTER_MODEL
        self.url = "https://openrouter.ai/api/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://neuroclipper.ai",
            "Content-Type": "application/json"
        }

    async def find_highlights(self, transcript: str) -> List[Dict[str, Any]]:
        """
        Анализирует текст и находит 5 виральных хайлайтов.
        """
        if not self.api_key:
            logger.error("❌ OPENROUTER_API_KEY не задан!")
            return []

        prompt = f"""
Ты — эксперт по виральному контенту (TikTok, Reels, Shorts). 
Проанализируй транскрипт видео и выдели 5 самых захватывающих моментов.

ПРАВИЛА:
1. Длительность каждого момента: 30-60 секунд.
2. Каждый момент должен иметь "хук" (захватывающее начало).
3. Ответ должен быть СТРОГО в формате JSON списка объектов.

ТРАНСКРИПТ:
{transcript[:40000]}

ФОРМАТ JSON:
[
  {{"start": 10.5, "end": 45.0, "title": "Название момента", "reason": "Почему это вирально"}},
  ...
]
"""
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                payload = {
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}]
                }
                response = await client.post(self.url, json=payload, headers=self.headers)
                response.raise_for_status()
                
                content = response.json()['choices'][0]['message']['content']
                # Очистка от markdown-мусора, если LLM его добавит
                content = content.replace("```json", "").replace("```", "").strip()
                
                highlights = json.loads(content)
                logger.info(f"--- [🧠] Claude нашел {len(highlights)} моментов.")
                return highlights
        except Exception as e:
            logger.error(f"❌ Ошибка LLM анализа: {e}")
            return []