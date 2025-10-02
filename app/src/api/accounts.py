from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.src.deps import get_db
from app.db import models
from app.src.schemas import AccountCreate, AccountRead

router = APIRouter()

@router.post("", response_model=AccountRead, status_code=status.HTTP_201_CREATED)
def create_account(payload: AccountCreate, db: Session = Depends(get_db)):
    # проверим, что бюджет существует
    if not db.query(models.Budget).filter(models.Budget.id == payload.budget_id).first():
        raise HTTPException(400, "budget_id not found")
    acc = models.Account(
        budget_id=payload.budget_id,
        name=payload.name,
        currency=payload.currency,
    )
    db.add(acc)
    db.commit()
    db.refresh(acc)
    return acc

@router.get("", response_model=list[AccountRead])
def list_accounts(
    db: Session = Depends(get_db),
    budget_id: int | None = Query(default=None)
):
    q = db.query(models.Account).order_by(models.Account.id.desc())
    if budget_id is not None:
        q = q.filter(models.Account.budget_id == budget_id)
    return q.all()