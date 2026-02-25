import os
import subprocess
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VideoDownloader:
    def __init__(self, download_path: str = "assets/downloads"):
        self.download_path = download_path
        if not os.path.exists(self.download_path):
            os.makedirs(self.download_path)

    def download(self, url: str, filename: str) -> str:
        output_template = os.path.join(self.download_path, f"{filename}.%(ext)s")
        command = [
            "yt-dlp", "-f", "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "--merge-output-format", "mp4", "-o", output_template, url
        ]
        try:
            subprocess.run(command, check=True)
            expected_file = os.path.join(self.download_path, f"{filename}.mp4")
            return expected_file if os.path.exists(expected_file) else None
        except Exception as e:
            logger.error(f"Ошибка загрузки: {e}")
            return None