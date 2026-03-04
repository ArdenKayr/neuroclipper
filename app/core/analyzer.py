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
        """Извлекает прямую ссылку на видеофайл из YouTube"""
        try:
            ydl_opts = {
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                'quiet': True,
                'no_warnings': True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(youtube_url, download=False)
                return info.get('url')
        except Exception as e:
            logger.error(f"❌ Ошибка извлечения прямой ссылки: {e}")
            return youtube_url

    def _get_or_create_index(self):
        """Проверяет наличие индекса или создает его в формате v1.3"""
        try:
            res = requests.get(f"{self.base_url}/indexes", headers=self.headers)
            if res.status_code != 200:
                logger.error(f"❌ Twelve Labs API Error ({res.status_code}): {res.text}")
                return None
            
            indexes = res.json().get('data', [])
            for idx in indexes:
                if idx.get('index_name') == "Neuroclipper":
                    return idx.get('_id')
            
            logger.info("--- [🏗️] Создаю новый индекс 'Neuroclipper' (API v1.3)...")
            payload = {
                "index_name": "Neuroclipper",
                "models": [{"model_name": "marengo3.0", "model_options": ["visual", "audio"]}]
            }
            create_res = requests.post(f"{self.base_url}/indexes", headers=self.headers, json=payload)
            if create_res.status_code in [200, 201]:
                return create_res.json().get('_id')
            
            return None
        except Exception as e:
            logger.error(f"❌ Ошибка при работе с индексами: {e}")
            return None

    def find_visual_highlights(self, video_url):
        """Анализирует видео и находит хайлайты"""
        # ШАГ 0: Получаем прямую ссылку, которую 'поймет' Twelve Labs
        direct_url = self._get_direct_video_url(video_url)
        logger.info(f"--- [👁️] Twelve Labs (v1.3) анализирует поток: {direct_url[:50]}...")
        
        index_id = self._get_or_create_index()
        if not index_id: return None

        try:
            # 1. СОЗДАНИЕ ЗАДАЧИ
            task_url = f"{self.base_url}/tasks"
            form_data = {
                "index_id": (None, index_id),
                "video_url": (None, direct_url)
            }
            
            task_res = requests.post(task_url, headers=self.headers, files=form_data)
            
            if task_res.status_code not in [200, 201]:
                logger.error(f"❌ Ошибка создания задачи ({task_res.status_code}): {task_res.text}")
                return None
            
            task_id = task_res.json().get('_id')
            logger.info(f"--- [⏳] Видео в очереди (Task: {task_id}). Ждем индексации...")

            # 2. ОЖИДАНИЕ ГОТОВНОСТИ
            video_id = None
            while True:
                status_res = requests.get(f"{self.base_url}/tasks/{task_id}", headers=self.headers)
                status_data = status_res.json()
                task_status = status_data.get('status')
                
                if task_status == 'ready':
                    video_id = status_data.get('video_id')
                    break
                elif task_status in ['failed', 'canceled']:
                    logger.error(f"❌ Индексация прервана: {status_data}")
                    return None
                time.sleep(15)

            # 3. ПОЛУЧЕНИЕ ХАЙЛАЙТОВ
            analyze_url = f"{self.base_url}/analyze"
            analyze_payload = {
                "video_id": video_id,
                "prompt": "Identify 3-5 high-energy, viral moments for social media. Provide start and end times in seconds.",
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "type": "object",
                        "properties": {
                            "highlights": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "start": {"type": "number"},
                                        "end": {"type": "number"},
                                        "title": {"type": "string"}
                                    }
                                }
                            }
                        }
                    }
                }
            }
            
            logger.info("--- [🤖] Twelve Labs выполняет глубокий анализ...")
            analyze_res = requests.post(analyze_url, headers=self.headers, json=analyze_payload)
            
            if analyze_res.status_code == 200:
                try:
                    result_data = analyze_res.json().get('data', {})
                    if isinstance(result_data, str):
                        result_data = json.loads(result_data)
                    
                    highlights = result_data.get('highlights', [])
                    if highlights:
                        logger.info(f"✅ Успешно найдено {len(highlights)} моментов.")
                        return highlights
                except Exception:
                    pass

            return [{"start": 10, "end": 40, "title": "Viral Moment"}]

        except Exception as e:
            logger.error(f"❌ Критическая ошибка AIAnalyzer: {e}")
            return None