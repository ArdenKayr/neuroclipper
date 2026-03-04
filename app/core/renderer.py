import os
import requests
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class VideoRenderer:
    def __init__(self):
        self.api_key = os.getenv("CREATOMATE_API_KEY")
        self.template_id = os.getenv("CREATOMATE_TEMPLATE_ID")

    def create_short(self, video_url, start_time, end_time, title, job_id):
        """Отправляет задачу на рендеринг в Creatomate"""
        logger.info(f"--- [☁️] Запуск облачного рендеринга для задачи #{job_id}")
        
        url = "https://api.creatomate.com/v1/renders"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "template_id": self.template_id,
            "modifications": {
                "Video-1": video_url,
                "Video-1.trim_start": start_time,
                "Video-1.duration": end_time - start_time,
                "Text-Title": title.upper()
            },
            "metadata": {"job_id": job_id}
        }

        try:
            response = requests.post(url, headers=headers, json=data)
            if response.status_code == 200:
                render_id = response.json().get('id')
                logger.info(f"✅ Задача принята Creatomate: {render_id}")
                return render_id
            return None
        except Exception as e:
            logger.error(f"Ошибка Creatomate: {e}")
            return None