from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip
import PIL.Image
import os
import logging

# План Б: фикс для новых версий Pillow
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

logger = logging.getLogger(__name__)

class VideoRenderer:
    def __init__(self, output_dir="assets/clips"):
        self.output_dir = output_dir
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def create_short(self, input_path, segments, start_time, end_time, title, output_name):
        """Создает вертикальный клип с динамическими субтитрами"""
        logger.info(f"--- [🎬] Рендеринг клипа: {start_time} - {end_time}")
        
        full_video = VideoFileClip(input_path)
        video = full_video.subclip(start_time, end_time)
        
        # 1. Кроп под 9:16 и фикс размера
        w, h = video.size
        target_w = h * 9 / 16
        video_cropped = video.crop(x_center=w/2, width=target_w)
        video_vertical = video_cropped.resize(height=1920)

        # 2. Генерация динамических субтитров
        clips_to_composite = [video_vertical]
        
        for seg in segments:
            # Берем только те фразы, которые попадают в наш интервал
            if seg['start'] >= start_time and seg['end'] <= end_time:
                rel_start = seg['start'] - start_time
                rel_end = seg['end'] - start_time
                
                txt_clip = TextClip(
                    seg['text'].upper(),
                    fontsize=80,
                    color='yellow',
                    font='Arial-Bold',
                    stroke_color='black',
                    stroke_width=3,
                    method='caption',
                    size=(target_w * 0.8, None)
                ).set_start(rel_start).set_duration(rel_end - rel_start).set_position(('center', 1300))
                
                clips_to_composite.append(txt_clip)

        # 3. Добавляем заголовок (статичный сверху)
        title_clip = TextClip(
            title,
            fontsize=100,
            color='white',
            font='Arial-Bold',
            bg_color='red',
            size=(target_w * 0.9, None),
            method='caption'
        ).set_duration(video.duration).set_position(('center', 200))
        
        clips_to_composite.append(title_clip)

        # 4. Сборка и фикс для телефонов
        final_clip = CompositeVideoClip(clips_to_composite)
        output_path = os.path.join(self.output_dir, f"{output_name}.mp4")
        
        # КЛЮЧЕВОЙ МОМЕНТ: ffmpeg_params и pixel_format для мобилок
        final_clip.write_videofile(
            output_path, 
            codec="libx264", 
            audio_codec="aac", 
            fps=24, 
            temp_audiofile="temp-audio.m4a", 
            remove_temp=True,
            ffmpeg_params=["-pix_fmt", "yuv420p"] # Теперь откроется на iPhone
        )
        
        full_video.close()
        return output_path