import logging
import subprocess
import os
import asyncio

logger = logging.getLogger(__name__)

class VideoRenderer:
    def __init__(self):
        self.output_dir = "assets/results"
        os.makedirs(self.output_dir, exist_ok=True)

    async def create_short(
        self, 
        local_video_path: str, 
        start_time: float, 
        end_time: float, 
        title: str, 
        job_id: int
    ) -> str:
        output_filename = f"clip_{job_id}_{int(start_time)}.mp4"
        output_path = os.path.join(self.output_dir, output_filename)
        
        # Увеличиваем "подушку безопасности" (padding)
        # Берем на 0.8 сек раньше и на 1.5 сек позже
        safe_start = max(0.0, float(start_time) - 0.8)
        safe_end = float(end_time) + 1.5
        duration = safe_end - safe_start

        # Фильтр: кроп центра под 9:16 и масштаб в 720p
        vf_chain = "crop=ih*9/16:ih:(iw-ow)/2:0,scale=720:1280"

        command = [
            "ffmpeg", "-y",
            "-ss", str(safe_start),
            "-i", local_video_path,
            "-t", str(duration),
            "-vf", vf_chain,
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            "-af", "aresample=async=1",  # Современный фикс рассинхрона аудио
            output_path
        ]

        try:
            logger.info(f"--- [⚙️] FFmpeg: Рендер {output_filename} (с {safe_start} по {safe_end} сек)")
            process = await asyncio.create_subprocess_exec(
                *command, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            _, stderr = await process.communicate()

            if process.returncode == 0:
                return output_path
            else:
                logger.error(f"❌ FFmpeg Error: {stderr.decode()}")
                return None
        except Exception as e:
            logger.error(f"❌ Ошибка рендера: {e}")
            return None