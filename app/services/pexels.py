import httpx
import logging
import os
from core.config import settings

logger = logging.getLogger(__name__)

class PexelsService:
    def __init__(self):
        self.api_key = settings.PEXELS_API_KEY
        # Добавляем User-Agent, чтобы CDN Pexels думал, что мы обычный браузер Chrome
        self.headers = {
            "Authorization": self.api_key if self.api_key else "",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    async def download_broll(self, query: str, output_path: str) -> str:
        if not self.api_key:
            logger.warning("⚠️ PEXELS_API_KEY не установлен, пропускаем B-Roll.")
            return None
            
        try:
            # Обязательно follow_redirects=True, так как Pexels перенаправляет ссылки
            async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
                url = f"https://api.pexels.com/videos/search?query={query}&orientation=portrait&size=medium&per_page=3"
                res = await client.get(url, headers=self.headers)
                res.raise_for_status()
                data = res.json()
                
                if not data.get("videos"):
                    logger.warning(f"⚠️ Pexels: Ничего не найдено по запросу '{query}'")
                    return None
                
                video_files = data["videos"][0].get("video_files", [])
                if not video_files: 
                    return None
                    
                video_files.sort(key=lambda x: x.get('height', 0), reverse=True)
                best_file = next((f for f in video_files if f.get("height", 0) <= 1920), video_files[0])
                
                download_url = best_file["link"]
                
                logger.info(f"--- [🎥] Скачиваю B-Roll '{query}' с Pexels...")
                
                # Для скачивания самого видео используем только User-Agent (без API ключа, чтобы не смущать CDN)
                cdn_headers = {"User-Agent": self.headers["User-Agent"]}
                video_res = await client.get(download_url, headers=cdn_headers)
                video_res.raise_for_status()
                
                with open(output_path, "wb") as f:
                    f.write(video_res.content)
                    
                return output_path
        except Exception as e:
            logger.error(f"❌ Ошибка Pexels API: {e}")
            return None