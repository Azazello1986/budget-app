from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware  # ← CORS
from app.src.api import (
    users,
    budgets,
    accounts,
    categories,
    steps,
    operations,
    auth,
)

app = FastAPI(title="Budget API")

# --- CORS ---
# Разрешаем фронту с budget.zotkin.me ходить на API.
# Если будешь открывать GUI и с других хостов — добавь их сюда.
allowed_origins = [
    "https://budget.zotkin.me",
    "http://budget.zotkin.me",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,          # для cookie-сессий
    allow_methods=["*"],             # позволяем все методы (GET/POST/PUT/DELETE/OPTIONS…)
    allow_headers=["*"],             # позволяем любые заголовки
)

# --- Роутеры под /api ---
app.include_router(users.router,      prefix="/api/users",      tags=["users"])
app.include_router(budgets.router,    prefix="/api/budgets",    tags=["budgets"])
app.include_router(accounts.router,   prefix="/api/accounts",   tags=["accounts"])
app.include_router(categories.router, prefix="/api/categories", tags=["categories"])
app.include_router(steps.router,      prefix="/api/steps",      tags=["steps"])
app.include_router(operations.router, prefix="/api/operations", tags=["operations"])
app.include_router(auth.router,       prefix="/api/auth",       tags=["auth"])

@app.get("/api/health", tags=["meta"])
def health():
    return {"status": "ok"}

# ВАЖНО: статику отдаёт Caddy, поэтому здесь ничего не монтируем.