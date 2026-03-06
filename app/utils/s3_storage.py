import boto3
import os
import logging
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class S3Storage:
    def __init__(self):
        # Cloudflare R2 требует явного указания endpoint_url
        self.s3 = boto3.client(
            's3',
            endpoint_url=os.getenv("S3_ENDPOINT_URL"),
            aws_access_key_id=os.getenv("S3_ACCESS_KEY"),
            aws_secret_access_key=os.getenv("S3_SECRET_KEY"),
            region_name="auto"
        )
        self.bucket = os.getenv("S3_BUCKET_NAME")
        self.public_url = os.getenv("S3_PUBLIC_URL")

    def upload_file(self, local_path, object_name=None):
        """Загружает файл в R2 и возвращает публичную ссылку"""
        if object_name is None:
            object_name = os.path.basename(local_path)

        try:
            extra_args = {'ContentType': 'video/mp4'}
            self.s3.upload_file(local_path, self.bucket, object_name, ExtraArgs=extra_args)
            
            file_url = f"{self.public_url}/{object_name}"
            logger.info(f"--- [☁️] Файл успешно загружен в R2: {file_url}")
            return file_url
        except ClientError as e:
            logger.error(f"❌ Ошибка загрузки в R2: {e}")
            return None