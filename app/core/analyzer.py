import whisper
import os
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AIAnalyzer:
    def __init__(self, model_size="base"):
        # Модели: tiny, base, small, medium, large
        # "base" — золотая середина для серверов без мощной GPU
        logger.info(f"--- [🧠] Загрузка модели Whisper ({model_size})...")
        self.model = whisper.load_model(model_size)

    def transcribe(self, video_path):
        """Превращает речь из видео в текст с таймкодами"""
        logger.info(f"--- [👂] Анализирую звук в {video_path}...")
        
        # Находим путь к аудио (Whisper сам вытащит звук из mp4)
        result = self.model.transcribe(video_path, verbose=False, language="ru")
        
        segments = result['segments']
        logger.info(f"--- [✅] Распознано {len(segments)} фрагментов текста.")
        return segments

    def find_highlights(self, segments, user_prompt=""):
        """
        Логика поиска хайлайтов. 
        Пока ищем по ключевым словам и плотности речи.
        """
        highlights = []
        # Список "хайповых" слов для триггера
        trigger_words = ["жесть", "шок", "внимание", "капец", "блин", "смешно", "хаха"]
        
        for i, segment in enumerate(segments):
            text = segment['text'].lower()
            
            # Если в тексте есть триггер-слово — это потенциальный хайлайт
            is_hot = any(word in text for word in trigger_words)
            
            if is_hot:
                # Берем кусок: 5 секунд до и 10 секунд после фразы
                start = max(0, segment['start'] - 5)
                end = segment['end'] + 10
                highlights.append({
                    "start": start,
                    "end": end,
                    "text": segment['text'],
                    "score": 1.0
                })
        
        logger.info(f"--- [🔥] Найдено {len(highlights)} потенциальных клипов.")
        return highlights