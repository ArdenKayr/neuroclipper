import logging
import os
import asyncio
from typing import Tuple, List, Dict, Any
from services.downloader import VideoDownloader
from utils.s3_storage import S3Storage
from services.vizard import VizardService
from core.config import settings

logger = logging.getLogger(__name__)

class AIAnalyzer:
    def __init__(self):
        self.downloader = VideoDownloader()
        self.s3 = S3Storage()
        self.vizard = VizardService()

    async def find_visual_highlights(self, url: str, job_id: int) -> Tuple[List[Dict[str, Any]], str, str]:
        """
        Основной метод анализа:
        1. Скачивание (локально)
        2. Загрузка в S3 (для рендерера)
        3. Анализ через Vizard (поиск моментов)
        """
        local_file = None
        s3_url = None
        highlights = []

        try:
            # 1. Скачивание (блокирующая операция, запускаем в потоке)
            logger.info(f"--- [📥] Загрузка видео для задачи #{job_id}")
            loop = asyncio.get_event_loop()
            local_file = await loop.run_in_executor(None, self.downloader.download_video, url, job_id)
            
            if not local_file or not os.path.exists(local_file):
                raise Exception("Файл не был скачан или путь не найден.")

            # 2. Загрузка в S3
            logger.info(f"--- [☁️] Загрузка оригинала в R2...")
            s_name = os.path.basename(local_file)
            # Метод upload_file синхронный, запускаем в потоке
            s3_url = await loop.run_in_executor(None, self.s3.upload_file, local_file, s_name)

            # 3. Умный поиск хайлайтов через Vizard
            if settings.VIZARD_API_KEY:
                logger.info(f"--- [📈] Запуск анализа Vizard API...")
                try:
                    project_id = await self.vizard.request_analysis(url)
                    highlights = await self.vizard.poll_results(project_id)
                except Exception as e:
                    logger.error(f"❌ Ошибка Vizard API: {e}")
            else:
                logger.warning("⚠️ VIZARD_API_KEY не задан. Используем fallback-хайлайт.")

            # Fallback: если Vizard не сработал, берем первые 60 секунд
            if not highlights:
                highlights = [{"start": 0, "end": 60, "score": 0, "title": "Highlight (Fallback)"}]

            return highlights, local_file, s3_url

        except Exception as e:
            logger.error(f"❌ Ошибка в AIAnalyzer: {e}")
            return [], local_file or "", s3_url or ""