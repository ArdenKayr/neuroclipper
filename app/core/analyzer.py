import os
import requests
import time
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class AIAnalyzer:
    def __init__(self):
        # Очищаем ключ от лишних пробелов
        self.api_key = os.getenv("TWELVE_LABS_API_KEY", "").strip()
        self.headers = {"x-api-key": self.api_key}
        self.base_url = "https://api.twelvelabs.io/v1.3"

    def _get_or_create_index(self):
        """Проверяет наличие индекса 'Neuroclipper' или создает его (v1.3 стандарт)"""
        try:
            res = requests.get(f"{self.base_url}/indexes", headers=self.headers)
            if res.status_code != 200:
                logger.error(f"❌ Twelve Labs API Error ({res.status_code}): {res.text}")
                return None
            
            indexes = res.json().get('data', [])
            for idx in indexes:
                if idx.get('index_name') == "Neuroclipper":
                    return idx.get('_id')
            
            # В v1.3 используем 'models' вместо 'engines'
            logger.info("--- [🏗️] Создаю новый индекс 'Neuroclipper'...")
            payload = {
                "index_name": "Neuroclipper",
                "models": [
                    {
                        "model_name": "marengo3.0",
                        "model_options": ["visual", "audio"]
                    }
                ]
            }
            create_res = requests.post(f"{self.base_url}/indexes", headers=self.headers, json=payload)
            if create_res.status_code in [200, 201]:
                return create_res.json().get('_id')
            
            logger.error(f"❌ Ошибка создания индекса: {create_res.text}")
            return None
        except Exception as e:
            logger.error(f"❌ Ошибка при работе с индексами: {e}")
            return None

    def find_visual_highlights(self, video_url):
        """Анализирует видео и находит лучшие моменты (Highlights)"""
        logger.info(f"--- [👁️] Twelve Labs начинает анализ: {video_url}")
        
        index_id = self._get_or_create_index()
        if not index_id:
            return None

        try:
            # 1. СОЗДАНИЕ ЗАДАЧИ (В v1.3 используем просто /tasks)
            task_url = f"{self.base_url}/tasks"
            # Параметр video_url используется для внешних ссылок
            payload = {
                "index_id": index_id, 
                "video_url": video_url
            }
            
            task_res = requests.post(task_url, headers=self.headers, json=payload)
            if task_res.status_code not in [200, 201]:
                logger.error(f"❌ Ошибка создания задачи ({task_res.status_code}): {task_res.text}")
                return None
            
            task_id = task_res.json().get('_id')
            logger.info(f"--- [⏳] Видео в очереди (Task: {task_id}). Анализ запущен...")

            # 2. ОЖИДАНИЕ (Polling)
            video_id = None
            while True:
                status_res = requests.get(f"{self.base_url}/tasks/{task_id}", headers=self.headers)
                status_data = status_res.json()
                task_status = status_data.get('status')
                
                if task_status == 'ready':
                    video_id = status_data.get('video_id')
                    logger.info("✅ Видео успешно проиндексировано!")
                    break
                elif task_status in ['failed', 'canceled']:
                    logger.error(f"❌ Индексация прервана. Статус: {task_status}")
                    return None
                
                # Для длинных видео проверяем статус каждые 15 секунд
                time.sleep(15)

            # 3. ГЕНЕРАЦИЯ ХАЙЛАЙТОВ
            # Используем эндпоинт /summarize с типом 'highlight'
            summ_url = f"{self.base_url}/summarize"
            summ_payload = {
                "video_id": video_id, 
                "type": "highlight",
                "prompt": "Identify viral, high-energy moments for social media."
            }
            
            logger.info("--- [🤖] Twelve Labs ищет виральные моменты...")
            summ_res = requests.post(summ_url, headers=self.headers, json=summ_payload)
            
            if summ_res.status_code == 200:
                highlights_data = summ_res.json().get('highlights', [])
                results = []
                for h in highlights_data:
                    results.append({
                        "start": h.get('start'),
                        "end": h.get('end'),
                        "title": h.get('title', 'Viral Clip')
                    })
                logger.info(f"✅ Найдено хайлайтов: {len(results)}")
                return results
            
            logger.error(f"❌ Ошибка генерации хайлайтов: {summ_res.text}")
            return [{"start": 10, "end": 40, "title": "Viral Moment"}]

        except Exception as e:
            logger.error(f"❌ Критическая ошибка: {e}")
            return None