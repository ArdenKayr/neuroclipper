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
        """Проверяет наличие индекса 'Neuroclipper' или создает его по стандартам v1.3"""
        try:
            res = requests.get(f"{self.base_url}/indexes", headers=self.headers)
            
            if res.status_code != 200:
                logger.error(f"❌ Twelve Labs API Error ({res.status_code}): {res.text}")
                return None
            
            data = res.json()
            indexes = data.get('data', [])
            for idx in indexes:
                if idx.get('index_name') == "Neuroclipper":
                    return idx.get('_id')
            
            # В v1.3 МЫ ИСПОЛЬЗУЕМ 'models' ВМЕСТО 'engines'
            logger.info("--- [🏗️] Создаю новый индекс 'Neuroclipper' (API v1.3)...")
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
            
            logger.error(f"❌ Не удалось создать индекс: {create_res.text}")
            return None

        except Exception as e:
            logger.error(f"❌ Ошибка при работе с индексами: {e}")
            return None

    def find_visual_highlights(self, video_url):
        """Ищет виральные моменты через эндпоинт /analyze"""
        logger.info(f"--- [👁️] Twelve Labs (v1.3) начинает анализ: {video_url}")
        
        index_id = self._get_or_create_index()
        if not index_id:
            return None

        try:
            # 1. Отправляем видео на индексацию
            task_url = f"{self.base_url}/tasks/external-provider"
            payload = {"index_id": index_id, "url": video_url}
            task_res = requests.post(task_url, headers=self.headers, json=payload)
            
            if task_res.status_code not in [200, 201]:
                logger.error(f"❌ Ошибка создания задачи: {task_res.text}")
                return None
            
            task_id = task_res.json().get('_id')
            logger.info(f"--- [⏳] Видео в очереди (Task: {task_id}). Ждем индексации...")

            # 2. Ожидание готовности
            video_id = None
            while True:
                status_res = requests.get(f"{self.base_url}/tasks/{task_id}", headers=self.headers)
                status_data = status_res.json()
                task_status = status_data.get('status')
                
                if task_status == 'ready':
                    video_id = status_data.get('video_id')
                    logger.info("✅ Индексация завершена успешно!")
                    break
                elif task_status in ['failed', 'canceled']:
                    logger.error(f"❌ Ошибка Twelve Labs. Статус: {task_status}")
                    return None
                
                time.sleep(15)

            # 3. Анализ видео и генерация хайлайтов
            analyze_url = f"{self.base_url}/analyze"
            analyze_payload = {
                "video_id": video_id,
                "prompt": "Identify 3-5 high-energy, viral segments suitable for social media. Return start and end timestamps."
            }
            logger.info("--- [🤖] Запуск /analyze для поиска лучших моментов...")
            analyze_res = requests.post(analyze_url, headers=self.headers, json=analyze_payload)
            
            if analyze_res.status_code == 200:
                # В v1.3 ответ от /analyze содержит текстовый разбор моментов
                logger.info("✅ Анализ выполнен успешно.")
                # Для теста возвращаем один сегмент, пока идет отладка парсинга таймкодов
                return [{"start": 10, "end": 40, "title": "Viral Moment"}]
            
            logger.error(f"❌ Ошибка /analyze: {analyze_res.text}")
            return [{"start": 0, "end": 30, "title": "Интересный момент"}]

        except Exception as e:
            logger.error(f"❌ Критическая ошибка AIAnalyzer: {e}")
            return None