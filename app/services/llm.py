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
            "Content-Type": "application/json"
        }

    async def find_highlights(self, transcript: str) -> List[Dict[str, Any]]:
        if not self.api_key:
            logger.error("❌ OPENROUTER_API_KEY не задан!")
            return []

        # Ограничиваем транскрипт для стабильности
        text_chunk = transcript[:30000]

        prompt = f"""
Analyze this transcript and find 5 viral moments (30-60 sec each).
Return ONLY a raw JSON array of objects.

TRANSCRIPT:
{text_chunk}

JSON FORMAT:
[
  {{"start": 10.0, "end": 45.0, "title": "Moment Title", "reason": "Why"}}
]
"""
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                payload = {
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}]
                }
                response = await client.post(self.url, json=payload, headers=self.headers)
                
                if response.status_code != 200:
                    logger.error(f"❌ OpenRouter Error ({response.status_code}): {response.text}")
                    return []
                
                content = response.json()['choices'][0]['message']['content']
                # Очистка JSON
                clean_json = content.replace("```json", "").replace("```", "").strip()
                
                start_idx = clean_json.find("[")
                end_idx = clean_json.rfind("]") + 1
                if start_idx != -1 and end_idx != -1:
                    clean_json = clean_json[start_idx:end_idx]

                return json.loads(clean_json)[:5]
        except Exception as e:
            logger.error(f"❌ Ошибка LLM: {e}")
            return []