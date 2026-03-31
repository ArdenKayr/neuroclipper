import logging
import yt_dlp
from typing import Tuple, Optional, Dict, Any

logger = logging.getLogger(__name__)

class LinkValidator:
    # Ограничиваем до 30 минут (1800 сек), чтобы аудио не превышало лимит 25 МБ для OpenAI
    def __init__(self, max_duration_seconds: int = 1800): 
        self.max_duration = max_duration_seconds
        self.ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
        }

    async def validate_video(self, url: str) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        try:
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if not info:
                    return False, "Не удалось извлечь данные о видео.", None

                duration = info.get('duration', 0)
                is_live = info.get('is_live', False)
                title = info.get('title', 'Unknown')

                logger.info(f"🔍 Валидация: {title} ({duration} сек.)")

                if is_live:
                    return False, "Стримы (Live) в прямом эфире не поддерживаются. Дождитесь окончания трансляции.", None

                if duration > self.max_duration:
                    mins = self.max_duration // 60
                    return False, f"Видео слишком длинное. Для теста максимальная длительность — {mins} минут.", None

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