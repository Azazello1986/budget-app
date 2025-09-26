#!/usr/bin/env bash
set -euo pipefail
cd /opt/budget-app

# 1) Обновить код (для варианта A — pull)
git fetch --all || true
git reset --hard origin/main || true

# 2) Собрать/обновить контейнеры
docker compose pull || true
docker compose up -d --build

# 3) Миграции (если уже подключишь Alembic)
if docker compose exec -T api bash -lc 'command -v alembic >/dev/null 2>&1'; then
  docker compose exec -T api alembic upgrade head || true
fi

# 4) Уборка висячих образов
docker image prune -f || true

echo "Deploy OK"

