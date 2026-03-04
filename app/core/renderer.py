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
        # Твой публичный адрес (замени, если IP другой)
        self.base_public_url = "http://82.97.243.143:8000/static"

    def create_short(self, local_filename, start_time, end_time, title, job_id):
        """Отправляет задачу, используя файл, который уже лежит на твоем сервере"""
        logger.info(f"--- [☁️] Creatomate забирает файл с твоего сервера: {local_filename}")
        
        # Ссылка, по которой Creatomate скачает видео у тебя
        # Нам нужно только имя файла из полного пути
        filename = os.path.basename(local_filename)
        direct_url = f"{self.base_public_url}/{filename}"
        
        url = "https://api.creatomate.com/v2/renders"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        metadata_payload = json.dumps({"job_id": job_id, "title": title})
        
        data = {
            "template_id": self.template_id,
            "modifications": {
                "Video-1.source": direct_url,
                "Video-1.trim_start": start_time,
                "Video-1.duration": end_time - start_time,
                "Text-Title.text": title.upper()
            },
            "metadata": metadata_payload
        }

        try:
            response = requests.post(url, headers=headers, json=data)
            if response.status_code in [200, 201]:
                logger.info(f"✅ Creatomate начал скачивание с твоего сервера!")
                return True
            else:
                logger.error(f"❌ Ошибка Creatomate: {response.text}")
                return None
        except Exception as e:
            logger.error(f"❌ Ошибка рендерера: {e}")
            return None