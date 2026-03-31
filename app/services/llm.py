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

        prompt = f"""
You are an expert TikTok/Shorts video editor. Analyze this video transcript.
The transcript includes timestamps in seconds [start - end] or in SRT format.

Your task is to find the 3 most viral, engaging, and standalone moments suitable for short-form video.
RULES:
1. Each clip MUST be between 30 and 60 seconds long.
2. A good clip has a hook (interesting start), builds tension, and has a satisfying conclusion.
3. The start and end timestamps MUST match exactly with the timestamps provided in the text. Do not invent or guess times!
4. Return ONLY a raw JSON array. No markdown, no text before or after.

FORMAT:
[
  {{"start": 12.5, "end": 45.0, "title": "Catchy Hook Title", "reason": "Why this goes viral"}}
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
                
                # Очистка JSON
                clean_json = content.replace("```json", "").replace("```", "").strip()
                start_idx = clean_json.find("[")
                end_idx = clean_json.rfind("]") + 1
                
                if start_idx != -1 and end_idx != -1:
                    clean_json = clean_json[start_idx:end_idx]
                    return json.loads(clean_json)[:5]
                
                return []
        except Exception as e:
            logger.error(f"❌ Ошибка LLM: {str(e)}")
            return []