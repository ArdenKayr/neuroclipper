import httpx
import logging
import os
from core.config import settings

logger = logging.getLogger(__name__)

class PexelsService:
    def __init__(self):
        self.api_key = settings.PEXELS_API_KEY

    async def download_broll(self, query: str, output_path: str) -> str:
        if not self.api_key:
            logger.warning("⚠️ PEXELS_API_KEY не установлен, пропускаем B-Roll.")
            return None
            
        try:
            # --- ШАГ 1: Поиск видео через API (С ключом авторизации) ---
            api_headers = {
                "Authorization": self.api_key
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                url = f"https://api.pexels.com/videos/search?query={query}&orientation=portrait&size=medium&per_page=3"
                res = await client.get(url, headers=api_headers)
                res.raise_for_status()
                data = res.json()
                
                if not data.get("videos"):
                    logger.warning(f"⚠️ Pexels: Ничего не найдено по запросу '{query}'")
                    return None
                
                video_files = data["videos"][0].get("video_files", [])
                if not video_files: 
                    return None
                    
                # Ищем вертикальное видео лучшего качества (до 1080x1920)
                video_files.sort(key=lambda x: x.get('height', 0), reverse=True)
                best_file = next((f for f in video_files if f.get("height", 0) <= 1920), video_files[0])
                
                download_url = best_file["link"]
                logger.info(f"--- [🎥] Найдено видео: {download_url}")
                logger.info(f"--- [🎥] Скачиваю B-Roll '{query}' как обычный браузер...")

            # --- ШАГ 2: Скачивание видео (БЕЗ ключа авторизации, маскируемся под браузер) ---
            download_headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Accept": "video/webm,video/mp4,video/*;q=0.9,application/json,text/plain,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5"
            }
            
            # Обязательно follow_redirects=True, так как Pexels делает перенаправление на сервера AWS
            async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as dl_client:
                video_res = await dl_client.get(download_url, headers=download_headers)
                video_res.raise_for_status()
                
                with open(output_path, "wb") as f:
                    f.write(video_res.content)
                    
            return output_path

        except Exception as e:
            logger.error(f"❌ Ошибка Pexels API: {e}")
            return None