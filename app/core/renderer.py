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

    def create_short(self, s3_url, start_time, end_time, title, job_id, local_filename, is_last=False):
        """Отправляет задачу на рендеринг, используя прямую ссылку из R2"""
        url = "https://api.creatomate.com/v2/renders"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        metadata = {
            "job_id": job_id,
            "title": title,
            "local_file": local_filename,
            "is_last": is_last
        }
        
        data = {
            "template_id": self.template_id,
            "modifications": {
                "Video-1.source": s3_url, # Источник — облако R2
                "Video-1.trim_start": start_time,
                "Video-1.duration": end_time - start_time,
                "Text-Title.text": title.upper()
            },
            "metadata": json.dumps(metadata)
        }

        try:
            response = requests.post(url, headers=headers, json=data)
            res_json = response.json()
            if response.status_code in [200, 201]:
                render_id = res_json[0].get('id') if isinstance(res_json, list) else res_json.get('id')
                return render_id
            else:
                logger.error(f"❌ Ошибка Creatomate API: {response.text}")
                return None
        except Exception as e:
            logger.error(f"❌ Ошибка рендерера: {e}")
            return None