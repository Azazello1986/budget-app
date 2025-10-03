from __future__ import annotations
from datetime import date
from typing import List, Optional

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import models
from app.db.deps import get_db
from app.src import schemas

router = APIRouter()


# ---------- Существующие эндпоинты (создание/список шагов) ----------
class _StepCreatePayload(schemas.StepCreate):
    pass


@router.post("", response_model=schemas.StepRead)
def create_step(payload: _StepCreatePayload, db: Session = Depends(get_db)):
    budget = db.get(models.Budget, payload.budget_id)
    if not budget:
        raise HTTPException(status_code=404, detail="budget not found")

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


@router.get("", response_model=List[schemas.StepRead])
def list_steps(budget_id: int = Query(...), db: Session = Depends(get_db)):
    steps = (
        db.query(models.BudgetStep)
        .filter(models.BudgetStep.budget_id == budget_id)
        .order_by(models.BudgetStep.date_start.desc(), models.BudgetStep.id.desc())
        .all()
    )
    return steps


# ---------- НОВОЕ: Лента операций шага ----------
@router.get("/{step_id}/feed", response_model=list[schemas.OperationRead])
def get_step_feed(step_id: int, db: Session = Depends(get_db)):
    """
    Возвращает операции шага, отсортированные по времени создания (как лента).
    Включает planned и actual.
    """
    ops = (
        db.query(models.Operation)
        .filter(models.Operation.step_id == step_id)
        .order_by(models.Operation.created_at.desc())
        .all()
    )
    return ops


# ---------- НОВОЕ: Сводка по шагу (только actual) ----------
@router.get("/{step_id}/summary", response_model=schemas.StepSummary)
def get_step_summary(step_id: int, db: Session = Depends(get_db)):
    """
    Возвращает суммы доходов/расходов за шаг по фактическим операциям.
    Переводы в сводку не включаем.
    """
    row = (
        db.query(
            sa.func.coalesce(
                sa.func.sum(
                    sa.case((models.Operation.sign == "income", models.Operation.amount), else_=0)
                ),
                0,
            ).label("inc"),
            sa.func.coalesce(
                sa.func.sum(
                    sa.case((models.Operation.sign == "expense", models.Operation.amount), else_=0)
                ),
                0,
            ).label("exp"),
        )
        .filter(models.Operation.step_id == step_id, models.Operation.kind == "actual")
        .one()
    )
    inc = row.inc or 0
    exp = row.exp or 0
    net = inc - exp
    return schemas.StepSummary(total_income=inc, total_expense=exp, net=net)


# ---------- НОВОЕ: Копирование плановых операций между шагами ----------
class _CopyPlannedPayload(BaseModel):
    to_step_id: int


@router.post("/{from_step_id}/copy_planned")
def copy_planned_operations(from_step_id: int, payload: _CopyPlannedPayload, db: Session = Depends(get_db)):
    src = db.get(models.BudgetStep, from_step_id)
    dst = db.get(models.BudgetStep, payload.to_step_id)
    if not src or not dst:
        raise HTTPException(status_code=404, detail="step not found")
    if src.budget_id != dst.budget_id:
        raise HTTPException(status_code=400, detail="steps belong to different budgets")

    planned_ops = (
        db.query(models.Operation)
        .filter(models.Operation.step_id == src.id, models.Operation.kind == "planned")
        .all()
    )

    copied = 0
    for op in planned_ops:
        db.add(
            models.Operation(
                budget_id=dst.budget_id,
                step_id=dst.id,
                kind="planned",
                sign=op.sign,
                amount=op.amount,
                currency=op.currency,
                date=op.date,
                account_id=op.account_id,
                account_id_to=op.account_id_to,
                category_id=op.category_id,
                comment=op.comment,
                planned_ref_id=None,
                created_by=None,
                created_at=sa.func.now(),
            )
        )
        copied += 1

    db.commit()
    return {"copied": copied}