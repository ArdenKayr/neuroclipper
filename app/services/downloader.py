import yt_dlp
import os
import time

class VideoDownloader:
    def __init__(self, download_path="assets/downloads"):
        self.download_path = download_path
        if not os.path.exists(self.download_path):
            os.makedirs(self.download_path)

    def download(self, url, job_id):
        # Добавляем timestamp, чтобы имя было уникальным: source_1_17089456.mp4
        timestamp = int(time.time())
        filename = f"source_{job_id}_{timestamp}"
        output_tmpl = os.path.join(self.download_path, f"{filename}.%(ext)s")
        
        ydl_opts = {
            'format': 'bestvideo[vcodec^=avc1]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': output_tmpl,
            'merge_output_format': 'mp4',
            'noplaylist': True,
            'quiet': True,
            'nooverwrites': False, # Разрешаем перезапись, если вдруг имя совпало
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return ydl.prepare_filename(info)
        except Exception as e:
            return None