FROM python:3.12-slim

# Системные утилиты (по минимуму) и очистка кэша apt
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Обновим pip и поставим зависимости (без кэша)
RUN python -m pip install --upgrade pip setuptools wheel

RUN pip install --no-cache-dir \
        fastapi \
        uvicorn[standard] \
        SQLAlchemy \
        psycopg[binary] \
        alembic \
        pydantic \
        email-validator \
        python-jose[cryptography] \
        passlib[bcrypt]==1.7.4 \
        bcrypt>=4.1.2

# Кладём код приложения
COPY app ./app

# Кладём alembic.ini рядом (корень рабочего каталога /app)
COPY alembic.ini ./alembic.ini

# PYTHONPATH чтобы импорты вида app.src.* работали
ENV PYTHONPATH=/app

# На проде буферизация логов выключена — попадает в stdout
ENV PYTHONUNBUFFERED=1
# (опционально) не писать .pyc
ENV PYTHONDONTWRITEBYTECODE=1

# (опционально) можно раскрыть порт
EXPOSE 8000

# Запуск API
CMD ["uvicorn", "app.src.main:app", "--host", "0.0.0.0", "--port", "8000"]