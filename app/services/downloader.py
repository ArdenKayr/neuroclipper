import yt_dlp
import os
import time
import logging

logger = logging.getLogger(__name__)

class VideoDownloader:
    def __init__(self, download_path="assets/downloads"):
        self.download_path = download_path
        if not os.path.exists(self.download_path):
            os.makedirs(self.download_path)

    def download_video(self, url: str, job_id: int):
        """
        Скачивает видео и авторские субтитры.
        Возвращает (video_path, subtitle_path)
        """
        timestamp = int(time.time())
        filename = f"source_{job_id}_{timestamp}"
        output_tmpl = os.path.join(self.download_path, f"{filename}.%(ext)s")
        
        ydl_opts = {
            'format': 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': output_tmpl,
            'merge_output_format': 'mp4',
            'noplaylist': True,
            'quiet': True,
            # Настройки субтитров
            'writesubtitles': True,
            'subtitleslangs': ['ru', 'en'],
            'writeautomaticsub': False, # СТРОГО ИГНОРИРУЕМ мусорные авто-субтитры
            'postprocessors': [{
                'key': 'FFmpegSubtitlesConvertor',
                'format': 'srt', # Конвертируем в удобный формат
            }],
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                video_path = ydl.prepare_filename(info)
                
                # Ищем файл субтитров (yt-dlp меняет расширение на .srt)
                base_path = os.path.splitext(video_path)[0]
                subtitle_path = f"{base_path}.ru.srt"
                if not os.path.exists(subtitle_path):
                    subtitle_path = f"{base_path}.en.srt"
                if not os.path.exists(subtitle_path):
                    subtitle_path = None

            logger.info(f"--- [📥] Загрузка завершена. Видео: {os.path.basename(video_path)}, Сабы: {subtitle_path}")
            return video_path, subtitle_path
        except Exception as e:
            logger.error(f"❌ Ошибка скачивания: {e}")
            return None, None