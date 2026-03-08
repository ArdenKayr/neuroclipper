import os
import time
import logging
from datetime import datetime, timedelta
import boto3
from core.config import settings

logger = logging.getLogger(__name__)

class CleanupService:
    def __init__(self):
        self.download_dir = os.path.join(os.getcwd(), "assets/downloads")
        self.threshold_days = settings.CLEANUP_THRESHOLD_DAYS
        
        # Инициализация клиента S3 для очистки облака
        self.s3_client = boto3.client(
            's3',
            endpoint_url=settings.S3_ENDPOINT_URL,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            region_name="auto"
        )
        self.bucket = settings.S3_BUCKET_NAME

    def clean_local_storage(self) -> int:
        """Удаляет старые локальные файлы видео из assets/downloads"""
        if not os.path.exists(self.download_dir):
            logger.warning(f"⚠️ Папка {self.download_dir} не найдена для очистки.")
            return 0

        count = 0
        now = time.time()
        # Файлы старше N дней
        seconds_threshold = self.threshold_days * 86400

        for filename in os.listdir(self.download_dir):
            file_path = os.path.join(self.download_dir, filename)
            # Пропускаем, если это не файл (например, папка)
            if not os.path.isfile(file_path):
                continue
                
            if os.stat(file_path).st_mtime < (now - seconds_threshold):
                try:
                    os.remove(file_path)
                    logger.info(f"🗑️ Удален локальный файл: {filename}")
                    count += 1
                except Exception as e:
                    logger.error(f"❌ Ошибка при удалении файла {filename}: {e}")
        
        return count

    def clean_s3_storage(self) -> int:
        """Удаляет старые объекты из Cloudflare R2"""
        count = 0
        try:
            # Получаем список объектов в бакете
            paginator = self.s3_client.get_paginator('list_objects_v2')
            threshold_date = datetime.now().astimezone() - timedelta(days=self.threshold_days)

            for page in paginator.paginate(Bucket=self.bucket):
                if 'Contents' not in page:
                    continue

                for obj in page['Contents']:
                    # Если объект старше порога — удаляем
                    if obj['LastModified'] < threshold_date:
                        self.s3_client.delete_object(Bucket=self.bucket, Key=obj['Key'])
                        logger.info(f"☁️🗑️ Удален объект из R2: {obj['Key']}")
                        count += 1
        except Exception as e:
            logger.error(f"❌ Ошибка при очистке S3: {e}")
            
        return count

    def run_full_cleanup(self):
        """Запуск полной очистки всех хранилищ"""
        logger.info("--- [🧹] Запуск плановой очистки хранилищ...")
        local_deleted = self.clean_local_storage()
        s3_deleted = self.clean_s3_storage()
        logger.info(f"--- [✅] Очистка завершена. Удалено локально: {local_deleted}, в S3: {s3_deleted}")
        return local_deleted, s3_deleted