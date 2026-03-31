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
                segments = t_data.get('segments') or []
                
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

    async def generate_karaoke_ass(self, audio_path: str) -> str:
        """Получает таймкоды ПОСЛОВНО и генерирует идеальный ASS файл для TikTok"""
        if not audio_path or not os.path.exists(audio_path):
            return ""

        try:
            with open(audio_path, "rb") as f:
                transcript = await self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=f,
                    response_format="verbose_json",
                    timestamp_granularities=["word", "segment"]
                )
            
            t_data = transcript.model_dump() if hasattr(transcript, "model_dump") else (transcript if isinstance(transcript, dict) else vars(transcript))
            
            # ИСПРАВЛЕНИЕ: Жестко защищаемся от того, что прокси может вернуть null
            words = t_data.get('words') or []

            # Если API не вернуло слова, делаем фоллбэк на сегменты
            if not words:
                logger.warning("⚠️ Whisper не вернул 'words', пробую разбить 'segments'...")
                segments = t_data.get('segments') or []
                for s in segments:
                    w_list = s.get('text', '').split()
                    duration = s.get('end', 0) - s.get('start', 0)
                    step = duration / max(1, len(w_list))
                    for i, w in enumerate(w_list):
                        words.append({
                            "word": w,
                            "start": s.get('start', 0) + i * step,
                            "end": s.get('start', 0) + (i + 1) * step
                        })

            if not words:
                return ""

            # ASS Заголовок (Жестко фиксируем 720x1280, стиль: Желтый, по центру внизу)
            ass_content = """[Script Info]
ScriptType: v4.00+
PlayResX: 720
PlayResY: 1280

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,46,&H0000FFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,0,2,20,20,350,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
            def format_time_ass(seconds):
                h = int(seconds // 3600)
                m = int((seconds % 3600) // 60)
                s = int(seconds % 60)
                cs = int(round(seconds - int(seconds), 2) * 100)
                if cs >= 100: cs = 99
                return f"{h}:{m:02}:{s:02}.{cs:02}"

            chunk_size = 2  # МАКСИМУМ 2 СЛОВА НА ЭКРАН!
            for i in range(0, len(words), chunk_size):
                chunk = words[i:i+chunk_size]
                start_time = chunk[0]['start']
                end_time = chunk[-1]['end']
                
                # Очищаем от лишних пробелов и делаем текст ЗАГЛАВНЫМ
                text = " ".join([w['word'] for w in chunk]).strip().upper()
                
                ass_content += f"Dialogue: 0,{format_time_ass(start_time)},{format_time_ass(end_time)},Default,,0,0,0,,{text}\n"

            return ass_content

        except Exception as e:
            logger.error(f"❌ Ошибка Whisper API при генерации ASS: {e}")
            return ""