import whisper
import logging

logger = logging.getLogger(__name__)

class AIAnalyzer:
    def __init__(self, model_size="base"):
        logger.info(f"--- [🧠] Загрузка Whisper ({model_size})...")
        self.model = whisper.load_model(model_size)

    def transcribe(self, video_path):
        result = self.model.transcribe(video_path, language="ru")
        return result['segments']

    def generate_hook_title(self, text_snippet):
        """Здесь должна быть логика LLM. Пока сделаем умную выжимку."""
        # В будущем тут будет: return llm.ask("Придумай хайповый заголовок для этого текста")
        words = text_snippet.split()
        if len(words) > 5:
            return " ".join(words[:5]).upper() + "..."
        return text_snippet.upper()

    def find_highlights(self, segments):
        """Алгоритм поиска: ищем плотность речи и ключевые слова"""
        highlights = []
        for i in range(len(segments) - 2):
            # Соединяем 3 сегмента для анализа контекста
            context_text = segments[i]['text'] + segments[i+1]['text']
            
            # Простая логика: если есть восклицания или "громкие" слова
            if any(word in context_text.lower() for word in ["блин", "представляешь", "шок", "смотри"]):
                highlights.append({
                    "start": segments[i]['start'],
                    "end": segments[i+2]['end'],
                    "text": context_text,
                    "title": self.generate_hook_title(context_text)
                })
        return highlights