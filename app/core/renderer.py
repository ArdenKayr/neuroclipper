import logging
import httpx
from core.config import settings

logger = logging.getLogger(__name__)

class VideoRenderer:
    def __init__(self):
        self.api_key = settings.CREATOMATE_API_KEY
        self.template_id = settings.CREATOMATE_TEMPLATE_ID
        self.url = "https://api.creatomate.com/v2/renders"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    async def create_short(
        self, 
        s3_url: str, 
        start_time: float, 
        end_time: float, 
        title: str, 
        job_id: int,
        local_filename: str = None, # Добавлено для совместимости
        style: str = "dynamic",
        is_last: bool = False
    ) -> str:
        """
        Отправляет запрос на рендер в Creatomate.
        """
        duration = float(end_time) - float(start_time)
        
        modifications = {
            "Video-1.source": s3_url,
            "Video-1.time": float(start_time),
            "Video-1.duration": duration,
            "Video-1.fit": "cover",
            "Video-1.crop": "smart" 
        }

        payload = {
            "template_id": self.template_id,
            "modifications": modifications,
            "metadata": {
                "job_id": str(job_id),
                "title": title,
                "is_last": str(is_last).lower()
            }
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self.url, json=payload, headers=self.headers)
                response.raise_for_status()
                data = response.json()
                
                render_id = data[0]['id']
                logger.info(f"--- [🎥] Рендер запущен в Creatomate. Render ID: {render_id}")
                return render_id
        except Exception as e:
            logger.error(f"❌ Ошибка Creatomate API: {e}")
            return None