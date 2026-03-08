FROM python:3.10-slim

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копируем и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код проекта
COPY . .

# Создаем папки для логов и загрузок заранее
RUN mkdir -p assets/downloads logs

# Указываем PYTHONPATH, чтобы модули импортировались корректно
ENV PYTHONPATH=/app/app
ENV PYTHONUNBUFFERED=1

# По умолчанию запускаем бота (будет переопределено в docker-compose)
CMD ["python", "app/bot/main.py"]