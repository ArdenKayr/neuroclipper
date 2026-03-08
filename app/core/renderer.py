import logging
import httpx
import json
from core.config import settings

logger = logging.getLogger(__name__)

class VideoRenderer:
    def __init__(self):
        self.api_key = settings.CREATOMATE_API_KEY
        self.template_id = settings.CREATOMATE_TEMPLATE_ID
        self.url = "https://api.creatomate.com/v2/renders"
        self.headers = {
            "Authorization": f"Bearer {settings.CREATOMATE_API_KEY}",
            "Content-Type": "application/json"
        }

    async def create_short(
        self, 
        s3_url: str, 
        start_time: float, 
        end_time: float, 
        title: str, 
        job_id: int,
        local_filename: str = None,
        style: str = "dynamic",
        is_last: bool = False
    ) -> str:
        duration = float(end_time) - float(start_time)
        
        # Убедитесь, что в шаблоне Creatomate слой называется "Video-1"
        payload = {
            "template_id": self.template_id,
            "modifications": {
                "Video-1.source": s3_url,
                "Video-1.time": float(start_time),
                "Video-1.duration": float(duration),
                "Video-1.fit": "cover",
                "Video-1.crop": "smart"
            },
            "metadata": json.dumps({
                "job_id": str(job_id),
                "is_last": str(is_last)
            })
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self.url, json=payload, headers=self.headers)
                
                if response.status_code >= 400:
                    logger.error(f"❌ Creatomate Error ({response.status_code}): {response.text}")
                    return None
                
                data = response.json()
                render_id = data[0]['id']
                logger.info(f"--- [🎥] Рендер запущен успешно. ID: {render_id}")
                return render_id
        except Exception as e:
            logger.error(f"❌ Критическая ошибка Renderer: {e}")
            return None