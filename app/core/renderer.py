import logging
import subprocess
import os
import asyncio
import cv2
from services.whisper import WhisperService
from services.pexels import PexelsService

logger = logging.getLogger(__name__)

class VideoRenderer:
    def __init__(self):
        self.output_dir = "assets/results"
        os.makedirs(self.output_dir, exist_ok=True)
        self.whisper = WhisperService()
        self.pexels = PexelsService()

    async def detect_faces(self, video_path: str, timestamp: float):
        frame_path = f"assets/temp_frame_{int(timestamp)}.jpg"
        
        cmd = [
            "ffmpeg", "-y", "-ss", str(timestamp), "-i", video_path, 
            "-vframes", "1", "-q:v", "2", frame_path
        ]
        process = await asyncio.create_subprocess_exec(*cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        await process.communicate()
        
        if not os.path.exists(frame_path):
            return []

        img = cv2.imread(frame_path)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        face_cascade = cv2.CascadeClassifier(cascade_path)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(50, 50))
        
        h, w = img.shape[:2]
        os.remove(frame_path)
        
        faces_list = sorted(faces, key=lambda f: f[2]*f[3], reverse=True)
        return faces_list, w, h

    async def create_short(self, local_video_path: str, start_time: float, end_time: float, title: str, job_id: int, b_roll_query: str = None, dubbed_audio_path: str = None) -> str:
        output_filename = f"clip_{job_id}_{int(start_time)}.mp4"
        if dubbed_audio_path:
            output_filename = f"clip_{job_id}_{int(start_time)}_en.mp4"
            
        output_path = os.path.join(self.output_dir, output_filename)
        
        safe_start = max(0.0, float(start_time) - 0.5)
        safe_end = float(end_time) + 0.5
        duration = safe_end - safe_start
        mid_time = safe_start + (duration / 2)

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

            # 3. СБОРКА ГРАФА ФИЛЬТРОВ FFmpeg
            faces_data = await self.detect_faces(local_video_path, mid_time)
            filters = []
            
            if not faces_data or len(faces_data[0]) == 0:
                logger.info("--- [👁️] Лица не найдены, делаю стандартный кроп.")
                filters.append("[0:v]setpts=PTS-STARTPTS,crop=ih*9/16:ih:(iw-ow)/2:0,scale=720:1280[bg]")
            else:
                faces, vid_w, vid_h = faces_data
                if len(faces) >= 2:
                    logger.info("--- [👯] Найдено 2+ лица! Включаю режим СПЛИТСКРИНА.")
                    top_two = sorted(faces[:2], key=lambda f: f[1])
                    f1_x, f1_y, f1_w, f1_h = top_two[0]
                    f2_x, f2_y, f2_w, f2_h = top_two[1]
                    
                    c1_x = f1_x + f1_w / 2
                    c2_x = f2_x + f2_w / 2
                    crop_h = vid_h / 2
                    
                    # ИСПРАВЛЕНИЕ: Ширина кропа рассчитывается от полной высоты видео, а не от половины!
                    crop_w = vid_h * 9 / 16
                    
                    x1 = max(0, min(vid_w - crop_w, c1_x - crop_w / 2))
                    x2 = max(0, min(vid_w - crop_w, c2_x - crop_w / 2))
                    
                    filters.append(
                        f"[0:v]setpts=PTS-STARTPTS,split=2[v1][v2]; "
                        f"[v1]crop={crop_w}:{crop_h}:{x1}:0[top]; "
                        f"[v2]crop={crop_w}:{crop_h}:{x2}:{vid_h/2}[bottom]; "
                        f"[top][bottom]vstack,scale=720:1280[bg]"
                    )
                else:
                    logger.info("--- [👤] Найдено 1 лицо! Делаю смарт-кроп.")
                    f_x, f_y, f_w, f_h = faces[0]
                    center_x = f_x + f_w / 2
                    crop_w = vid_h * 9/16
                    x = max(0, min(vid_w - crop_w, center_x - crop_w / 2))
                    
                    filters.append(f"[0:v]setpts=PTS-STARTPTS,crop={crop_w}:{vid_h}:{x}:0,scale=720:1280[bg]")

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