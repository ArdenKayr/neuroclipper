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
        # Твой публичный IP для доступа Creatomate к файлам
        self.base_public_url = "http://82.97.243.143:8000/static"

    def create_short(self, local_filename, start_time, end_time, title, job_id, is_last=False):
        """Отправляет задачу на рендеринг с метаданными для последующей очистки"""
        filename = os.path.basename(local_filename)
        direct_url = f"{self.base_public_url}/{filename}"
        
        url = "https://api.creatomate.com/v2/renders"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Передаем информацию о файле и очередности в метаданных
        metadata = {
            "job_id": job_id,
            "title": title,
            "local_file": local_filename,
            "is_last": is_last
        }
        
        data = {
            "template_id": self.template_id,
            "modifications": {
                "Video-1.source": direct_url,
                "Video-1.trim_start": start_time,
                "Video-1.duration": end_time - start_time,
                "Text-Title.text": title.upper()
            },
            "metadata": json.dumps(metadata)
        }

        try:
            response = requests.post(url, headers=headers, json=data)
            res_json = response.json()
            if response.status_code in [200, 201] or res_json.get('status') == 'planned':
                render_id = res_json[0].get('id') if isinstance(res_json, list) else res_json.get('id')
                return render_id
            else:
                logger.error(f"❌ Ошибка Creatomate API: {response.text}")
                return None
        except Exception as e:
            logger.error(f"❌ Ошибка рендерера: {e}")
            return None