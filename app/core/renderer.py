import os
import requests
import json
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class VideoRenderer:
    def __init__(self):
        self.api_key = os.getenv("CREATOMATE_API_KEY")
        self.template_id = os.getenv("CREATOMATE_TEMPLATE_ID")

    def create_short(self, video_url, start_time, end_time, title, job_id):
        """Отправляет задачу на рендеринг в Creatomate API v2"""
        logger.info(f"--- [☁️] Запуск облачного рендеринга для задачи #{job_id}")
        
        # Используем актуальный URL v2
        url = "https://api.creatomate.com/v2/renders"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Creatomate требует, чтобы metadata была строкой. 
        # Мы упакуем туда ID задачи и заголовок в формате JSON-строки.
        metadata_payload = json.dumps({
            "job_id": job_id,
            "title": title
        })
        
        data = {
            "template_id": self.template_id,
            "modifications": {
                "Video-1.source": video_url,
                "Video-1.trim_start": start_time,
                "Video-1.duration": end_time - start_time,
                "Text-Title.text": title.upper()
            },
            "metadata": metadata_payload
        }

        try:
            response = requests.post(url, headers=headers, json=data)
            if response.status_code == 200:
                res_data = response.json()
                # API v2 возвращает список объектов
                render_id = res_data[0].get('id') if isinstance(res_data, list) else res_data.get('id')
                logger.info(f"✅ Задача принята Creatomate: {render_id}")
                return render_id
            else:
                logger.error(f"❌ Ошибка Creatomate API: {response.text}")
                return None
        except Exception as e:
            logger.error(f"Ошибка Creatomate: {e}")
            return None