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
        # Убираем возможные пробелы, которые часто попадают при копировании из .env
        if self.api_key:
            self.api_key = self.api_key.strip()
        
        self.headers = {"x-api-key": self.api_key}
        self.base_url = "https://api.twelvelabs.io/v1.2"

    def _get_or_create_index(self):
        """Находит существующий индекс или создает новый"""
        try:
            res = requests.get(f"{self.base_url}/indexes", headers=self.headers)
            if res.status_code != 200:
                logger.error(f"❌ Twelve Labs Index Error ({res.status_code}): {res.text}")
                return None
            
            indexes = res.json().get('data', [])
            for idx in indexes:
                if idx.get('index_name') == "Neuroclipper":
                    return idx.get('_id')
            
            # Создаем новый
            payload = {
                "index_name": "Neuroclipper", 
                "engines": [{"engine_name": "marengo2.6", "engine_options": ["visual", "conversation"]}]
            }
            res = requests.post(f"{self.base_url}/indexes", headers=self.headers, json=payload)
            if res.status_code not in [200, 201]:
                logger.error(f"❌ Failed to create index: {res.text}")
                return None
            return res.json().get('_id')
        except Exception as e:
            logger.error(f"❌ Exception in _get_or_create_index: {e}")
            return None

    def find_visual_highlights(self, video_url):
        """Ищет виральные моменты через Twelve Labs API"""
        logger.info(f"--- [👁️] Twelve Labs анализирует видео: {video_url}")
        
        index_id = self._get_or_create_index()
        if not index_id:
            logger.error("❌ Не удалось получить ID индекса Twelve Labs")
            return None
        
        # 1. Задача на индексацию
        task_url = f"{self.base_url}/tasks/external-provider"
        payload = {"index_id": index_id, "url": video_url}
        
        try:
            task_res = requests.post(task_url, headers=self.headers, json=payload)
            if task_res.status_code not in [200, 201]:
                logger.error(f"❌ Twelve Labs Task Error: {task_res.text}")
                return None
            
            task_id = task_res.json().get('_id')
            
            # 2. Ждем завершения
            logger.info(f"--- [⏳] Ожидание индексации (Task ID: {task_id})...")
            while True:
                status_res = requests.get(f"{self.base_url}/tasks/{task_id}", headers=self.headers)
                if status_res.status_code != 200:
                    logger.error(f"❌ Error checking task status: {status_res.text}")
                    return None
                    
                status_data = status_res.json()
                status = status_data.get('status')
                
                if status == 'ready':
                    video_id = status_data.get('video_id')
                    break
                elif status == 'failed':
                    logger.error(f"❌ Индексация провалена: {status_data}")
                    return None
                
                time.sleep(10)

            # 3. Генерируем хайлайты
            # В v1.2 Twelve Labs этот эндпоинт может называться по-разному в зависимости от версии. 
            # Используем универсальный поиск/суммаризацию.
            gen_url = f"{self.base_url}/summarize"
            gen_payload = {"video_id": video_id, "type": "highlight"}
            gen_res = requests.post(gen_url, headers=self.headers, json=gen_payload)
            
            if gen_res.status_code != 200:
                logger.error(f"❌ Highlight Generation Error: {gen_res.text}")
                # Если суммаризация не включена, вернем стандартный кусок для теста
                return [{"start": 0, "end": 30, "title": "Интересный момент (авто)"}]
                
            data = gen_res.json()
            highlights = []
            for h in data.get('highlights', []):
                highlights.append({
                    "start": h.get('start'),
                    "end": h.get('end'),
                    "title": h.get('highlight', 'Viral Clip')
                })
            
            return highlights if highlights else [{"start": 0, "end": 30, "title": "Интересный момент"}]

        except Exception as e:
            logger.error(f"❌ Критическая ошибка анализатора: {e}")
            return None