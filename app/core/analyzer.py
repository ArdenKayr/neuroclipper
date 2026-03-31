import logging
import os
import asyncio
import re
from typing import Tuple, List, Dict, Any
from services.downloader import VideoDownloader
from utils.s3_storage import S3Storage
from services.vizard import VizardService
from services.whisper import WhisperService
from services.llm import SmartLLMService
from core.config import settings

logger = logging.getLogger(__name__)

def clean_srt(srt_text: str) -> str:
    """Превращает грязный SRT в формат [12.5 - 15.0] Текст"""
    lines = srt_text.strip().split('\n')
    formatted = []
    current_time = ""
    current_text = []
    
    for line in lines:
        line = line.strip()
        if not line:
            if current_time and current_text:
                formatted.append(f"{current_time} {' '.join(current_text)}")
            current_time = ""
            current_text = []
            continue
            
        if '-->' in line:
            try:
                start_str, end_str = line.split('-->')
                def time_to_sec(t_str):
                    parts = t_str.strip().replace(',', '.').split(':')
                    return int(parts[0])*3600 + int(parts[1])*60 + float(parts[2])
                s = time_to_sec(start_str)
                e = time_to_sec(end_str)
                current_time = f"[{s:.1f} - {e:.1f}]"
            except:
                current_time = "[0.0 - 0.0]"
        elif not line.isdigit():
            clean_line = re.sub(r'<[^>]+>', '', line)
            current_text.append(clean_line)
            
    if current_time and current_text:
        formatted.append(f"{current_time} {' '.join(current_text)}")
        
    return "\n".join(formatted)

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
            logger.info(f"--- [📥] Задача #{job_id}: Подготовка ресурсов")
            loop = asyncio.get_event_loop()
            local_file, sub_file = await loop.run_in_executor(None, self.downloader.download_video, url, job_id)
            
            if not local_file:
                raise Exception("Видео не скачано.")

            s_name = os.path.basename(local_file)
            s3_task = loop.run_in_executor(None, self.s3.upload_file, local_file, s_name)

            if sub_file:
                logger.info(f"--- [📄] Использую авторские субтитры: {sub_file}")
                with open(sub_file, 'r', encoding='utf-8') as f:
                    raw_srt = f.read()
                    transcript_text = clean_srt(raw_srt)
            else:
                logger.info("--- [🎙️] Авторских сабов нет. Запуск Whisper...")
                audio_file = await loop.run_in_executor(None, self.whisper.extract_audio, local_file)
                transcript_text = await self.whisper.transcribe(audio_file)

            # --- 🔥 ДЕБАГГЕР 🔥 ---
            preview = transcript_text[:200].replace('\n', ' | ')
            logger.info(f"--- [🔍] Текст для LLM (превью): {preview}")
            # ----------------------

            try:
                s3_url = await s3_task
            except Exception as e:
                logger.error(f"⚠️ Ошибка загрузки в S3: {e}")
                s3_url = ""

            highlights = []
            if transcript_text:
                logger.info(f"--- [🧠] Поиск хайлайтов через {settings.OPENROUTER_MODEL}...")
                highlights = await self.llm.find_highlights(transcript_text)
            
            if not highlights:
                highlights = [{"start": 0.0, "end": 30.0, "title": "Демо-клип", "reason": "fallback"}]

            return highlights, local_file, s3_url

        except Exception as e:
            logger.error(f"❌ Ошибка в AIAnalyzer: {e}")
            return [], local_file or "", s3_url or ""