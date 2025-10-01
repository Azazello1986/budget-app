FROM python:3.12-slim
WORKDIR /app

# (опционально) системные тулзы для сборки колёс — часто не требуются, но полезны
RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
 && rm -rf /var/lib/apt/lists/*

# Бэкенд-зависимости
RUN pip install --no-cache-dir \
    fastapi uvicorn[standard] \
    SQLAlchemy psycopg[binary] alembic pydantic email-validator

# Кладём код
COPY app ./app

# Импорты ищут внутри /app
ENV PYTHONPATH=/app

# Стартуем FastAPI
CMD ["uvicorn", "app.src.main:app", "--host", "0.0.0.0", "--port", "8000"]