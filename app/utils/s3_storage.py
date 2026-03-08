import boto3
import os
import logging
from botocore.exceptions import ClientError
from tenacity import retry, stop_after_attempt, wait_exponential
from core.config import settings

logger = logging.getLogger(__name__)

class S3Storage:
    def __init__(self):
        self.s3 = boto3.client(
            's3',
            endpoint_url=settings.S3_ENDPOINT_URL,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            region_name="auto"
        )
        self.bucket = settings.S3_BUCKET_NAME
        self.public_url = settings.S3_PUBLIC_URL

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def upload_file(self, local_path, object_name=None):
        """Загружает файл в R2 с механизмом повторных попыток"""
        if object_name is None:
            object_name = os.path.basename(local_path)

        try:
            extra_args = {'ContentType': 'video/mp4'}
            self.s3.upload_file(local_path, self.bucket, object_name, ExtraArgs=extra_args)
            
            file_url = f"{self.public_url}/{object_name}"
            logger.info(f"--- [☁️] Файл загружен в R2: {file_url}")
            return file_url
        except ClientError as e:
            logger.error(f"❌ Ошибка S3 (попытка будет повторена): {e}")
            raise e # Для работы tenacity