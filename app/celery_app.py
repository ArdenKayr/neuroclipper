import os
from celery import Celery
from dotenv import load_dotenv

load_dotenv()

# Настройки Redis
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

app = Celery(
    "neuroclipper",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["core.tasks"] # Здесь будут лежать наши задачи
)

# Оптимизация: один воркер берет только одну задачу за раз
app.conf.worker_prefetch_multiplier = 1
app.conf.task_acks_late = True

if __name__ == "__main__":
    app.start()