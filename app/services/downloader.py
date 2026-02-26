import yt_dlp
import os
import logging

logger = logging.getLogger(__name__)

class VideoDownloader:
    def __init__(self, download_path="assets/downloads"):
        self.download_path = download_path
        if not os.path.exists(self.download_path):
            os.makedirs(self.download_path)

    def download(self, url, filename):
        output_tmpl = os.path.join(self.download_path, f"{filename}.%(ext)s")
        
        # ФИКС: Принудительно запрашиваем H.264 (avc1), чтобы избежать AV1
        ydl_opts = {
            'format': 'bestvideo[vcodec^=avc1]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': output_tmpl,
            'merge_output_format': 'mp4',
            'noplaylist': True,
            'quiet': True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return ydl.prepare_filename(info)
        except Exception as e:
            logger.error(f"Ошибка загрузки: {e}")
            return None