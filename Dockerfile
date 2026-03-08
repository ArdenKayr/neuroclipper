FROM python:3.10-slim

WORKDIR /app

# Установка системных зависимостей для сборки и работы видео-библиотек
RUN apt-get update && apt-get install -y ffmpeg git build-essential && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/app/app