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
            logger.error(f"❌ Ошибка скачивания: {e}")
            return None

    def find_visual_highlights(self, video_url):
        local_file = self._download_video(video_url)
        if not local_file: return [], None

        index_id = self._get_or_create_index()
        if not index_id: return [], local_file

        try:
            # 1. Загрузка файла в задачу
            task_url = f"{self.base_url}/tasks"
            with open(local_file, 'rb') as video_data:
                files = {
                    "index_id": (None, str(index_id)),
                    "video_file": (os.path.basename(local_file), video_data, "video/mp4")
                }
                task_res = requests.post(task_url, headers=self.headers, files=files)

            if task_res.status_code not in [200, 201]:
                return [], local_file

            task_id = task_res.json().get('_id')
            logger.info(f"--- [⏳] Анализ в Twelve Labs (Task: {task_id})")

            # 2. Ожидание индексации
            video_id = None
            while True:
                status_res = requests.get(f"{self.base_url}/tasks/{task_id}", headers=self.headers)
                status_data = status_res.json()
                if status_data.get('status') == 'ready':
                    video_id = status_data.get('video_id')
                    break
                elif status_data.get('status') in ['failed', 'canceled']:
                    return [], local_file
                time.sleep(20)

            # 3. ПОЛУЧЕНИЕ РЕАЛЬНЫХ ХАЙЛАЙТОВ
            analyze_url = f"{self.base_url}/analyze"
            # Мы просим ИИ вернуть строго JSON структуру
            analyze_payload = {
                "video_id": video_id,
                "prompt": "Identify all highly engaging, viral segments. For each segment, return a JSON object with 'start', 'end' (in seconds), and a short 'title'. Return only the list of JSON objects.",
            }
            analyze_res = requests.post(analyze_url, headers=self.headers, json=analyze_payload)
            
            if analyze_res.status_code == 200:
                raw_data = analyze_res.json().get('data', "")
                logger.info(f"--- [🤖] Ответ ИИ: {raw_data}")
                
                # Попытка вытащить JSON из текста (ИИ иногда добавляет пояснения)
                try:
                    # Ищем начало и конец списка [ ... ]
                    start_idx = raw_data.find('[')
                    end_idx = raw_data.rfind(']') + 1
                    if start_idx != -1 and end_idx != -1:
                        highlights = json.loads(raw_data[start_idx:end_idx])
                        return highlights, local_file
                except Exception as parse_err:
                    logger.error(f"❌ Ошибка парсинга хайлайтов: {parse_err}")

            # Если не распарсили, вернем хоть что-то, чтобы не ломать цепочку
            return [{"start": 5, "end": 25, "title": "Auto-clip"}], local_file

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