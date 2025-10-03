from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import APIRouter

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
allowed_origins = [
    "https://budget.zotkin.me",
    "http://budget.zotkin.me",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API роутер с единым префиксом /api ---
api = APIRouter(prefix="/api")

# если внутри модулей роутеров пути такие:
#   users:      "/users"      (или без префикса, но с @router.get("/..."))
#   budgets:    "/budgets"
#   accounts:   "/accounts"
#   categories: "/categories"
#   steps:      "/steps"
#   operations: "/operations"
#   auth:       "/auth"
# то просто подключаем их без дополнительного '/api' здесь:
api.include_router(users.router,      tags=["users"])
api.include_router(budgets.router,    tags=["budgets"])
api.include_router(accounts.router,   tags=["accounts"])
api.include_router(categories.router, tags=["categories"])
api.include_router(steps.router,      tags=["steps"])
api.include_router(operations.router, tags=["operations"])
api.include_router(auth.router,       tags=["auth"])

# Регистрируем общий /api в приложение
app.include_router(api)

@app.get("/api/health", tags=["meta"])
def health():
    return {"status": "ok"}