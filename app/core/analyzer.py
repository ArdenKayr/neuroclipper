import logging
import os
import asyncio
from typing import Tuple, List, Dict, Any
from services.downloader import VideoDownloader
from utils.s3_storage import S3Storage
from services.vizard import VizardService
from services.whisper import WhisperService
from services.llm import SmartLLMService
from core.config import settings

logger = logging.getLogger(__name__)

class AIAnalyzer:
    def __init__(self):
        self.downloader = VideoDownloader()
        self.s3 = S3Storage()
        self.vizard = VizardService()
        self.whisper = WhisperService()
        self.llm = SmartLLMService()

    async def find_visual_highlights(self, url: str, job_id: int) -> Tuple[List[Dict[str, Any]], str, str]:
        local_file = None
        s3_url = None
        transcript_text = ""
        
        try:
            # 1. Загрузка
            logger.info(f"--- [📥] Задача #{job_id}: Подготовка ресурсов")
            loop = asyncio.get_event_loop()
            local_file, sub_file = await loop.run_in_executor(None, self.downloader.download_video, url, job_id)
            
            if not local_file:
                raise Exception("Видео не скачано.")

            # 2. Параллельная загрузка в S3
            s_name = os.path.basename(local_file)
            s3_task = loop.run_in_executor(None, self.s3.upload_file, local_file, s_name)

            # 3. Получение текста
            if sub_file:
                logger.info(f"--- [📄] Использую авторские субтитры: {sub_file}")
                with open(sub_file, 'r', encoding='utf-8') as f:
                    transcript_text = f.read()
            else:
                logger.info("--- [🎙️] Авторских сабов нет. Запуск Whisper...")
                audio_file = await loop.run_in_executor(None, self.whisper.extract_audio, local_file)
                # Получаем готовый текст с таймкодами напрямую
                transcript_text = await self.whisper.transcribe(audio_file)

            # Безопасное ожидание S3, чтобы ошибка облака не обрушила весь процесс
            try:
                s3_url = await s3_task
            except Exception as e:
                logger.error(f"⚠️ Ошибка загрузки в S3, продолжаем локально: {e}")
                s3_url = ""

            # 4. Анализ смыслов
            highlights = []
            if settings.ENABLE_VIZARD and settings.VIZARD_API_KEY:
                logger.info("--- [📈] Использую Vizard API...")
                v_job = await self.vizard.request_analysis(url)
                highlights = await self.vizard.poll_results(v_job)
            else:
                if transcript_text:
                    logger.info(f"--- [🧠] Поиск хайлайтов через {settings.OPENROUTER_MODEL}...")
                    highlights = await self.llm.find_highlights(transcript_text)
            
            if not highlights:
                logger.warning("⚠️ Анализ не дал результатов. Применяю fallback.")
                highlights = [{"start": 0.0, "end": 30.0, "title": "Демо-клип", "reason": "fallback"}]

            return highlights, local_file, s3_url

        except Exception as e:
            logger.error(f"❌ Ошибка в AIAnalyzer: {e}")
            return [], local_file or "", s3_url or ""