import os
import requests
import json
import logging
import yt_dlp
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class VideoRenderer:
    def __init__(self):
        self.api_key = os.getenv("CREATOMATE_API_KEY")
        self.template_id = os.getenv("CREATOMATE_TEMPLATE_ID")

    def _get_direct_url(self, url):
        """Извлекает прямую ссылку для Creatomate"""
        if "youtube.com" not in url and "youtu.be" not in url:
            return url
        try:
            ydl_opts = {'format': 'best', 'quiet': True, 'no_warnings': True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return info.get('url', url)
        except Exception as e:
            logger.warning(f"⚠️ Ошибка yt-dlp: {e}")
            return url

    def create_short(self, video_url, start_time, end_time, title, job_id):
        """Отправляет задачу на рендеринг"""
        logger.info(f"--- [☁️] Запуск облачного рендеринга для задачи #{job_id}")
        
        direct_url = self._get_direct_url(video_url)
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
            res_json = response.json()
            
            # Считаем успехом статус 200, 201 или наличие статуса 'planned' в теле ответа
            if response.status_code in [200, 201] or res_json.get('status') == 'planned':
                render_id = res_json[0].get('id') if isinstance(res_json, list) else res_json.get('id')
                logger.info(f"✅ Видео успешно ушло на рендер! ID: {render_id}")
                return render_id
            else:
                logger.error(f"❌ Ошибка Creatomate API: {response.text}")
                return None
        except Exception as e:
            logger.error(f"❌ Критическая ошибка рендерера: {e}")
            return None