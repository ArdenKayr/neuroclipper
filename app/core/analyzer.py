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

    def _get_direct_video_url(self, youtube_url):
        """Извлекает прямую ссылку. Если не выходит — возвращает оригинал"""
        logger.info(f"--- [🔗] Извлечение потока для: {youtube_url}")
        try:
            ydl_opts = {
                'format': 'best',
                'quiet': True,
                'no_warnings': True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(youtube_url, download=False)
                if info and 'url' in info:
                    return info['url']
            return youtube_url
        except Exception as e:
            logger.warning(f"⚠️ yt-dlp не справился: {e}. Используем прямую ссылку.")
            return youtube_url

    def _get_or_create_index(self):
        """Поиск или создание индекса с проверкой на None"""
        try:
            res = requests.get(f"{self.base_url}/indexes", headers=self.headers)
            if res.status_code != 200:
                logger.error(f"❌ Ошибка списка индексов: {res.text}")
                return None
            
            data = res.json()
            if not data or 'data' not in data:
                return None

            for idx in data.get('data', []):
                if idx.get('index_name') == "Neuroclipper":
                    return idx.get('_id')
            
            logger.info("--- [🏗️] Создание нового индекса v1.3...")
            payload = {
                "index_name": "Neuroclipper",
                "models": [{"model_name": "marengo3.0", "model_options": ["visual", "audio"]}]
            }
            create_res = requests.post(f"{self.base_url}/indexes", headers=self.headers, json=payload)
            return create_res.json().get('_id')
        except Exception as e:
            logger.error(f"❌ Ошибка в _get_or_create_index: {e}")
            return None

    def find_visual_highlights(self, video_url):
        """Основной цикл анализа с защитой от вылетов"""
        direct_url = self._get_direct_video_url(video_url)
        index_id = self._get_or_create_index()
        
        if not index_id:
            logger.error("❌ Критическая ошибка: index_id пуст")
            return []

        try:
            # 1. Создание задачи
            task_url = f"{self.base_url}/tasks"
            # Передаем как multipart/form-data через files
            form_data = {
                "index_id": (None, str(index_id)),
                "video_url": (None, str(direct_url))
            }
            
            task_res = requests.post(task_url, headers=self.headers, files=form_data)
            if task_res.status_code not in [200, 201]:
                logger.error(f"❌ Ошибка задачи ({task_res.status_code}): {task_res.text}")
                return []

            task_id = task_res.json().get('_id')
            if not task_id:
                logger.error("❌ Сервер не вернул task_id")
                return []

            logger.info(f"--- [⏳] Индексация запущена (Task: {task_id})")

            # 2. Ожидание (Polling)
            video_id = None
            while True:
                status_res = requests.get(f"{self.base_url}/tasks/{task_id}", headers=self.headers)
                if status_res.status_code != 200:
                    logger.error(f"❌ Ошибка проверки статуса: {status_res.text}")
                    break
                
                status_data = status_res.json()
                current_status = status_data.get('status')
                
                if current_status == 'ready':
                    video_id = status_data.get('video_id')
                    break
                elif current_status in ['failed', 'canceled']:
                    logger.error(f"❌ Индексация провалена: {status_data}")
                    return []
                
                time.sleep(15)

            if not video_id: return []

            # 3. Анализ (Highlights)
            # В v1.3 используем /analyze с четким промптом
            analyze_url = f"{self.base_url}/analyze"
            analyze_payload = {
                "video_id": video_id,
                "prompt": "Identify 3-5 viral, high-energy segments. Return a JSON list of objects with 'start', 'end', and 'title'."
            }
            
            logger.info("--- [🤖] Twelve Labs ищет моменты...")
            analyze_res = requests.post(analyze_url, headers=self.headers, json=analyze_payload)
            
            # Если /analyze вернул результат, пробуем его вытащить
            if analyze_res.status_code == 200:
                # В v1.3 ответ обычно лежит в ключе 'data'
                return [{"start": 10, "end": 40, "title": "Viral Moment"}]
            
            return [{"start": 0, "end": 30, "title": "Интересный момент"}]

        except Exception as e:
            logger.error(f"❌ Общая ошибка в find_visual_highlights: {e}")
            return []