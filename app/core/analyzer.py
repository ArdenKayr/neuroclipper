import os
import requests
import time
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class AIAnalyzer:
    def __init__(self):
        self.api_key = os.getenv("TWELVE_LABS_API_KEY")
        self.headers = {"x-api-key": self.api_key}
        self.base_url = "https://api.twelvelabs.io/v1.2"

    def _get_or_create_index(self):
        """Находит существующий индекс или создает новый для Neuroclipper"""
        res = requests.get(f"{self.base_url}/indexes", headers=self.headers)
        indexes = res.json().get('data', [])
        for idx in indexes:
            if idx.get('index_name') == "Neuroclipper":
                return idx.get('_id')
        
        # Создаем новый, если не нашли
        payload = {"index_name": "Neuroclipper", "engines": [{"engine_name": "marengo2.6", "engine_options": ["visual", "conversation"]}]}
        res = requests.post(f"{self.base_url}/indexes", headers=self.headers, json=payload)
        return res.json().get('_id')

    def find_visual_highlights(self, video_url):
        """Ищет виральные моменты в длинных видео через Twelve Labs"""
        logger.info(f"--- [👁️] Twelve Labs анализирует длинное видео: {video_url}")
        
        index_id = self._get_or_create_index()
        
        # 1. Создаем задачу на индексацию видео-ссылки
        task_url = f"{self.base_url}/tasks/external-provider"
        payload = {"index_id": index_id, "url": video_url}
        task_res = requests.post(task_url, headers=self.headers, json=payload)
        task_id = task_res.json().get('_id')
        
        # 2. Ждем завершения (для длинных видео это необходимо)
        logger.info(f"--- [⏳] Ожидание индексации (Task ID: {task_id})...")
        while True:
            status_res = requests.get(f"{self.base_url}/tasks/{task_id}", headers=self.headers)
            status = status_res.json().get('status')
            if status == 'ready':
                video_id = status_res.json().get('video_id')
                break
            elif status == 'failed':
                return None
            time.sleep(10)

        # 3. Генерируем хайлайты
        gen_url = f"{self.base_url}/summarize"
        gen_payload = {"video_id": video_id, "type": "highlight"}
        gen_res = requests.post(gen_url, headers=self.headers, json=gen_payload)
        
        data = gen_res.json()
        highlights = []
        for h in data.get('highlights', []):
            highlights.append({
                "start": h.get('start'),
                "end": h.get('end'),
                "title": h.get('highlight', 'Viral Clip')
            })
            
        return highlights if highlights else [{"start": 0, "end": 30, "title": "Интересный момент"}]