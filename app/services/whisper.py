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
        """Конвертирует видео в легкий MP3 для транскрибации"""
        audio_path = video_path.replace(".mp4", ".mp3")
        try:
            # Обрезаем аудио до первых 30 минут, чтобы точно не словить ошибку 400 от OpenAI (превышение веса)
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
        """Отправляет аудио в Whisper API и возвращает текст с ТАЙМКОДАМИ"""
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
            
            # Собираем текст с таймкодами: [12.0 - 15.5] Текст
            formatted_text = ""
            if hasattr(transcript, 'segments') and transcript.segments:
                for seg in transcript.segments:
                    start = seg.start if hasattr(seg, 'start') else seg.get('start', 0)
                    end = seg.end if hasattr(seg, 'end') else seg.get('end', 0)
                    text = seg.text if hasattr(seg, 'text') else seg.get('text', '')
                    formatted_text += f"[{start:.1f} - {end:.1f}] {text.strip()}\n"
            else:
                formatted_text = transcript.text if hasattr(transcript, 'text') else str(transcript)
                
            return formatted_text
        except Exception as e:
            logger.error(f"❌ Ошибка Whisper API: {e}")
            return ""
        finally:
            if os.path.exists(audio_path):
                os.remove(audio_path)