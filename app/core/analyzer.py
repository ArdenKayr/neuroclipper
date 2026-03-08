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
        Асинхронный пайплайн анализа.
        """
        local_file = None
        s3_url = None
        highlights = []

        try:
            # 1. Скачивание (нужно для локального Whisper в будущем)
            logger.info(f"--- [📥] Загрузка видео для задачи #{job_id}")
            loop = asyncio.get_event_loop()
            local_file = await loop.run_in_executor(None, self.downloader.download_video, url, job_id)
            
            if not local_file:
                raise Exception("Ошибка: Видео не скачано.")

            # 2. Загрузка в S3 (параллельно, пока Vizard думает)
            logger.info(f"--- [☁️] Резервное копирование в R2...")
            s_name = os.path.basename(local_file)
            s3_url = await loop.run_in_executor(None, self.s3.upload_file, local_file, s_name)

            # 3. Vizard AI Анализ
            if settings.VIZARD_API_KEY:
                logger.info(f"--- [📈] Запуск анализа Vizard API...")
                try:
                    # Шлем оригинальный URL (Vizard сам выкачает метаданные YouTube)
                    project_id = await self.vizard.request_analysis(url)
                    highlights = await self.vizard.poll_results(project_id)
                except Exception as e:
                    logger.error(f"❌ Ошибка Vizard API: {e}")
            
            if not highlights:
                logger.warning("⚠️ Хайлайты не получены. Используем демо-нарезку.")
                highlights = [{"start": 0, "end": 60, "score": 0, "title": "Демо-клип (Fallback)"}]

            return highlights, local_file, s3_url

        except Exception as e:
            logger.error(f"❌ Ошибка AIAnalyzer: {e}")
            return [], local_file or "", s3_url or ""