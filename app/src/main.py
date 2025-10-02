from fastapi import FastAPI
# Статика больше не нужна в API (её отдаёт Caddy на /),
# но импорт оставить не обязательно. Уберём, чтобы не тянуть лишнее.
# from fastapi.staticfiles import StaticFiles

from app.src.api import users, budgets, accounts, categories, steps, operations

# Важно: root_path указывает базовый путь за прокси (для корректных ссылок в OpenAPI и url_for)
app = FastAPI(root_path="/api")

# Роутеры API (пути внутри контейнера без /api — прокси его срезает)
app.include_router(users.router,       prefix="/users",       tags=["users"])
app.include_router(budgets.router,     prefix="/budgets",     tags=["budgets"])
app.include_router(accounts.router,    prefix="/accounts",    tags=["accounts"])
app.include_router(categories.router,  prefix="/categories",  tags=["categories"])
app.include_router(steps.router,       prefix="/steps",       tags=["steps"])
app.include_router(operations.router,  prefix="/operations",  tags=["operations"])

@app.get("/health")
def health():
    return {"status": "ok"}

# Раздачу GUI убрали из FastAPI — теперь статику отдаёт Caddy по корню домена.
# Если очень нужно оставить локальную раздачу, раскомментируй:
# from fastapi.staticfiles import StaticFiles
# app.mount("/gui", StaticFiles(directory="app/static", html=True), name="gui")