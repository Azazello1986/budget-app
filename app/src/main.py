from fastapi import FastAPI, APIRouter
from app.src.api import users, budgets, accounts, categories, steps, operations

app = FastAPI(title="Budget App")

# Группируем весь API под единым префиксом /api
api = APIRouter()

api.include_router(users.router,       prefix="/users",       tags=["users"])
api.include_router(budgets.router,     prefix="/budgets",     tags=["budgets"])
api.include_router(accounts.router,    prefix="/accounts",    tags=["accounts"])
api.include_router(categories.router,  prefix="/categories",  tags=["categories"])
api.include_router(steps.router,       prefix="/steps",       tags=["steps"])
api.include_router(operations.router,  prefix="/operations",  tags=["operations"])

@api.get("/health")
def health():
    return {"status": "ok"}

# Подвешиваем всё под /api
app.include_router(api, prefix="/api")