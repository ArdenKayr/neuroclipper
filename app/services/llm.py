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
        if not self.api_key:
            logger.error("❌ OPENROUTER_API_KEY не задан!")
            return []

        # Ограничиваем транскрипт, чтобы не превысить лимиты контекста
        truncated_transcript = transcript[:40000]

        prompt = f"""
Ты — эксперт по виральности. Проанализируй текст и выдели 5 лучших моментов для Shorts (по 30-60 сек).
Верни ответ СТРОГО в формате JSON списка объектов без лишнего текста.

ТРАНСКРИПТ:
{truncated_transcript}

ФОРМАТ ОТВЕТА:
[
  {{"start": 10.5, "end": 45.0, "title": "Интригующее название", "reason": "Почему это круто"}}
]
"""
        try:
            async with httpx.AsyncClient(timeout=90.0) as client:
                payload = {
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3
                }
                response = await client.post(self.url, json=payload, headers=self.headers)
                response.raise_for_status()
                
                content = response.json()['choices'][0]['message']['content']
                # Очистка текста от возможных пояснений модели
                clean_json = content.replace("```json", "").replace("```", "").strip()
                
                # Ищем начало и конец массива, если модель добавила лишний текст
                start_idx = clean_json.find("[")
                end_idx = clean_json.rfind("]") + 1
                if start_idx != -1 and end_idx != -1:
                    clean_json = clean_json[start_idx:end_idx]

                highlights = json.loads(clean_json)
                logger.info(f"--- [🧠] Claude успешно выделил {len(highlights)} хайлайтов.")
                return highlights[:5]
        except Exception as e:
            logger.error(f"❌ Ошибка LLM анализа (400 или JSON): {e}")
            return []