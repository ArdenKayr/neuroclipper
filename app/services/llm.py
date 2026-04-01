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

Your task is to find the 3 most viral, engaging, and standalone moments.
CRITICAL RULES FOR CONTEXT AND TIMESTAMPS:
1. CONTEXT IS EVERYTHING: The clip MUST be a complete, standalone thought. If the speaker says "Because of this..." or "He did it...", you MUST step back and include the previous sentences that explain what "this" or who "he" is. Never start mid-thought.
2. DO NOT CUT WORDS: To prove you are not cutting mid-sentence, you MUST provide the "start_quote" (first 5 words of your clip) and "end_quote" (last 5 words of your clip).
3. The start and end timestamps MUST match exactly with the timestamps provided in the text for those exact quotes.
4. Length: 30 to 60 seconds.
5. "title" and "reason" MUST be in Russian.
6. "b_roll_query" MUST be a 1-2 word search term in English for a background stock video that visually matches the core topic of the clip (e.g. "money falling", "sad man", "business meeting", "fast car").

FORMAT:
[
  {{
    "start": 12.5, 
    "end": 45.0, 
    "start_quote": "The exact first five words",
    "end_quote": "The exact last five words",
    "title": "Название на русском", 
    "reason": "Почему этот момент станет виральным",
    "b_roll_query": "english search term"
  }}
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
                
                logger.info(f"--- [🤖] Ответ от нейросети: {content[:300]}...")
                
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

    async def translate_to_english(self, russian_text: str) -> str:
        prompt = f"Translate the following text to natural, engaging English suitable for a TikTok/Shorts video voiceover. Do not output anything other than the translated text itself. No intros, no quotes.\n\nText: {russian_text}"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                payload = {
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3
                }
                response = await client.post(self.url, json=payload, headers=self.headers)
                if response.status_code == 200:
                    return response.json()['choices'][0]['message']['content'].strip()
                return ""
        except Exception as e:
            logger.error(f"❌ Ошибка перевода: {e}")
            return ""