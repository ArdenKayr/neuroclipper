import logging
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from core.config import settings
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class VizardService:
    def __init__(self):
        self.api_key = settings.VIZARD_API_KEY
        self.base_url = "https://api.vizard.ai/v1" # Базовый URL API Vizard
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
        Отправляет видео на анализ в Vizard.
        Возвращает project_id.
        """
        if not self.api_key:
            raise ValueError("VIZARD_API_KEY не установлен в конфигурации.")

        async with httpx.AsyncClient(timeout=30.0) as client:
            payload = {
                "url": video_url,
                "auto_clip": True,
                "language": "auto"
            }
            response = await client.post(f"{self.base_url}/projects", json=payload, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            project_id = data.get("id")
            logger.info(f"--- [🧠] Vizard: Видео отправлено на анализ. Project ID: {project_id}")
            return project_id

    async def get_highlights(self, project_id: str) -> List[Dict[str, Any]]:
        """
        Получает результаты анализа (хайлайты) по ID проекта.
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{self.base_url}/projects/{project_id}/clips", headers=self.headers)
            response.raise_for_status()
            data = response.json()
            
            clips = data.get("clips", [])
            # Сортируем по Virality Score (если есть) и берем топ-5
            sorted_clips = sorted(clips, key=lambda x: x.get("virality_score", 0), reverse=True)
            
            highlights = []
            for clip in sorted_clips[:5]:
                highlights.append({
                    "start": clip["start_time"],
                    "end": clip["end_time"],
                    "score": clip.get("virality_score", 0),
                    "title": clip.get("title", "Виральный момент")
                })
            
            return highlights

    async def poll_analysis(self, project_id: str, max_retries: int = 60) -> List[Dict[str, Any]]:
        """
        Опрашивает API Vizard до готовности результатов.
        """
        for i in range(max_retries):
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/projects/{project_id}", headers=self.headers)
                status = response.json().get("status")
                
                if status == "completed":
                    return await self.get_highlights(project_id)
                elif status == "failed":
                    logger.error(f"❌ Vizard: Анализ проекта {project_id} провален.")
                    return []
                
                if i % 5 == 0:
                    logger.info(f"⏳ Vizard: Анализ в процессе (статус: {status})...")
                
                await asyncio.sleep(10) # Ждем 10 секунд перед следующим опросом
        
        return []