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
        self.base_url = "https://api.vizard.ai/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
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
            raise ValueError("VIZARD_API_KEY не задан. Анализ невозможен.")

        async with httpx.AsyncClient(timeout=30.0) as client:
            # У Vizard API может меняться структура эндпоинта, 
            # используем стандартную схему создания проекта
            payload = {
                "input_url": video_url,
                "auto_clip": True,
                "aspect_ratio": "9:16"
            }
            response = await client.post(f"{self.base_url}/projects", json=payload, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            project_id = data.get("id")
            logger.info(f"--- [🧠] Vizard: Проект создан. ID: {project_id}")
            return project_id

    async def poll_results(self, project_id: str, timeout_min: int = 30) -> List[Dict[str, Any]]:
        """
        Ожидает завершения анализа, опрашивая API раз в 20 секунд.
        """
        max_attempts = (timeout_min * 60) // 20
        
        async with httpx.AsyncClient(timeout=20.0) as client:
            for attempt in range(max_attempts):
                try:
                    response = await client.get(f"{self.base_url}/projects/{project_id}", headers=self.headers)
                    response.raise_for_status()
                    project_data = response.json()
                    status = project_data.get("status")

                    if status == "completed":
                        logger.info(f"--- [✅] Vizard: Анализ завершен для {project_id}")
                        return self._parse_clips(project_data)
                    
                    if status == "failed":
                        logger.error(f"--- [❌] Vizard: Анализ провален для {project_id}")
                        return []

                    if attempt % 3 == 0:
                        logger.info(f"--- [⏳] Vizard: Видео анализируется (статус: {status})...")
                    
                except Exception as e:
                    logger.warning(f"⚠️ Ошибка при опросе Vizard: {e}")

                await asyncio.sleep(20)
        
        logger.error(f"--- [🛑] Vizard: Превышено время ожидания для {project_id}")
        return []

    def _parse_clips(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Извлекает тайминги и virality score из ответа API"""
        clips = data.get("clips", [])
        parsed = []
        for c in clips:
            parsed.append({
                "start": c.get("start_time"),
                "end": c.get("end_time"),
                "score": c.get("virality_score", 0),
                "title": c.get("title", "AI Highlight")
            })
        # Берем топ-5 самых виральных моментов
        return sorted(parsed, key=lambda x: x['score'], reverse=True)[:5]