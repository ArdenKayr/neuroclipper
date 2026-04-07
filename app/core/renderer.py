import logging
import subprocess
import os
import asyncio
import cv2
import glob
import shutil
from services.whisper import WhisperService
from services.pexels import PexelsService

logger = logging.getLogger(__name__)

class VideoRenderer:
    def __init__(self):
        self.output_dir = "assets/results"
        os.makedirs(self.output_dir, exist_ok=True)
        self.whisper = WhisperService()
        self.pexels = PexelsService()

    async def analyze_tracking(self, video_path: str, start_time: float, duration: float):
        """Извлекает 1 кадр/сек, анализирует маршрут движения лиц и сглаживает его"""
        temp_dir = f"assets/temp_track_{int(start_time)}"
        os.makedirs(temp_dir, exist_ok=True)

        # Вытаскиваем 1 кадр в секунду для супер-быстрого анализа
        cmd = [
            "ffmpeg", "-y", "-ss", str(start_time), "-i", video_path,
            "-t", str(duration), "-vf", "fps=1", "-q:v", "2",
            f"{temp_dir}/frame_%04d.jpg"
        ]
        process = await asyncio.create_subprocess_exec(*cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        await process.communicate()

        frames = sorted(glob.glob(f"{temp_dir}/frame_*.jpg"))
        if not frames:
            shutil.rmtree(temp_dir, ignore_errors=True)
            return None

        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        face_cascade = cv2.CascadeClassifier(cascade_path)

        vid_w, vid_h = 0, 0
        detections = []

        for f_path in frames:
            img = cv2.imread(f_path)
            if img is None: continue
            if vid_w == 0:
                vid_h, vid_w = img.shape[:2]
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(50, 50))
            faces_list = sorted(faces, key=lambda f: f[2]*f[3], reverse=True)
            detections.append(faces_list)

        shutil.rmtree(temp_dir, ignore_errors=True)

        if not detections:
            return None

        # Если в 30%+ кадров есть 2 человека, включаем сплитскрин
        two_faces_count = sum(1 for faces in detections if len(faces) >= 2)
        is_split = two_faces_count >= len(detections) * 0.3

        centers_1 = []
        centers_2 = []
        last_c1 = vid_w / 2
        last_c2 = vid_w / 2

        # Собираем центры лиц, если лицо пропало - берем прошлое положение
        for faces in detections:
            if is_split:
                if len(faces) >= 2:
                    top_two = sorted(faces[:2], key=lambda f: f[1])
                    last_c1 = top_two[0][0] + top_two[0][2]/2
                    last_c2 = top_two[1][0] + top_two[1][2]/2
                elif len(faces) == 1:
                    last_c1 = faces[0][0] + faces[0][2]/2
            else:
                if len(faces) >= 1:
                    last_c1 = faces[0][0] + faces[0][2]/2

            centers_1.append(last_c1)
            if is_split:
                centers_2.append(last_c2)

        # Сглаживание координат (Moving Average), чтобы камера не дергалась
        def smooth(arr):
            if len(arr) < 3: return arr
            res = [arr[0]]
            for i in range(1, len(arr)-1):
                res.append((arr[i-1] + arr[i] + arr[i+1]) / 3.0)
            res.append(arr[-1])
            return res

        return {
            "is_split": is_split,
            "centers_1": smooth(centers_1),
            "centers_2": smooth(centers_2) if is_split else [],
            "vid_w": vid_w,
            "vid_h": vid_h
        }

    def _build_x_expr(self, centers, crop_w, vid_w):
        """Строит математическую функцию для FFmpeg для плавной интерполяции камеры"""
        if not centers: return "0"
        if len(centers) == 1:
            return str(round(max(0, min(vid_w - crop_w, centers[0] - crop_w / 2)), 1))

        parts = []
        for t in range(len(centers) - 1):
            c0 = round(max(0, min(vid_w - crop_w, centers[t] - crop_w / 2)), 1)
            c1 = round(max(0, min(vid_w - crop_w, centers[t+1] - crop_w / 2)), 1)
            # Линейная интерполяция между секундой t и t+1
            expr = f"(gte(t,{t})*lt(t,{t+1}))*({c0}+({c1}-{c0})*(t-{t}))"
            parts.append(expr)
            
        last_c = round(max(0, min(vid_w - crop_w, centers[-1] - crop_w / 2)), 1)
        parts.append(f"(gte(t,{len(centers)-1}))*{last_c}")
        
        return "+".join(parts)

    async def create_short(self, local_video_path: str, start_time: float, end_time: float, title: str, job_id: int, b_roll_query: str = None, dubbed_audio_path: str = None) -> str:
        output_filename = f"clip_{job_id}_{int(start_time)}.mp4"
        if dubbed_audio_path:
            output_filename = f"clip_{job_id}_{int(start_time)}_en.mp4"
            
        output_path = os.path.join(self.output_dir, output_filename)
        
        safe_start = max(0.0, float(start_time) - 0.5)
        safe_end = float(end_time) + 0.5
        duration = safe_end - safe_start

        ass_path = f"assets/temp_sub_{job_id}_{int(start_time)}.ass"
        has_subs = False
        
        try:
            # 1. АУДИО И СУБТИТРЫ
            if dubbed_audio_path and os.path.exists(dubbed_audio_path):
                audio_source = dubbed_audio_path
            else:
                audio_source = f"assets/temp_audio_{job_id}_{int(start_time)}.wav" 
                cmd_audio = [
                    "ffmpeg", "-y", "-ss", str(safe_start), "-i", local_video_path,
                    "-t", str(duration), "-vn", 
                    "-c:a", "pcm_s16le", "-ar", "16000", "-ac", "1", 
                    "-af", "aresample=async=1", 
                    audio_source
                ]
                process_aud = await asyncio.create_subprocess_exec(*cmd_audio, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                await process_aud.communicate()

            if os.path.exists(audio_source):
                logger.info("--- [📝] Отправляю аудио в Whisper для генерации субтитров...")
                ass_text = await self.whisper.generate_karaoke_ass(audio_source)
                if ass_text and len(ass_text.strip()) > 0:
                    with open(ass_path, "w", encoding="utf-8") as f:
                        f.write(ass_text)
                    has_subs = True
                
                if not dubbed_audio_path:
                    os.remove(audio_source)

            # 2. СКАЧИВАЕМ B-ROLL
            broll_path = None
            if b_roll_query:
                broll_temp = f"assets/temp_broll_{job_id}_{int(start_time)}.mp4"
                broll_path = await self.pexels.download_broll(b_roll_query, broll_temp)

            # 3. ДИНАМИЧЕСКИЙ КРОП С ПАНАРАМИРОВАНИЕМ
            track_data = await self.analyze_tracking(local_video_path, safe_start, duration)
            filters = []
            
            if not track_data:
                logger.info("--- [👁️] Лица не найдены, делаю стандартный кроп по центру.")
                filters.append("[0:v]setpts=PTS-STARTPTS,crop=ih*9/16:ih:(iw-ow)/2:0,scale=720:1280[bg]")
            else:
                is_split = track_data["is_split"]
                vid_w, vid_h = track_data["vid_w"], track_data["vid_h"]
                
                # Защита от нечетных пикселей (FFmpeg этого не любит)
                crop_w = int(vid_h * 9 / 16)
                if crop_w % 2 != 0: crop_w -= 1
                
                if is_split:
                    logger.info("--- [👯] Включаю ДИНАМИЧЕСКИЙ СПЛИТСКРИН с плавным слежением.")
                    crop_h = int(vid_h / 2)
                    if crop_h % 2 != 0: crop_h -= 1
                    
                    x1_expr = self._build_x_expr(track_data["centers_1"], crop_w, vid_w)
                    x2_expr = self._build_x_expr(track_data["centers_2"], crop_w, vid_w)
                    
                    filters.append(
                        f"[0:v]setpts=PTS-STARTPTS,split=2[v1][v2]; "
                        f"[v1]crop={crop_w}:{crop_h}:{x1_expr}:0[top]; "
                        f"[v2]crop={crop_w}:{crop_h}:{x2_expr}:{vid_h//2}[bottom]; "
                        f"[top][bottom]vstack,scale=720:1280[bg]"
                    )
                else:
                    logger.info("--- [👤] Включаю ДИНАМИЧЕСКИЙ СМАРТ-КРОП с плавным слежением.")
                    x_expr = self._build_x_expr(track_data["centers_1"], crop_w, vid_w)
                    
                    filters.append(f"[0:v]setpts=PTS-STARTPTS,crop={crop_w}:{vid_h}:{x_expr}:0,scale=720:1280[bg]")

            if broll_path:
                filters.append("[1:v]scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,setpts=PTS-STARTPTS[broll]")
                filters.append("[bg][broll]overlay=x=0:y=0:enable='between(t,1.5,4.5)':eof_action=pass[vid_broll]")
                bg_out = "[vid_broll]"
            else:
                bg_out = "[bg]"

            if has_subs:
                logger.info("--- [✨] Вшиваем субтитры в видео...")
                abs_ass_path = os.path.abspath(ass_path).replace('\\', '/')
                abs_ass_path = abs_ass_path.replace(':', '\\:')
                filters.append(f"{bg_out}subtitles='{abs_ass_path}'[vout]")
            else:
                filters.append(f"{bg_out}null[vout]")

            filter_complex = "; ".join(filters)

            # 4. ЗАПУСК FFMPEG
            command = [
                "ffmpeg", "-y",
                "-ss", str(safe_start),
                "-i", local_video_path
            ]
            
            if broll_path:
                command.extend(["-stream_loop", "-1", "-i", broll_path])
                
            if dubbed_audio_path:
                command.extend(["-i", dubbed_audio_path])
                audio_idx = 2 if broll_path else 1
                audio_map = f"{audio_idx}:a"
            else:
                audio_map = "0:a"
                
            command.extend([
                "-t", str(duration),
                "-filter_complex", filter_complex,
                "-map", "[vout]", "-map", audio_map,
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                "-c:a", "aac", "-b:a", "128k",
                "-af", "aresample=async=1",
                output_path
            ])

            logger.info(f"--- [⚙️] FFmpeg: Финальный рендер {output_filename}")
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
        finally:
            if os.path.exists(ass_path):
                try: os.remove(ass_path)
                except: pass
            if broll_path and os.path.exists(broll_path):
                try: os.remove(broll_path)
                except: pass