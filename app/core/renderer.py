from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip
import PIL.Image
import os
import logging

# План Б: фикс для новых версий Pillow (ANTIALIAS удален в 10.0.0)
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

logger = logging.getLogger(__name__)

class VideoRenderer:
    def __init__(self, output_dir="assets/clips"):
        self.output_dir = output_dir
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def create_short(self, input_path, segments, start_time, end_time, title, output_name):
        """Создает вертикальный клип с динамическими субтитрами и гарантией четного разрешения"""
        logger.info(f"--- [🎬] Рендеринг клипа: {start_time} - {end_time}")
        
        full_video = VideoFileClip(input_path)
        video = full_video.subclip(start_time, end_time)
        
        # 1. Расчет размеров для 9:16
        w, h = video.size
        target_h = h
        target_w = int(h * 9 / 16)

        # ФИКС: Делаем ширину и высоту четными (кратными 2)
        # Если число нечетное, вычитаем 1
        if target_w % 2 != 0: target_w -= 1
        if target_h % 2 != 0: target_h -= 1
        
        # 2. Кроп и ресайз
        video_cropped = video.crop(x_center=w/2, width=target_w, height=target_h)
        # Принудительно задаем четный размер при ресайзе, если он нужен
        video_vertical = video_cropped.resize(height=target_h)

        # 3. Генерация динамических субтитров
        clips_to_composite = [video_vertical]
        
        for seg in segments:
            # Берем фразы, попадающие в интервал клипа
            if seg['start'] >= start_time and seg['end'] <= end_time:
                rel_start = seg['start'] - start_time
                rel_end = seg['end'] - start_time
                
                # Защита от слишком коротких сегментов
                duration = rel_end - rel_start
                if duration <= 0: continue

                txt_clip = TextClip(
                    seg['text'].strip().upper(),
                    fontsize=70,
                    color='yellow',
                    font='Arial-Bold',
                    stroke_color='black',
                    stroke_width=2,
                    method='caption',
                    size=(target_w * 0.8, None)
                ).set_start(rel_start).set_duration(duration).set_position(('center', int(target_h * 0.7)))
                
                clips_to_composite.append(txt_clip)

        # 4. Добавляем плашку с заголовком сверху
        title_clip = TextClip(
            title.upper(),
            fontsize=80,
            color='white',
            font='Arial-Bold',
            bg_color='red',
            size=(target_w * 0.9, None),
            method='caption'
        ).set_duration(video.duration).set_position(('center', int(target_h * 0.1)))
        
        clips_to_composite.append(title_clip)

        # 5. Сборка и фикс для телефонов (yuv420p)
        final_clip = CompositeVideoClip(clips_to_composite, size=(target_w, target_h))
        output_path = os.path.join(self.output_dir, f"{output_name}.mp4")
        
        final_clip.write_videofile(
            output_path, 
            codec="libx264", 
            audio_codec="aac", 
            fps=24, 
            temp_audiofile=f"temp-audio-{output_name}.m4a", 
            remove_temp=True,
            ffmpeg_params=["-pix_fmt", "yuv420p"]
        )
        
        full_video.close()
        return output_path