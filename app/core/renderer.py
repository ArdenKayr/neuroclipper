from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip
import os
import logging

logger = logging.getLogger(__name__)

class VideoRenderer:
    def __init__(self, output_dir="assets/clips"):
        self.output_dir = output_dir
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def create_short(self, input_path, start_time, end_time, text, output_name):
        """Создает вертикальный клип с субтитрами"""
        logger.info(f"--- [🎬] Рендеринг клипа: {start_time} - {end_time}")
        
        # 1. Загружаем видео и вырезаем фрагмент
        video = VideoFileClip(input_path).subclip(start_time, end_time)
        
        # 2. Кропаем под вертикальный формат (9:16)
        # Берем центр кадра
        w, h = video.size
        target_w = h * 9 / 16
        video_cropped = video.crop(x_center=w/2, width=target_w)
        video_vertical = video_cropped.resize(height=1920) # Стандарт TikTok/Reels

        # 3. Генерируем субтитры
        txt_clip = TextClip(
            text, 
            fontsize=70, 
            color='yellow', 
            font='Arial-Bold',
            stroke_color='black',
            stroke_width=2,
            method='caption',
            size=(target_w*0.8, None)
        ).set_position(('center', 1400)).set_duration(video.duration)

        # 4. Собираем всё вместе
        final_clip = CompositeVideoClip([video_vertical, txt_clip])
        
        output_path = os.path.join(self.output_dir, f"{output_name}.mp4")
        final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac", fps=24)
        
        return output_path