from __future__ import annotations

from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware

# Подроутеры
from app.src.api import (
    auth,
    users,
    budgets,
    accounts,
    categories,
    steps,
    operations,
)

app = FastAPI(title="Budget App API", version="0.1.0")

# CORS — чтобы фронт мог ходить в API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_root():
    return {"status": "ok"}

# Единый префикс для всего API
api = APIRouter(prefix="/api")

# Явные префиксы для каждого роутера
api.include_router(auth.router,       prefix="/auth",       tags=["auth"])        # /api/auth/...
api.include_router(users.router,      prefix="/users",      tags=["users"])       # /api/users/...
api.include_router(budgets.router,    prefix="/budgets",    tags=["budgets"])     # /api/budgets/...
api.include_router(accounts.router,   prefix="/accounts",   tags=["accounts"])    # /api/accounts/...
api.include_router(categories.router, prefix="/categories", tags=["categories"])  # /api/categories/...
api.include_router(steps.router,      prefix="/steps",      tags=["steps"])       # /api/steps/...
api.include_router(operations.router, prefix="/operations", tags=["operations"])  # /api/operations/...

# Подключаем агрегатор к приложению
app.include_router(api)