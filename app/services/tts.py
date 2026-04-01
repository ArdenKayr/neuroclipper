import edge_tts
import logging

logger = logging.getLogger(__name__)

class TTSService:
    def __init__(self):
        # Мужской, энергичный американский голос. Идеально для Shorts/Reels.
        self.voice = "en-US-ChristopherNeural" 

    async def generate_audio(self, text: str, output_path: str) -> str:
        try:
            logger.info(f"--- [🎙️] Генерирую английскую озвучку: {text[:30]}...")
            # Ускоряем на 5%, чтобы звучало динамичнее
            communicate = edge_tts.Communicate(text, self.voice, rate="+5%") 
            await communicate.save(output_path)
            return output_path
        except Exception as e:
            logger.error(f"❌ Ошибка Edge TTS: {e}")
            return None