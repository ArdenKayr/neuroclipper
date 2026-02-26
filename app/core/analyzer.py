import google.generativeai as genai
import os
import time
import json
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class AIAnalyzer:
    def __init__(self, model_size="base"):
        # Оставляем Whisper для титров
        import whisper
        self.whisper_model = whisper.load_model(model_size)
        
        # Настраиваем Gemini
        genai.configure(api_key=os.getenv("GEMINI_KEY"))
        self.vision_model = genai.GenerativeModel('gemini-1.5-pro')

    def transcribe(self, video_path):
        """Точная расшифровка для титров"""
        result = self.whisper_model.transcribe(video_path, language="ru")
        return result['segments']

    def find_visual_highlights(self, video_path):
        """Мультимодальный анализ видео через Gemini"""
        logger.info("--- [👁️] Отправка видео на визуальный анализ в Gemini...")
        
        # 1. Загружаем видео в облако Google (временно)
        video_file = genai.upload_file(path=video_path)
        
        # Ждем, пока файл обработается на стороне Google
        while video_file.state.name == "PROCESSING":
            time.sleep(2)
            video_file = genai.get_file(video_file.name)

        # 2. Промпт для поиска хайлайтов
        prompt = """
        Проанализируй это видео. Найди 3 самых динамичных, эмоциональных или смешных момента для TikTok/Reels.
        Для каждого момента:
        1. Укажи время начала и конца.
        2. Придумай виральный заголовок (крючок).
        3. Объясни, почему это круто (визуальный контекст).
        
        Ответ выдай СТРОГО в формате JSON списка:
        [{"start": 10.5, "end": 25.0, "title": "ОН ЭТО СДЕЛАЛ!", "reason": "Эмоциональная реакция и прыжок"}]
        """

        # 3. Получаем ответ
        response = self.vision_model.generate_content([video_file, prompt])
        
        # Очищаем файл в облаке
        genai.delete_file(video_file.name)
        
        # Парсим JSON (убираем лишние кавычки если есть)
        clean_json = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(clean_json)