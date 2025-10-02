from fastapi import FastAPI
from app.src.api import users, budgets, accounts, categories, steps

app = FastAPI()

app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(budgets.router, prefix="/budgets", tags=["budgets"])
app.include_router(accounts.router,   prefix="/accounts",   tags=["accounts"])
app.include_router(categories.router, prefix="/categories", tags=["categories"])
app.include_router(steps.router,    prefix="/steps",    tags=["steps"])

@app.get("/health")
def health():
    return {"status": "ok"}
