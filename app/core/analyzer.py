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
        logger.info(f"--- [🧠] Загрузка Whisper ({model_size})...")
        self.whisper_model = whisper.load_model(model_size)
        
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
        )

    def transcribe(self, video_path):
        result = self.whisper_model.transcribe(video_path, language="ru")
        return result['segments']

    def _extract_frames(self, video_path, num_frames=10):
        cap = cv2.VideoCapture(video_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames <= 0: return []
        
        interval = total_frames // (num_frames + 1)
        base64_frames = []
        
        for i in range(num_frames):
            cap.set(cv2.CAP_PROP_POS_FRAMES, (i + 1) * interval)
            ret, frame = cap.read()
            if ret:
                # Уменьшаем для экономии лимитов
                frame = cv2.resize(frame, (640, 360))
                _, buffer = cv2.imencode(".jpg", frame)
                base64_frames.append(base64.b64encode(buffer).decode("utf-8"))
        
        cap.release()
        return base64_frames

    def find_visual_highlights(self, video_path):
        logger.info("--- [👁️] Визуальный анализ через OpenRouter...")
        
        base64_frames = self._extract_frames(video_path)
        if not base64_frames: return None

        # Промпт стал строже, чтобы ИИ не ошибался в JSON
        content = [
            {"type": "text", "text": "Analyze these frames. Find 1-3 viral highlights. Return ONLY a JSON list: [{'start': 10.0, 'end': 25.0, 'title': 'HOOK', 'reason': 'why'}]. No markdown, no text, just JSON."}
        ]
        
        for frame in base64_frames:
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{frame}"}
            })

        try:
            # ОБНОВЛЕНО: Используем актуальную модель Gemini 2.0 Flash
            response = self.client.chat.completions.create(
                model="google/gemini-2.0-flash-001",
                messages=[{"role": "user", "content": content}]
            )
            
            res_text = response.choices[0].message.content
            # Чистим ответ от лишних символов
            clean_json = res_text.replace('```json', '').replace('```', '').strip()
            return json.loads(clean_json)
        except Exception as e:
            logger.error(f"Ошибка OpenRouter: {e}")
            return None