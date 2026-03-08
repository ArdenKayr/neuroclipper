import os
import logging
import subprocess
from openai import AsyncOpenAI
from core.config import settings

logger = logging.getLogger(__name__)

class WhisperService:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    def extract_audio(self, video_path: str) -> str:
        """Извлекает аудио из видео с помощью ffmpeg для экономии трафика API"""
        audio_path = video_path.replace(".mp4", ".mp3")
        try:
            # Сжимаем аудио до 32kbps моно, чтобы файл был крошечным
            command = [
                "ffmpeg", "-y", "-i", video_path,
                "-vn", "-acodec", "libmp3lame", "-ac", "1", "-ab", "32k", "-ar", "16000",
                audio_path
            ]
            subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return audio_path
        except Exception as e:
            logger.error(f"❌ Ошибка извлечения аудио: {e}")
            return None

    async def transcribe(self, audio_path: str):
        """Транскрибация с получением таймингов на уровне слов"""
        if not os.path.exists(audio_path):
            return None

        try:
            with open(audio_path, "rb") as audio_file:
                transcript = await self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="verbose_json",
                    timestamp_granularities=["word"]
                )
            return transcript
        except Exception as e:
            logger.error(f"❌ Ошибка Whisper API: {e}")
            return None
        finally:
            if os.path.exists(audio_path):
                os.remove(audio_path)