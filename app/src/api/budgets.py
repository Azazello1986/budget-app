# app/src/api/budgets.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.src.deps import get_db
from app.db import models
from app.src.schemas import BudgetCreate, BudgetRead

router = APIRouter()

@router.post("", response_model=BudgetRead, status_code=status.HTTP_201_CREATED)
def create_budget(payload: BudgetCreate, db: Session = Depends(get_db)):
    owner = db.query(models.User).filter(models.User.id == payload.owner_user_id).first()
    if not owner:
        raise HTTPException(status_code=400, detail="owner_user_id not found")
    b = models.Budget(
        name=payload.name,
        currency=payload.currency,
        owner_user_id=payload.owner_user_id,
    )
    db.add(b)
    db.commit()
    db.refresh(b)
    return b

@router.get("", response_model=list[BudgetRead])
def list_budgets(
    db: Session = Depends(get_db),
    owner_user_id: int | None = Query(default=None, description="optional filter by owner"),
):
    q = db.query(models.Budget).order_by(models.Budget.id.desc())
    if owner_user_id is not None:
        q = q.filter(models.Budget.owner_user_id == owner_user_id)
    return q.all()