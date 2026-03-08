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
        local_filename: str = None,
        style: str = "dynamic",
        is_last: bool = False
    ) -> str:
        """
        Отправляет запрос на рендер в Creatomate.
        Поле metadata теперь передается строго как JSON-строка.
        """
        duration = float(end_time) - float(start_time)
        
        # Данные для модификации шаблона
        modifications = {
            "Video-1.source": s3_url,
            "Video-1.time": float(start_time),
            "Video-1.duration": float(duration),
            "Video-1.fit": "cover",
            "Video-1.crop": "smart" 
        }

        # Creatomate требует, чтобы metadata была строкой
        metadata_str = json.dumps({
            "job_id": str(job_id),
            "is_last": str(is_last).lower(),
            "title": title
        })

        payload = {
            "template_id": self.template_id,
            "modifications": modifications,
            "metadata": metadata_str
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self.url, json=payload, headers=self.headers)
                
                if response.status_code not in [200, 201, 202]:
                    logger.error(f"❌ Creatomate Error ({response.status_code}): {response.text}")
                    return None
                
                data = response.json()
                # Creatomate возвращает список объектов рендера
                render_id = data[0]['id'] if isinstance(data, list) else data.get('id')
                
                logger.info(f"--- [🎥] Рендер запущен успешно. ID: {render_id}")
                return render_id
        except Exception as e:
            logger.error(f"❌ Критическая ошибка Renderer: {str(e)}")
            return None