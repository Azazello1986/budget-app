from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.src.api import users, budgets, accounts, categories, steps, operations, auth

app = FastAPI()

# Все API доступны под префиксом /api
app.include_router(users.router,      prefix="/api/users",      tags=["users"])  # /api/users
app.include_router(budgets.router,    prefix="/api/budgets",    tags=["budgets"])  # /api/budgets
app.include_router(accounts.router,   prefix="/api/accounts",   tags=["accounts"])  # /api/accounts
app.include_router(categories.router, prefix="/api/categories", tags=["categories"])  # /api/categories
app.include_router(steps.router,      prefix="/api/steps",      tags=["steps"])  # /api/steps
app.include_router(operations.router, prefix="/api/operations", tags=["operations"])  # /api/operations
app.include_router(auth.router,       prefix="/api/auth",       tags=["auth"])  # /api/auth

@app.get("/api/health")
def health():
    return {"status": "ok"}

# GUI: раздаём статику с корня домена
# Важно: монтируем после роутов API, чтобы /api/* обрабатывалось приложением
app.mount("/", StaticFiles(directory="app/static", html=True), name="gui")