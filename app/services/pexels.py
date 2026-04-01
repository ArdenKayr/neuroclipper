import httpx
import logging
import os
from core.config import settings

logger = logging.getLogger(__name__)

class PexelsService:
    def __init__(self):
        self.api_key = settings.PEXELS_API_KEY
        self.headers = {"Authorization": self.api_key} if self.api_key else {}

    async def download_broll(self, query: str, output_path: str) -> str:
        if not self.api_key:
            logger.warning("⚠️ PEXELS_API_KEY не установлен, пропускаем B-Roll.")
            return None
            
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Ищем вертикальное видео
                url = f"https://api.pexels.com/videos/search?query={query}&orientation=portrait&size=medium&per_page=3"
                res = await client.get(url, headers=self.headers)
                res.raise_for_status()
                data = res.json()
                
                if not data.get("videos"):
                    logger.warning(f"⚠️ Pexels: Ничего не найдено по запросу '{query}'")
                    return None
                
                # Берем лучшее HD-видео
                video_files = data["videos"][0].get("video_files", [])
                if not video_files: 
                    return None
                    
                video_files.sort(key=lambda x: x.get('height', 0), reverse=True)
                best_file = next((f for f in video_files if f.get("height", 0) <= 1920), video_files[0])
                
                download_url = best_file["link"]
                
                logger.info(f"--- [🎥] Скачиваю B-Roll '{query}' с Pexels...")
                video_res = await client.get(download_url)
                video_res.raise_for_status()
                
                with open(output_path, "wb") as f:
                    f.write(video_res.content)
                    
                return output_path
        except Exception as e:
            logger.error(f"❌ Ошибка Pexels API: {e}")
            return None