import os
import requests
import time
import json
import logging
import yt_dlp
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class AIAnalyzer:
    def __init__(self):
        self.api_key = os.getenv("TWELVE_LABS_API_KEY", "").strip()
        self.headers = {"x-api-key": self.api_key}
        self.base_url = "https://api.twelvelabs.io/v1.3"
        self.temp_dir = "/root/neuroclipper/temp_videos"
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)

    def _download_video(self, youtube_url):
        logger.info(f"--- [📥] Загрузка видео на сервер: {youtube_url}")
        timestamp = int(time.time())
        output_path = f"{self.temp_dir}/video_{timestamp}.mp4"
        
        ydl_opts = {
            'format': 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': output_path,
            'quiet': True,
            'no_warnings': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([youtube_url])
            return output_path
        except Exception as e:
            logger.error(f"❌ Ошибка скачивания видео: {e}")
            return None

    def find_visual_highlights(self, video_url):
        """Возвращает (highlights, local_file_path)"""
        local_file = self._download_video(video_url)
        if not local_file:
            return [], None

        index_id = self._get_or_create_index()
        if not index_id:
            return [], local_file

        try:
            task_url = f"{self.base_url}/tasks"
            logger.info(f"--- [📤] Отправка в Twelve Labs...")
            
            with open(local_file, 'rb') as video_data:
                files = {
                    "index_id": (None, str(index_id)),
                    "video_file": (os.path.basename(local_file), video_data, "video/mp4")
                }
                task_res = requests.post(task_url, headers=self.headers, files=files)

            if task_res.status_code not in [200, 201]:
                logger.error(f"❌ Ошибка загрузки: {task_res.text}")
                return [], local_file

            task_id = task_res.json().get('_id')
            logger.info(f"--- [⏳] Анализ запущен (Task: {task_id})")

            # ВАЖНО: Мы НЕ удаляем файл здесь, так как он нужен рендереру
            # В реальном проекте файлы удаляются по крону или после успеха рендера
            
            # Для теста возвращаем хайлайт
            return [{"start": 10, "end": 40, "title": "Viral Moment"}], local_file

        except Exception as e:
            logger.error(f"❌ Ошибка анализатора: {e}")
            return [], local_file

    def _get_or_create_index(self):
        try:
            res = requests.get(f"{self.base_url}/indexes", headers=self.headers)
            data = res.json().get('data', [])
            for idx in data:
                if idx.get('index_name') == "Neuroclipper":
                    return idx.get('_id')
            
            payload = {
                "index_name": "Neuroclipper",
                "models": [{"model_name": "marengo3.0", "model_options": ["visual", "audio"]}]
            }
            create_res = requests.post(f"{self.base_url}/indexes", headers=self.headers, json=payload)
            return create_res.json().get('_id')
        except:
            return None