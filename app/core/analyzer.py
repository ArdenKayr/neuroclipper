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
            # 1. Скачивание
            logger.info(f"--- [📥] Загрузка видео для задачи #{job_id}")
            local_file = await self.downloader.download_video(url, job_id)
            if not local_file:
                raise Exception("Ошибка при скачивании видео")

            # 2. Загрузка в S3 (параллельно с анализом, если API позволяет ссылку)
            logger.info(f"--- [☁️] Загрузка оригинала в R2...")
            s3_url = await self.s3.upload_file(local_file, f"source_{job_id}_{int(asyncio.get_event_loop().time())}.mp4")

            # 3. Умный поиск хайлайтов через Vizard
            if settings.VIZARD_API_KEY:
                logger.info(f"--- [📈] Запуск анализа Vizard API...")
                try:
                    # В реальном API можно передать s3_url или исходный url
                    project_id = await self.vizard.request_analysis(url)
                    highlights = await self.vizard.poll_analysis(project_id)
                except Exception as e:
                    logger.error(f"❌ Ошибка Vizard API: {e}. Используем fallback.")
            
            # Fallback: если Vizard не сработал или нет ключа, берем первые 30 секунд
            if not highlights:
                logger.warning("⚠️ Хайлайты не найдены. Создаем fallback-фрагмент (0-60 сек).")
                highlights = [{"start": 0, "end": 60, "score": 0, "title": "Highlight (Fallback)"}]

            return highlights, local_file, s3_url

        except Exception as e:
            logger.error(f"❌ Ошибка в AIAnalyzer: {e}")
            return [], "", ""