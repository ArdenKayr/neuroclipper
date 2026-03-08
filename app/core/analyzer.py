import logging
import os
import asyncio
from typing import Tuple, List, Dict, Any
from services.downloader import VideoDownloader
from utils.s3_storage import S3Storage
from services.vizard import VizardService
from services.whisper import WhisperService
from core.config import settings

logger = logging.getLogger(__name__)

class AIAnalyzer:
    def __init__(self):
        self.downloader = VideoDownloader()
        self.s3 = S3Storage()
        self.vizard = VizardService()
        self.whisper = WhisperService()

    async def find_visual_highlights(self, url: str, job_id: int) -> Tuple[List[Dict[str, Any]], str, str]:
        local_file = None
        s3_url = None
        transcript_text = ""
        
        try:
            # 1. Загрузка контента
            logger.info(f"--- [📥] Задача #{job_id}: Скачивание видео и метаданных")
            loop = asyncio.get_event_loop()
            local_file, sub_file = await loop.run_in_executor(None, self.downloader.download_video, url, job_id)
            
            if not local_file:
                raise Exception("Видео не скачано")

            # 2. Параллельная загрузка в облако
            s_name = os.path.basename(local_file)
            s3_task = loop.run_in_executor(None, self.s3.upload_file, local_file, s_name)

            # 3. Получение текста (Авторские сабы или Whisper)
            if sub_file:
                logger.info("--- [📄] Найдены авторские субтитры. Используем их.")
                with open(sub_file, 'r', encoding='utf-8') as f:
                    transcript_text = f.read()
            else:
                logger.info("--- [🎙️] Авторских сабов нет. Запуск Whisper...")
                audio_file = await loop.run_in_executor(None, self.whisper.extract_audio, local_file)
                res = await self.whisper.transcribe(audio_file)
                transcript_text = res.text if res else ""

            s3_url = await s3_task

            # 4. Анализ (Vizard или наш SmartLLM)
            if settings.ENABLE_VIZARD and settings.VIZARD_API_KEY:
                logger.info("--- [📈] Используем Vizard AI...")
                vizard_job = await self.vizard.request_analysis(url)
                highlights = await self.vizard.poll_results(vizard_job)
            else:
                logger.info(f"--- [🧠] Поиск хайлайтов через {settings.OPENROUTER_MODEL}...")
                # ШАГ 2.4: Здесь будет вызов SmartLLMService.analyze(transcript_text)
                highlights = [{"start": 15, "end": 75, "title": "AI Highlight (Claude)", "transcript": transcript_text[:150]}]

            return highlights, local_file, s3_url

        except Exception as e:
            logger.error(f"❌ Ошибка в AIAnalyzer: {e}")
            return [], local_file or "", s3_url or ""