import os
import logging
import subprocess
from openai import AsyncOpenAI
from core.config import settings

logger = logging.getLogger(__name__)

class WhisperService:
    def __init__(self):
        # 🔥 Настраиваем клиент с учетом возможного прокси
        client_kwargs = {"api_key": settings.OPENAI_API_KEY}
        if settings.OPENAI_BASE_URL:
            client_kwargs["base_url"] = settings.OPENAI_BASE_URL
            
        self.client = AsyncOpenAI(**client_kwargs)

    def extract_audio(self, video_path: str) -> str:
        audio_path = video_path.replace(".mp4", ".mp3")
        try:
            command = [
                "ffmpeg", "-y", "-i", video_path, "-t", "1800",
                "-vn", "-acodec", "libmp3lame", "-ac", "1", "-ab", "32k", "-ar", "16000",
                audio_path
            ]
            subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return audio_path
        except Exception as e:
            logger.error(f"❌ Ошибка ffmpeg: {e}")
            return None

    async def transcribe(self, audio_path: str) -> str:
        if not audio_path or not os.path.exists(audio_path):
            return ""

        try:
            with open(audio_path, "rb") as f:
                transcript = await self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=f,
                    response_format="verbose_json",
                    timestamp_granularities=["segment"]
                )
            
            formatted_text = ""
            try:
                t_data = transcript.model_dump() if hasattr(transcript, "model_dump") else (transcript if isinstance(transcript, dict) else vars(transcript))
                segments = t_data.get('segments', [])
                
                if segments:
                    for seg in segments:
                        start = seg.get('start', 0)
                        end = seg.get('end', 0)
                        text = seg.get('text', '')
                        formatted_text += f"[{float(start):.1f} - {float(end):.1f}] {text.strip()}\n"
                else:
                    formatted_text = t_data.get('text', str(transcript))
            except Exception as parse_e:
                logger.error(f"⚠️ Ошибка парсинга сегментов Whisper: {parse_e}")
                formatted_text = str(transcript)
                
            return formatted_text
        except Exception as e:
            logger.error(f"❌ Ошибка Whisper API: {e}")
            return ""
        finally:
            if os.path.exists(audio_path):
                os.remove(audio_path)