from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.src.deps import get_db
from app.db import models
from app.src.schemas import StepCreate, StepRead

router = APIRouter()

@router.post("", response_model=StepRead, status_code=status.HTTP_201_CREATED)
def create_step(payload: StepCreate, db: Session = Depends(get_db)):
    # бюджет должен существовать
    if not db.query(models.Budget).filter(models.Budget.id == payload.budget_id).first():
        raise HTTPException(400, "budget_id not found")

    # простая валидация дат
    if payload.date_start > payload.date_end:
        raise HTTPException(400, "date_start must be <= date_end")

    step = models.BudgetStep(
        budget_id=payload.budget_id,
        granularity=payload.granularity,
        name=payload.name,
        date_start=payload.date_start,
        date_end=payload.date_end,
    )
    db.add(step)
    db.commit()
    db.refresh(step)
    return step

@router.get("", response_model=list[StepRead])
def list_steps(db: Session = Depends(get_db), budget_id: int = Query(...)):
    return (
        db.query(models.BudgetStep)
        .filter(models.BudgetStep.budget_id == budget_id)
        .order_by(models.BudgetStep.date_start.desc())
        .all()
    )