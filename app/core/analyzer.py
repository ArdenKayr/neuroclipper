import os
import cv2
import json
import base64
import logging
import whisper
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class AIAnalyzer:
    def __init__(self, model_size="base"):
        # Whisper для точных титров (работает локально, блокировки нет)
        logger.info(f"--- [🧠] Загрузка Whisper ({model_size})...")
        self.whisper_model = whisper.load_model(model_size)
        
        # Настройка OpenRouter (обход блокировки Google)
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
        )

    def transcribe(self, video_path):
        """Расшифровка аудио в текст"""
        result = self.whisper_model.transcribe(video_path, language="ru")
        return result['segments']

    def _extract_frames(self, video_path, num_frames=10):
        """Извлекает несколько кадров из видео для визуального анализа"""
        cap = cv2.VideoCapture(video_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        interval = total_frames // (num_frames + 1)
        
        base64_frames = []
        for i in range(num_frames):
            cap.set(cv2.CAP_PROP_POS_FRAMES, (i + 1) * interval)
            ret, frame = cap.read()
            if ret:
                # Уменьшаем размер кадра для экономии токенов
                frame = cv2.resize(frame, (640, 360))
                _, buffer = cv2.imencode(".jpg", frame)
                base64_frames.append(base64.b64encode(buffer).decode("utf-8"))
        
        cap.release()
        return base64_frames

    def find_visual_highlights(self, video_path):
        """Анализ видео через OpenRouter (Gemini 1.5 Pro/Flash)"""
        logger.info("--- [👁️] Визуальный анализ через OpenRouter...")
        
        base64_frames = self._extract_frames(video_path)
        
        # Формируем контент для нейронки (кадры + инструкции)
        content = [
            {"type": "text", "text": "Проанализируй эти кадры из видео. Найди 2-3 самых интересных или динамичных момента. Выдай ответ строго в формате JSON списка: [{'start': 10.0, 'end': 25.0, 'title': 'ЗАГОЛОВОК', 'reason': 'почему'}]"}
        ]
        
        for frame in base64_frames:
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{frame}"}
            })

        try:
            response = self.client.chat.completions.create(
                model="google/gemini-flash-1.5", # Быстрая и дешевая модель
                messages=[{"role": "user", "content": content}]
            )
            
            res_text = response.choices[0].message.content
            # Очистка от markdown-оформления
            clean_json = res_text.replace('```json', '').replace('```', '').strip()
            return json.loads(clean_json)
        except Exception as e:
            logger.error(f"Ошибка OpenRouter: {e}")
            return None