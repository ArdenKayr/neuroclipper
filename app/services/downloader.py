import yt_dlp
import os
import time
import logging
import socket

logger = logging.getLogger(__name__)

# --- ЯДЕРНЫЙ ФИКС СЕТИ ДЛЯ DOCKER ---
# Полностью отключаем IPv6 на уровне Python. 
# yt-dlp больше не попытается использовать сломанные маршруты Google.
old_getaddrinfo = socket.getaddrinfo

def ipv4_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    if family == socket.AF_UNSPEC:
        family = socket.AF_INET
    responses = old_getaddrinfo(host, port, family, type, proto, flags)
    return [res for res in responses if res[0] == socket.AF_INET]

socket.getaddrinfo = ipv4_getaddrinfo
# ------------------------------------

class VideoDownloader:
    def __init__(self, download_path="assets/downloads"):
        self.download_path = download_path
        if not os.path.exists(self.download_path):
            os.makedirs(self.download_path)

    def download_video(self, url: str, job_id: int):
        """
        Скачивает видео и ТОЛЬКО авторские субтитры (без автогенерации).
        Возвращает (путь_к_видео, путь_к_субтитрам)
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
            'writesubtitles': True,
            'subtitleslangs': ['ru', 'en'],
            'writeautomaticsub': False,  # Игнорируем мусорные авто-сабы
            'postprocessors': [{
                'key': 'FFmpegSubtitlesConvertor',
                'format': 'srt',
            }],
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                video_path = ydl.prepare_filename(info)
                
                # Поиск файла субтитров
                base_path = os.path.splitext(video_path)[0]
                sub_path = f"{base_path}.ru.srt"
                if not os.path.exists(sub_path):
                    sub_path = f"{base_path}.en.srt"
                
                final_sub_path = sub_path if sub_path and os.path.exists(sub_path) else None

            logger.info(f"--- [📥] Загрузка завершена. Субтитры найдены: {final_sub_path is not None}")
            return video_path, final_sub_path
        except Exception as e:
            logger.error(f"❌ Ошибка yt-dlp: {e}")
            return None, None