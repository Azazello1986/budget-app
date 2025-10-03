import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# Подтягиваем Base из моделей
from app.db.models import Base  # <- важно: путь к вашим моделям

# Alembic Config object
config = context.config

# Логи Alembic (если в ini включены)
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Метаданные моделей для autogenerate
target_metadata = Base.metadata

def get_url() -> str:
    # Пробуем взять готовый DATABASE_URL (например: postgresql+psycopg2://user:pass@db:5432/budget)
    url = os.getenv("DATABASE_URL")
    if url:
        return url

    # Либо собираем из compose-переменных
    user = os.getenv("POSTGRES_USER", "budget_user")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")
    host = os.getenv("POSTGRES_HOST", "db")
    port = os.getenv("POSTGRES_PORT", "5432")
    name = os.getenv("POSTGRES_DB", "budget")
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{name}"

def run_migrations_offline():
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,       # сравнивать также типы колонок
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        future=True,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()