import yt_dlp
import os
import time
import logging
from utils.s3_storage import S3Storage

logger = logging.getLogger(__name__)

class VideoDownloader:
    def __init__(self, download_path="assets/downloads"):
        self.download_path = download_path
        self.s3 = S3Storage()
        if not os.path.exists(self.download_path):
            os.makedirs(self.download_path)

    def download(self, url, job_id):
        """Скачивает видео, загружает в R2 и возвращает (local_path, s3_url)"""
        timestamp = int(time.time())
        filename = f"source_{job_id}_{timestamp}"
        output_tmpl = os.path.join(self.download_path, f"{filename}.%(ext)s")
        
        ydl_opts = {
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
            
            # Загружаем в R2
            s3_url = self.s3.upload_file(local_path)
            
            return local_path, s3_url
        except Exception as e:
            logger.error(f"❌ Ошибка скачивания или S3: {e}")
            return None, None