import logging
import subprocess
import os
import asyncio
import cv2

logger = logging.getLogger(__name__)

class VideoRenderer:
    def __init__(self):
        self.output_dir = "assets/results"
        os.makedirs(self.output_dir, exist_ok=True)

    async def detect_faces(self, video_path: str, timestamp: float):
        """Извлекает 1 кадр и ищет на нем координаты лиц"""
        frame_path = f"assets/temp_frame_{int(timestamp)}.jpg"
        
        # 1. Извлекаем кадр через FFmpeg
        cmd = [
            "ffmpeg", "-y", "-ss", str(timestamp), "-i", video_path, 
            "-vframes", "1", "-q:v", "2", frame_path
        ]
        process = await asyncio.create_subprocess_exec(*cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        await process.communicate()
        
        if not os.path.exists(frame_path):
            return []

        # 2. Ищем лица через OpenCV
        img = cv2.imread(frame_path)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Используем встроенный в OpenCV каскад Хаара
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        face_cascade = cv2.CascadeClassifier(cascade_path)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(50, 50))
        
        # Получаем размеры видео
        h, w = img.shape[:2]
        os.remove(frame_path)
        
        # Сортируем лица по размеру (от больших к меньшим)
        faces_list = sorted(faces, key=lambda f: f[2]*f[3], reverse=True)
        return faces_list, w, h

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
        
        safe_start = max(0.0, float(start_time) - 0.5)
        safe_end = float(end_time) + 0.5
        duration = safe_end - safe_start
        mid_time = safe_start + (duration / 2)

        # --- СМАРТ КРОП И СПЛИТСКРИН ---
        faces_data = await self.detect_faces(local_video_path, mid_time)
        filter_complex = ""
        
        if not faces_data or len(faces_data[0]) == 0:
            logger.info("--- [👁️] Лица не найдены, делаю стандартный кроп по центру.")
            filter_complex = "[0:v]crop=ih*9/16:ih:(iw-ow)/2:0,scale=720:1280[vout]"
        else:
            faces, vid_w, vid_h = faces_data
            
            if len(faces) >= 2:
                logger.info("--- [👯] Найдено 2+ лица! Включаю режим СПЛИТСКРИНА.")
                # Берем два самых больших лица и сортируем их по высоте (кто выше сидит в оригинале)
                top_two = sorted(faces[:2], key=lambda f: f[1])
                f1_x, f1_y, f1_w, f1_h = top_two[0]
                f2_x, f2_y, f2_w, f2_h = top_two[1]
                
                # Вычисляем центр каждого лица
                c1_x = f1_x + f1_w / 2
                c2_x = f2_x + f2_w / 2
                
                # Ширина и высота для каждой половинки (экран делим пополам)
                crop_h = vid_h / 2
                crop_w = crop_h * 9/16
                
                # Защита от выхода за границы экрана
                x1 = max(0, min(vid_w - crop_w, c1_x - crop_w / 2))
                x2 = max(0, min(vid_w - crop_w, c2_x - crop_w / 2))
                
                # Сложнейший граф: режем верх, режем низ, ставим их друг над другом
                filter_complex = (
                    f"[0:v]crop={crop_w}:{crop_h}:{x1}:0[top]; "
                    f"[0:v]crop={crop_w}:{crop_h}:{x2}:{vid_h/2}[bottom]; "
                    f"[top][bottom]vstack,scale=720:1280[vout]"
                )
            else:
                logger.info("--- [👤] Найдено 1 лицо! Делаю смарт-кроп на говорящего.")
                f_x, f_y, f_w, f_h = faces[0]
                center_x = f_x + f_w / 2
                
                crop_w = vid_h * 9/16
                x = max(0, min(vid_w - crop_w, center_x - crop_w / 2))
                
                filter_complex = f"[0:v]crop={crop_w}:{vid_h}:{x}:0,scale=720:1280[vout]"

        # --- СТУДИЙНЫЙ ЗВУК (Audio Enhance) ---
        # aresample - синхронизация
        # afftdn - удаление фонового шума
        # acompressor - выравнивание громкости
        # bass - добавление бархатности голосу
        audio_filters = "aresample=async=1,afftdn=nf=-25,acompressor=ratio=3:makeup=2,bass=g=5:f=110"

        command = [
            "ffmpeg", "-y",
            "-ss", str(safe_start),
            "-i", local_video_path,
            "-t", str(duration),
            "-filter_complex", filter_complex,
            "-map", "[vout]", "-map", "0:a",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-af", audio_filters,
            "-c:a", "aac", "-b:a", "128k",
            output_path
        ]

        try:
            logger.info(f"--- [⚙️] FFmpeg: Рендер {output_filename} (со смарт-кропом и аудио-улучшением)")
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