import logging
import asyncio
import os
import subprocess
from celery_app import app as celery_app
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from models.db_models import Job, User
from core.analyzer import AIAnalyzer
from core.renderer import VideoRenderer
from services.whisper import WhisperService
from services.llm import SmartLLMService
from services.tts import TTSService
from aiogram import Bot
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from core.config import settings

logger = logging.getLogger(__name__)

async def _async_process_job(job_id: int):
    # 1. ИЗОЛИРОВАННАЯ БД
    db_url = settings.DATABASE_URL
    if db_url and db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    local_engine = create_async_engine(db_url, pool_pre_ping=True)
    LocalSession = async_sessionmaker(bind=local_engine, expire_on_commit=False)
    
    bot = Bot(token=settings.BOT_TOKEN)

    try:
        async with LocalSession() as session:
            result = await session.execute(
                select(Job, User).join(User, Job.user_id == User.id).where(Job.id == job_id)
            )
            data = result.first()
            if not data: return
            job, user = data

            status_msg = await bot.send_message(
                chat_id=user.tg_id, 
                text="⏳ **Видео скачано!**\nСлушаю аудио и ищу виральные моменты через ИИ...", 
                parse_mode="Markdown"
            )

            analyzer = AIAnalyzer()
            highlights, local_raw_path, _ = await analyzer.find_visual_highlights(job.input_url, job.id)

            if not highlights or not local_raw_path:
                await bot.edit_message_text(
                    "❌ Не удалось проанализировать видео. Возможно, там нет речи.",
                    chat_id=user.tg_id, message_id=status_msg.message_id
                )
                raise Exception("Анализ не удался")

            await bot.edit_message_text(
                f"✅ **Найдено {len(highlights)} хайлайтов!**\nНачинаю нарезку и обработку кадров (FFmpeg)...",
                chat_id=user.tg_id, message_id=status_msg.message_id, parse_mode="Markdown"
            )

            renderer = VideoRenderer()
            for i, clip in enumerate(highlights[:3]):
                final_path = await renderer.create_short(
                    local_video_path=local_raw_path,
                    start_time=clip['start'],
                    end_time=clip['end'],
                    title=clip.get('title', f'Clip {i+1}'),
                    job_id=job.id
                )

                if final_path and os.path.exists(final_path):
                    video_file = FSInputFile(final_path)
                    caption = f"🎬 **Клип №{i+1}**\n📌 {clip.get('title')}"
                    if clip.get('reason'):
                        caption += f"\n💡 {clip.get('reason')}"
                    
                    # --- СОЗДАЕМ КНОПКУ ДЛЯ АНГЛИЙСКОЙ ОЗВУЧКИ ---
                    markup = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(
                            text="🇺🇸 Сделать на английском", 
                            callback_data=f"dub_{job.id}_{clip['start']}_{clip['end']}"
                        )]
                    ])
                        
                    await bot.send_video(
                        chat_id=user.tg_id, 
                        video=video_file, 
                        caption=caption,
                        reply_markup=markup
                    )
                    os.remove(final_path)

            if os.path.exists(local_raw_path):
                os.remove(local_raw_path)

            job.status = 'completed'
            await session.commit()
            
    except Exception as e:
        logger.error(f"❌ Ошибка задачи {job_id}: {e}")
        try:
            if 'user' in locals():
                await bot.send_message(user.tg_id, "⚠️ Произошла ошибка при обработке видео.")
        except Exception:
            pass
    finally:
        await local_engine.dispose()
        await bot.session.close()

# --- НОВАЯ ЗАДАЧА: АНГЛИЙСКИЙ ДАББИНГ ---
async def _async_dub_job(job_id: int, start_time: float, end_time: float, tg_id: int):
    db_url = settings.DATABASE_URL
    if db_url and db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    local_engine = create_async_engine(db_url, pool_pre_ping=True)
    LocalSession = async_sessionmaker(bind=local_engine, expire_on_commit=False)
    bot = Bot(token=settings.BOT_TOKEN)
    
    try:
        async with LocalSession() as session:
            result = await session.execute(select(Job).where(Job.id == job_id))
            job = result.scalar_one_or_none()
            if not job: return
            
        status_msg = await bot.send_message(chat_id=tg_id, text="📥 Скачиваю исходник для перевода...")
        
        # 1. Скачиваем исходник (yt-dlp сделает это быстро)
        clip_raw_path = f"assets/downloads/raw_dub_{job_id}_{int(start_time)}.mp4"
        cmd_dl = [
            "yt-dlp", "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4",
            job.input_url, "-o", clip_raw_path
        ]
        proc = await asyncio.create_subprocess_exec(*cmd_dl, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        await proc.communicate()
        
        if not os.path.exists(clip_raw_path):
            raise Exception("Не удалось скачать исходное видео для даббинга.")
            
        await bot.edit_message_text("📝 Распознаю и перевожу текст...", chat_id=tg_id, message_id=status_msg.message_id)
        
        whisper = WhisperService()
        llm = SmartLLMService()
        tts = TTSService()
        renderer = VideoRenderer()
        
        # 2. Извлекаем аудио ТОЛЬКО нужного фрагмента
        duration = end_time - start_time
        temp_audio = f"assets/temp_dub_audio_{job_id}.mp3"
        os.system(f"ffmpeg -y -ss {start_time} -i {clip_raw_path} -t {duration} -vn -c:a libmp3lame -b:a 128k {temp_audio}")
        
        # 3. Распознаем русскую речь
        ru_text = await whisper.transcribe(temp_audio)
        if os.path.exists(temp_audio): os.remove(temp_audio)
        
        # 4. Переводим
        await bot.edit_message_text("🎙️ Генерирую американскую озвучку...", chat_id=tg_id, message_id=status_msg.message_id)
        en_text = await llm.translate_to_english(ru_text)
        
        # 5. Озвучиваем нейроголосом
        tts_audio_path = f"assets/tts_{job_id}_{int(start_time)}.mp3"
        await tts.generate_audio(en_text, tts_audio_path)
        
        # 6. Финальный рендер
        await bot.edit_message_text("⚙️ Вшиваю звук и английские субтитры в видео...", chat_id=tg_id, message_id=status_msg.message_id)
        
        final_path = await renderer.create_short(
            local_video_path=clip_raw_path,
            start_time=start_time,
            end_time=end_time,
            title="English Dub",
            job_id=job_id,
            dubbed_audio_path=tts_audio_path
        )
        
        if final_path and os.path.exists(final_path):
            await bot.send_video(
                chat_id=tg_id, 
                video=FSInputFile(final_path), 
                caption="🇺🇸 **Твоя английская версия готова!**\nТеперь можно покорять западный YouTube Shorts."
            )
            os.remove(final_path)
            
        # Уборка
        if os.path.exists(clip_raw_path): os.remove(clip_raw_path)
        if os.path.exists(tts_audio_path): os.remove(tts_audio_path)
        
    except Exception as e:
        logger.error(f"❌ Ошибка даббинга: {e}")
        await bot.send_message(tg_id, "⚠️ Произошла ошибка при создании английской версии.")
    finally:
        await local_engine.dispose()
        await bot.session.close()

@celery_app.task(name="process_video_job")
def process_video_job(job_id):
    return asyncio.run(_async_process_job(job_id))

@celery_app.task(name="dub_video_job")
def dub_video_job(job_id, start_time, end_time, tg_id):
    return asyncio.run(_async_dub_job(job_id, start_time, end_time, tg_id))