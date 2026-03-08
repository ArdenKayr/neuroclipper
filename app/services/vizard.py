import logging
import httpx
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from core.config import settings
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class VizardService:
    def __init__(self):
        self.api_key = settings.VIZARD_API_KEY
        # Актуальный базовый URL Vizard API
        self.base_url = "https://elb-api.vizard.ai/hvizard-server-front/open-api/v1"
        self.headers = {
            "VIZARDAI_API_KEY": self.api_key,
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
        Создает проект в Vizard.
        videoType: 2 (YouTube), 1 (Прямая ссылка на файл)
        """
        if not self.api_key:
            raise ValueError("VIZARD_API_KEY не установлен.")

        v_type = 2 if "youtube.com" in video_url or "youtu.be" in video_url else 1

        async with httpx.AsyncClient(timeout=30.0) as client:
            payload = {
                "videoUrl": video_url,
                "videoType": v_type,
                "lang": "auto",
                "preferLength": [0] # AI выбирает длину сам
            }
            response = await client.post(f"{self.base_url}/project/create", json=payload, headers=self.headers)
            
            if response.status_code != 200:
                logger.error(f"❌ Vizard Error {response.status_code}: {response.text}")
                response.raise_for_status()

            data = response.json()
            if data.get("code") != 2000:
                raise Exception(f"Vizard API Error: {data.get('errMsg')}")

            project_id = data.get("projectId")
            logger.info(f"--- [🧠] Vizard: Проект создан. ID: {project_id}")
            return str(project_id)

    async def poll_results(self, project_id: str, timeout_min: int = 40) -> List[Dict[str, Any]]:
        """
        Опрашивает статус проекта и возвращает хайлайты.
        """
        max_attempts = (timeout_min * 60) // 30
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for attempt in range(max_attempts):
                try:
                    response = await client.get(f"{self.base_url}/project/query/{project_id}", headers=self.headers)
                    response.raise_for_status()
                    res_json = response.json()

                    # Vizard возвращает code 2000 при успехе
                    if res_json.get("code") == 2000:
                        data = res_json.get("data", {})
                        videos = data.get("videos", [])
                        
                        if videos:
                            logger.info(f"--- [✅] Vizard: Найдено {len(videos)} клипов.")
                            return self._parse_clips(videos)
                        
                        if attempt % 4 == 0:
                            logger.info(f"--- [⏳] Vizard: Видео еще обрабатывается...")
                    else:
                        logger.warning(f"⚠️ Vizard Status: {res_json.get('errMsg')}")

                except Exception as e:
                    logger.warning(f"⚠️ Ошибка опроса Vizard: {e}")

                await asyncio.sleep(30) # Интервал 30 сек
        
        return []

    def _parse_clips(self, videos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Извлекает данные клипов"""
        parsed = []
        for v in videos:
            # Vizard API возвращает готовые клипы. 
            # Мы берем их название и виральность.
            parsed.append({
                "start": 0, # Для готовых клипов Vizard мы используем их целиком
                "end": v.get("videoMsDuration", 60000) / 1000,
                "score": float(v.get("viralScore", 0)),
                "title": v.get("title", "AI Clip"),
                "vizard_url": v.get("videoUrl") # Прямая ссылка на клип от Vizard
            })
        return sorted(parsed, key=lambda x: x['score'], reverse=True)[:5]