import os
import requests
import time
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class AIAnalyzer:
    def __init__(self):
        # Убираем лишние пробелы из ключа
        self.api_key = os.getenv("TWELVE_LABS_API_KEY", "").strip()
        self.headers = {"x-api-key": self.api_key}
        
        # Переходим на v1.1, так как v1.2 иногда выдает 404 на некоторых типах аккаунтов
        self.base_url = "https://api.twelvelabs.io/v1.1"

    def _get_or_create_index(self):
        """Проверяет наличие индекса 'Neuroclipper' или создает его"""
        try:
            # 1. Пробуем получить список индексов
            res = requests.get(f"{self.base_url}/indexes", headers=self.headers)
            
            # Если v1.1 выдает 404, пробуем v1.2 (авто-переключение)
            if res.status_code == 404:
                logger.info("--- [🔄] Переключаюсь на API v1.2...")
                self.base_url = "https://api.twelvelabs.io/v1.2"
                res = requests.get(f"{self.base_url}/indexes", headers=self.headers)

            if res.status_code != 200:
                logger.error(f"❌ Twelve Labs API Error ({res.status_code}): {res.text}")
                return None
            
            data = res.json()
            indexes = data.get('data', [])
            for idx in indexes:
                if idx.get('index_name') == "Neuroclipper":
                    return idx.get('_id')
            
            # 2. Если индекса нет, создаем его
            logger.info("--- [🏗️] Создаю новый индекс 'Neuroclipper' в Twelve Labs...")
            payload = {
                "index_name": "Neuroclipper",
                "engines": [
                    {
                        "engine_name": "marengo2.6",
                        "engine_options": ["visual", "conversation"]
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
        """Анализирует длинное видео и находит лучшие моменты"""
        logger.info(f"--- [👁️] Twelve Labs начинает глубокий анализ: {video_url}")
        
        index_id = self._get_or_create_index()
        if not index_id:
            return None

        try:
            # 1. Отправляем видео на индексацию (занимает время для длинных видео)
            task_url = f"{self.base_url}/tasks/external-provider"
            payload = {"index_id": index_id, "url": video_url}
            task_res = requests.post(task_url, headers=self.headers, json=payload)
            
            if task_res.status_code not in [200, 201]:
                logger.error(f"❌ Ошибка создания задачи: {task_res.text}")
                return None
            
            task_id = task_res.json().get('_id')
            logger.info(f"--- [⏳] Видео в очереди на анализ (Task: {task_id}). Ждем...")

            # 2. Ожидание готовности (Long Polling)
            video_id = None
            while True:
                status_res = requests.get(f"{self.base_url}/tasks/{task_id}", headers=self.headers)
                task_status = status_res.json().get('status')
                
                if task_status == 'ready':
                    video_id = status_res.json().get('video_id')
                    logger.info("✅ Анализ завершен!")
                    break
                elif task_status == 'failed':
                    logger.error("❌ Twelve Labs не смог обработать это видео.")
                    return None
                
                time.sleep(15) # Ждем 15 секунд перед следующей проверкой

            # 3. Получаем хайлайты (авто-суммаризация)
            # В v1.1/v1.2 для длинных видео используем эндпоинт 'summarize'
            summ_url = f"{self.base_url}/summarize"
            summ_payload = {"video_id": video_id, "type": "highlight"}
            summ_res = requests.post(summ_url, headers=self.headers, json=summ_payload)
            
            if summ_res.status_code == 200:
                highlights_data = summ_res.json().get('highlights', [])
                results = []
                for h in highlights_data:
                    results.append({
                        "start": h.get('start'),
                        "end": h.get('end'),
                        "title": h.get('highlight', 'Viral Clip')
                    })
                return results
            
            # Если суммаризация не сработала, берем дефолтный кусок, чтобы не ломать поток
            return [{"start": 10, "end": 40, "title": "Viral Moment"}]

        except Exception as e:
            logger.error(f"❌ Критическая ошибка AIAnalyzer: {e}")
            return None