import logging
import yt_dlp
from typing import Tuple, Optional, Dict, Any

logger = logging.getLogger(__name__)

class LinkValidator:
    def __init__(self, max_duration_seconds: int = 10800): # Лимит поднят до часа
        self.max_duration = max_duration_seconds
        self.ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
        }

    async def validate_video(self, url: str) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Проверяет ссылку на видео.
        Возвращает: (Is_Valid, Error_Message, Metadata)
        """
        try:
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                # Извлекаем информацию без скачивания самого файла
                info = ydl.extract_info(url, download=False)
                
                if not info:
                    return False, "Не удалось извлечь данные о видео.", None

                duration = info.get('duration', 0)
                is_live = info.get('is_live', False)
                title = info.get('title', 'Unknown')

                logger.info(f"🔍 Валидация: {title} ({duration} сек.)")

                # 1. Проверка на Live-статус (стримы, которые идут ПРЯМО СЕЙЧАС)
                # Мы не можем резать видео, которое еще не закончилось.
                if is_live:
                    return False, "Стримы (Live) в прямом эфире не поддерживаются. Дождитесь окончания трансляции.", None

                # 2. Проверка на длительность (теперь до 3 часов)
                if duration > self.max_duration:
                    hours = self.max_duration // 3600
                    return False, f"Видео слишком длинное. Максимальная длительность — {hours} часа.", None

                # 3. Проверка на доступность форматов
                if not info.get('formats'):
                    return False, "Видео недоступно, защищено или удалено.", None

                return True, None, {
                    "title": title,
                    "duration": duration,
                    "thumbnail": info.get('thumbnail'),
                    "original_url": url
                }

        except yt_dlp.utils.DownloadError as e:
            logger.error(f"❌ Ошибка yt-dlp при валидации: {e}")
            return False, "Ссылка недействительна или видео находится в приватном доступе.", None
        except Exception as e:
            logger.error(f"❌ Непредвиденная ошибка валидатора: {e}")
            return False, f"Ошибка при проверке ссылки: {str(e)}", None