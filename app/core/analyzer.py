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
            # 1. Скачивание (видео + авторские сабы)
            logger.info(f"--- [📥] Начинаю загрузку для задачи #{job_id}")
            loop = asyncio.get_event_loop()
            local_file, sub_file = await loop.run_in_executor(None, self.downloader.download_video, url, job_id)
            
            # 2. Загрузка в R2 (пока идет анализ)
            s_name = os.path.basename(local_file)
            s3_task = loop.run_in_executor(None, self.s3.upload_file, local_file, s_name)

            # 3. ПОЛУЧЕНИЕ ТЕКСТА
            if sub_file:
                logger.info(f"--- [📄] Используем авторские субтитры: {sub_file}")
                with open(sub_file, 'r', encoding='utf-8') as f:
                    transcript_text = f.read()
            else:
                logger.info("--- [🎙️] Авторских субтитров нет. Запускаю Whisper...")
                audio_file = await loop.run_in_executor(None, self.whisper.extract_audio, local_file)
                res = await self.whisper.transcribe(audio_file)
                transcript_text = res.text if res else ""

            s3_url = await s3_task

            # 4. ВЫБОР МОЗГА (Vizard или наша LLM)
            if settings.ENABLE_VIZARD and settings.VIZARD_API_KEY:
                logger.info("--- [📈] Использую мозг Vizard...")
                highlights = await self.vizard.request_analysis(url) # Vizard сам качает
                highlights = await self.vizard.poll_results(highlights)
            else:
                logger.info(f"--- [🧠] Использую собственный мозг ({settings.OPENROUTER_MODEL})...")
                # В ШАГЕ 2.4 мы вызовем здесь SmartLLMService(transcript_text)
                highlights = [{"start": 30, "end": 90, "title": "Highlight from LLM (Pending 2.4)", "transcript": transcript_text[:100]}]

            return highlights, local_file, s3_url

        except Exception as e:
            logger.error(f"❌ Ошибка AIAnalyzer: {e}")
            return [], local_file or "", s3_url or ""