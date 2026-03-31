FROM python:3.10-slim

# Системные зависимости
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    build-essential \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Создаем пользователя n_user
RUN useradd -m -s /bin/bash n_user

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

# Создаем папки и даем права
RUN mkdir -p assets/downloads assets/results logs && \
    chown -R n_user:n_user /app

ENV PYTHONPATH=/app/app
ENV PYTHONUNBUFFERED=1

USER n_user

CMD ["python", "app/bot/main.py"]