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
        Полный цикл анализа видео.
        """
        local_file = None
        s3_url = None
        highlights = []

        try:
            # 1. Скачивание (нам все равно нужен локальный файл для Whisper в будущем)
            logger.info(f"--- [📥] Загрузка видео для задачи #{job_id}")
            local_file = await self.downloader.download_video(url, job_id)
            if not local_file:
                raise Exception("Не удалось скачать видео")

            # 2. Загрузка в S3 (для рендерера Creatomate)
            logger.info(f"--- [☁️] Загрузка исходника в Cloudflare R2...")
            s_name = f"source_{job_id}.mp4"
            s3_url = await self.s3.upload_file(local_file, s_name)

            # 3. Интеллектуальный анализ через Vizard
            if settings.VIZARD_API_KEY:
                logger.info(f"--- [📈] Vizard: Запуск анализа контента...")
                try:
                    # Отправляем на анализ оригинальный URL (Vizard сам его скачает)
                    project_id = await self.vizard.request_analysis(url)
                    highlights = await self.vizard.poll_results(project_id)
                except Exception as e:
                    logger.error(f"❌ Ошибка Vizard: {e}")
            else:
                logger.warning("⚠️ VIZARD_API_KEY отсутствует. Работаю в демо-режиме (нарезка 0-60 сек).")

            # 4. Fallback (если API не вернуло ничего или нет ключа)
            if not highlights:
                highlights = [{
                    "start": 0, 
                    "end": 60, 
                    "score": 0, 
                    "title": "Демо-клип (Vizard недоступен)"
                }]

            return highlights, local_file, s3_url

        except Exception as e:
            logger.error(f"❌ Критическая ошибка в AIAnalyzer: {e}")
            return [], "", ""