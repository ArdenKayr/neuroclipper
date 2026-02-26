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
        logger.info(f"--- [🧠] Загрузка Whisper ({model_size})...")
        self.whisper_model = whisper.load_model(model_size)
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
        )

    def transcribe(self, video_path):
        result = self.whisper_model.transcribe(video_path, language="ru")
        return result['segments']

    def _extract_frames(self, video_path, num_frames=15):
        cap = cv2.VideoCapture(video_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames <= 0: return []
        interval = total_frames // (num_frames + 1)
        base64_frames = []
        for i in range(num_frames):
            cap.set(cv2.CAP_PROP_POS_FRAMES, (i + 1) * interval)
            ret, frame = cap.read()
            if ret:
                frame = cv2.resize(frame, (800, 450))
                _, buffer = cv2.imencode(".jpg", frame)
                base64_frames.append(base64.b64encode(buffer).decode("utf-8"))
        cap.release()
        return base64_frames

    def _clean_json_string(self, text):
        """Парсит JSON, исправляя ошибки форматирования ИИ"""
        text = re.sub(r'```json\s*|```', '', text)
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if not match: return None
        json_str = match.group(0)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            # Попытка исправить одинарные кавычки
            json_str = re.sub(r"(\s*)'(\w+)':", r'\1"\2":', json_str)
            json_str = re.sub(r":\s*'([^']*)'", r': "\1"', json_str)
            try:
                return json.loads(json_str)
            except:
                return None

    def find_visual_highlights(self, video_path):
        logger.info("--- [👁️] Глубокий анализ сцен через Gemini 3 Flash...")
        base64_frames = self._extract_frames(video_path)
        if not base64_frames: return None

        prompt = """Analyze frames. Find 1-3 highlights. Return ONLY a valid JSON list.
        Format: [{"start": 10.0, "end": 20.0, "title": "HOOK", "reason": "why", "visual_description": "what"}]"""

        content = [{"type": "text", "text": prompt}]
        for frame in base64_frames:
            content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{frame}"}})

        try:
            response = self.client.chat.completions.create(
                model="google/gemini-3-flash-preview", 
                messages=[{"role": "user", "content": content}],
                temperature=0.1
            )
            return self._clean_json_string(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"Ошибка OpenRouter: {e}")
            return None