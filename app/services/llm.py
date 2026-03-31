import logging
import json
import httpx
import re
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
            
        if not transcript or len(transcript.strip()) < 50:
            logger.error("❌ Текст слишком короткий или пустой! LLM нечего анализировать.")
            return []

        prompt = f"""
You are an expert TikTok/Shorts video editor. Analyze this video transcript.
The transcript includes timestamps in seconds [start - end].

Your task is to find the 3 most viral, engaging, and standalone moments suitable for short-form video.
RULES:
1. Each clip MUST be between 30 and 60 seconds long.
2. The start and end timestamps MUST match exactly with the timestamps provided in the text.
3. Return ONLY a raw JSON array. No markdown, no intro text.

FORMAT:
[
  {{"start": 12.5, "end": 45.0, "title": "Catchy Title", "reason": "Why"}}
]

TRANSCRIPT:
{transcript[:30000]}
"""
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                payload = {
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.2
                }
                response = await client.post(self.url, json=payload, headers=self.headers)
                
                if response.status_code != 200:
                    logger.error(f"❌ OpenRouter Error ({response.status_code}): {response.text}")
                    return []
                
                data = response.json()
                content = data['choices'][0]['message']['content']
                
                # 🔥 Логируем сырой ответ, чтобы понять, что не так
                logger.info(f"--- [🤖] Ответ от нейросети: {content[:300]}...")
                
                # Пуленепробиваемый поиск массива JSON в тексте
                match = re.search(r'\[.*\]', content, re.DOTALL)
                if match:
                    clean_json = match.group(0)
                    try:
                        parsed = json.loads(clean_json)
                        return parsed[:3]
                    except json.JSONDecodeError as je:
                        logger.error(f"❌ Ошибка парсинга JSON от LLM: {je}\nСырой кусок: {clean_json}")
                        return []
                else:
                    logger.error("❌ LLM не вернула массив [...] вообще.")
                    return []
                    
        except Exception as e:
            logger.error(f"❌ Ошибка LLM-сервиса: {str(e)}")
            return []