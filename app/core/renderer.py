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
        """Режет видео и делает кроп 9:16 бесплатно"""
        output_filename = f"clip_{job_id}_{int(start_time)}.mp4"
        output_path = os.path.join(self.output_dir, output_filename)
        duration = float(end_time) - float(start_time)

        # Фильтр: кроп центра под 9:16 и масштаб в 720p
        vf_chain = "crop=ih*9/16:ih:(iw-ow)/2:0,scale=720:1280"

        command = [
            "ffmpeg", "-y",
            "-ss", str(start_time),
            "-t", str(duration),
            "-i", local_video_path,
            "-vf", vf_chain,
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            output_path
        ]

        try:
            logger.info(f"--- [⚙️] FFmpeg: Рендер {output_filename}")
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