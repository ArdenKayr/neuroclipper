import logging
import httpx
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from core.config import settings
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class VizardService:
    def __init__(self):
        self.api_key = settings.VIZARD_API_KEY
        # Проверь в документации Vizard, не изменился ли базовый URL для твоего тарифа
        self.base_url = "https://api.vizard.ai/v1" 
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(httpx.HTTPError),
        reraise=True
    )
    async def request_analysis(self, video_url: str) -> str:
        """
        Отправляет URL видео в Vizard для генерации хайлайтов.
        """
        if not self.api_key:
            raise ValueError("VIZARD_API_KEY не задан.")

        async with httpx.AsyncClient(timeout=30.0) as client:
            payload = {
                "input_url": video_url,
                "auto_clip": True,
                "aspect_ratio": "9:16"
            }
            # Попробуем основной эндпоинт создания проекта
            response = await client.post(f"{self.base_url}/projects", json=payload, headers=self.headers)
            
            if response.status_code == 404:
                logger.error(f"❌ Vizard API вернул 404. Проверь эндпоинт или API Key. Ответ: {response.text}")
                raise httpx.HTTPStatusError("API Endpoint not found", request=response.request, response=response)
                
            response.raise_for_status()
            data = response.json()
            project_id = data.get("id")
            logger.info(f"--- [🧠] Vizard: Проект создан успешно. ID: {project_id}")
            return project_id

    async def poll_results(self, project_id: str, timeout_min: int = 30) -> List[Dict[str, Any]]:
        """
        Ожидает завершения анализа.
        """
        max_attempts = (timeout_min * 60) // 20
        
        async with httpx.AsyncClient(timeout=20.0) as client:
            for attempt in range(max_attempts):
                try:
                    response = await client.get(f"{self.base_url}/projects/{project_id}", headers=self.headers)
                    if response.status_code == 404:
                        logger.warning(f"⚠️ Проект {project_id} еще не виден в API...")
                        await asyncio.sleep(10)
                        continue

                    response.raise_for_status()
                    project_data = response.json()
                    status = project_data.get("status")

                    if status == "completed":
                        return self._parse_clips(project_data)
                    
                    if status == "failed":
                        logger.error(f"--- [❌] Vizard: Анализ провален.")
                        return []

                    if attempt % 3 == 0:
                        logger.info(f"--- [⏳] Vizard: Статус проекта {project_id}: {status}...")
                    
                except Exception as e:
                    logger.warning(f"⚠️ Ошибка при опросе Vizard: {e}")

                await asyncio.sleep(20)
        
        return []

    def _parse_clips(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        clips = data.get("clips", [])
        parsed = []
        for c in clips:
            parsed.append({
                "start": c.get("start_time", 0),
                "end": c.get("end_time", 60),
                "score": c.get("virality_score", 0),
                "title": c.get("title", "AI Highlight")
            })
        return sorted(parsed, key=lambda x: x['score'], reverse=True)[:5]