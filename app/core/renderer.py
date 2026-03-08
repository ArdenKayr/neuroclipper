import os
import json
import logging
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from core.config import settings

logger = logging.getLogger(__name__)

class VideoRenderer:
    def __init__(self):
        self.creatomate_key = settings.CREATOMATE_API_KEY
        self.creatomate_template_id = settings.CREATOMATE_TEMPLATE_ID
        self.captions_api_key = settings.CAPTIONS_API_KEY

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _generate_captions(self, video_url: str, style: str) -> str:
        """Асинхронный вызов Captions.ai для генерации стилизованных субтитров (SRT/VTT)"""
        if not self.captions_api_key:
            logger.warning("⚠️ CAPTIONS_API_KEY не задан. Рендерим видео без субтитров.")
            return "" # Возвращаем пустоту, чтобы Creatomate не искал фейковый файл

        logger.info(f"--- [💬] Генерация субтитров Captions.ai (Стиль: {style})")
        async with httpx.AsyncClient() as client:
            # Здесь будет реальный вызов API Captions.ai, когда ты добавишь ключ
            # res = await client.post("https://api.captions.ai/v1/generate", headers={"x-api-key": self.captions_api_key})
            # return res.json().get('srt_url')
            
            # Пока API не подключено окончательно, даже с ключом отдаем пустоту для безопасности тестов
            return ""

    async def create_short(self, s3_url: str, start_time: float, end_time: float, title: str, job_id: int, local_filename: str, style: str = "dynamic", reframe_data: dict = None, is_last: bool = False):
        """Отправляет задачу на рендеринг в Creatomate с учетом стиля и Auto-Reframe"""
        url = "https://api.creatomate.com/v2/renders"
        headers = {
            "Authorization": f"Bearer {self.creatomate_key}",
            "Content-Type": "application/json"
        }
        
        # 1. Генерация субтитров перед рендером
        captions_url = await self._generate_captions(s3_url, style)
        
        # 2. Логика Auto-Reframe (если Vizard отдал координаты фокуса)
        scale = reframe_data.get("scale", "100%") if reframe_data else "150%"
        x_pos = reframe_data.get("x", "50%") if reframe_data else "50%"

        metadata = {
            "job_id": job_id,
            "title": title,
            "local_file": local_filename,
            "is_last": is_last,
            "style": style
        }
        
        modifications = {
            "Video-1.source": s3_url,
            "Video-1.trim_start": start_time,
            "Video-1.duration": end_time - start_time,
            "Video-1.scale": scale,  # Auto-Reframe Zoom
            "Video-1.x": x_pos,      # Auto-Reframe X-Axis
            "Text-Title.text": title.upper()
        }

        # Если мы получили реальную ссылку на субтитры, скармливаем их в слой Creatomate
        if captions_url:
            modifications["Subtitles.source"] = captions_url
            # Настройка шрифтов в зависимости от пресета
            if style == "dynamic":
                modifications["Subtitles.fill_color"] = "#FFFF00"
            elif style == "minimal":
                modifications["Subtitles.fill_color"] = "#FFFFFF"

        data = {
            "template_id": self.creatomate_template_id,
            "modifications": modifications,
            "metadata": json.dumps(metadata)
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=data, timeout=30.0)
                response.raise_for_status()
                res_json = response.json()
                render_id = res_json[0].get('id') if isinstance(res_json, list) else res_json.get('id')
                logger.info(f"--- [🎥] Рендер запущен в Creatomate (Task: {render_id}, Стиль: {style})")
                return render_id
        except Exception as e:
            logger.error(f"❌ Ошибка рендерера: {e}")
            return None