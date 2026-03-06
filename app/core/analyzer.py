import os
import requests
import time
import json
import logging
from dotenv import load_dotenv
from services.downloader import VideoDownloader

load_dotenv()
logger = logging.getLogger(__name__)

class AIAnalyzer:
    def __init__(self):
        self.api_key = os.getenv("TWELVE_LABS_API_KEY", "").strip()
        self.headers = {"x-api-key": self.api_key}
        self.base_url = "https://api.twelvelabs.io/v1.3"
        self.downloader = VideoDownloader()

    def find_visual_highlights(self, video_url, job_id):
        """Возвращает хайлайты, локальный путь и S3 URL"""
        local_file, s3_url = self.downloader.download(video_url, job_id)
        if not local_file: 
            return [], None, None

        index_id = self._get_or_create_index()
        if not index_id: 
            return [], local_file, s3_url

        try:
            # 1. Загрузка в Twelve Labs
            task_url = f"{self.base_url}/tasks"
            with open(local_file, 'rb') as video_data:
                files = {
                    "index_id": (None, str(index_id)),
                    "video_file": (os.path.basename(local_file), video_data, "video/mp4")
                }
                task_res = requests.post(task_url, headers=self.headers, files=files)

            if task_res.status_code not in [200, 201]:
                return [], local_file, s3_url

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
                    return [], local_file, s3_url
                time.sleep(20)

            # 3. Получение хайлайтов
            analyze_url = f"{self.base_url}/analyze"
            analyze_payload = {
                "video_id": video_id,
                "prompt": "Identify all highly engaging, viral segments. For each segment, return a JSON object with 'start', 'end' (in seconds), and a short 'title'. Return only the list of JSON objects.",
            }
            analyze_res = requests.post(analyze_url, headers=self.headers, json=analyze_payload)
            
            if analyze_res.status_code == 200:
                raw_data = analyze_res.json().get('data', "")
                try:
                    start_idx = raw_data.find('[')
                    end_idx = raw_data.rfind(']') + 1
                    if start_idx != -1 and end_idx != -1:
                        highlights = json.loads(raw_data[start_idx:end_idx])
                        return highlights, local_file, s3_url
                except Exception as parse_err:
                    logger.error(f"❌ Ошибка парсинга хайлайтов: {parse_err}")

            return [{"start": 5, "end": 25, "title": "Auto-clip"}], local_file, s3_url

        except Exception as e:
            logger.error(f"❌ Ошибка анализатора: {e}")
            return [], local_file, s3_url

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