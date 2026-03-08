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

    def download_video(self, url: str, job_id: int) -> str:
        """
        Скачивает видео локально и возвращает путь к файлу.
        """
        timestamp = int(time.time())
        filename = f"source_{job_id}_{timestamp}"
        output_tmpl = os.path.join(self.download_path, f"{filename}.%(ext)s")
        
        ydl_opts = {
            # Ограничиваем качество до 720p для экономии места и ресурсов
            'format': 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': output_tmpl,
            'merge_output_format': 'mp4',
            'noplaylist': True,
            'quiet': True,
            'nooverwrites': False,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                local_path = ydl.prepare_filename(info)
            
            logger.info(f"--- [📥] Видео скачано локально: {local_path}")
            return local_path
        except Exception as e:
            logger.error(f"❌ Ошибка yt-dlp при скачивании: {e}")
            return None