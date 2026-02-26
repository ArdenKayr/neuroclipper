import os
import cv2
import json
import base64
import logging
import whisper
import re
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class AIAnalyzer:
    def __init__(self, model_size="base"):
        # Локальный Whisper для генерации текста субтитров
        logger.info(f"--- [🧠] Загрузка Whisper ({model_size})...")
        self.whisper_model = whisper.load_model(model_size)
        
        # Настройка OpenRouter для доступа к Gemini 3
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
        )

    def transcribe(self, video_path):
        """Расшифровка аудио для наложения титров"""
        result = self.whisper_model.transcribe(video_path, language="ru")
        return result['segments']

    def _extract_frames(self, video_path, num_frames=15):
        """Извлекает ключевые кадры для визуального анализа (увеличено до 15)"""
        cap = cv2.VideoCapture(video_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames <= 0: return []
        
        interval = total_frames // (num_frames + 1)
        base64_frames = []
        
        for i in range(num_frames):
            cap.set(cv2.CAP_PROP_POS_FRAMES, (i + 1) * interval)
            ret, frame = cap.read()
            if ret:
                # Оптимальный размер для Gemini 3 Flash
                frame = cv2.resize(frame, (800, 450))
                _, buffer = cv2.imencode(".jpg", frame)
                base64_frames.append(base64.b64encode(buffer).decode("utf-8"))
        
        cap.release()
        return base64_frames

    def _extract_json(self, text):
        """Интеллектуальный поиск JSON в ответе нейросети"""
        try:
            match = re.search(r'\[.*\]', text, re.DOTALL)
            if match:
                return json.loads(match.group(0))
            return json.loads(text)
        except Exception:
            logger.error(f"Не удалось распарсить JSON. Ответ ИИ: {text}")
            return None

    def find_visual_highlights(self, video_path):
        """Глубокий визуальный анализ через Gemini 3 Flash Preview"""
        logger.info("--- [👁️] Глубокий анализ сцен через Gemini 3 Flash...")
        
        base64_frames = self._extract_frames(video_path)
        if not base64_frames: return None

        # Продвинутый промпт для анализа визуальных сцен
        prompt = """
        Ты - эксперт по виральному контенту и профессиональный видеомонтажер. 
        Проанализируй последовательность кадров и выдели 1-3 самых захватывающих хайлайта.
        
        Критерии выбора:
        1. Визуальная динамика (движение, жестикуляция).
        2. Эмоциональные пики (мимика, смех, удивление).
        3. Смена планов или яркие визуальные события.

        Для каждого момента опиши визуальную сцену (visual_description).
        
        Выдай ответ СТРОГО в формате JSON списка:
        [
          {
            "start": 12.5, 
            "end": 30.0, 
            "title": "ЗАГОЛОВОК КРЮЧОК", 
            "reason": "почему это вирально",
            "visual_description": "детальное описание того, что происходит в кадре"
          }
        ]
        """

        content = [{"type": "text", "text": prompt}]
        for frame in base64_frames:
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{frame}"}
            })

        try:
            response = self.client.chat.completions.create(
                model="google/gemini-3-flash-preview", 
                messages=[{"role": "user", "content": content}],
                temperature=0.2
            )
            
            res_text = response.choices[0].message.content
            return self._extract_json(res_text)
        except Exception as e:
            logger.error(f"Ошибка при обращении к Gemini 3: {e}")
            return None