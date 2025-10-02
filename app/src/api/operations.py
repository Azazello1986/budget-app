from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from decimal import Decimal

from app.src.deps import get_db
from app.db import models
from app.src.schemas import OperationCreate, OperationRead

router = APIRouter()

def _get_step(db: Session, step_id: int):
    return db.query(models.BudgetStep).filter(models.BudgetStep.id == step_id).first()

def _get_account(db: Session, acc_id: int | None):
    if not acc_id:
        return None
    return db.query(models.Account).filter(models.Account.id == acc_id).first()

def _get_category(db: Session, cat_id: int | None):
    if not cat_id:
        return None
    return db.query(models.Category).filter(models.Category.id == cat_id).first()

@router.post("", response_model=OperationRead, status_code=status.HTTP_201_CREATED)
def create_operation(payload: OperationCreate, db: Session = Depends(get_db)):
    step = _get_step(db, payload.step_id)
    if not step:
        raise HTTPException(400, "step_id not found")

    if payload.sign in {"income", "expense"}:
        acc = _get_account(db, payload.account_id)
        if not acc:
            raise HTTPException(400, "account_id not found")
        if acc.budget_id != step.budget_id:
            raise HTTPException(400, "account belongs to another budget")

    if payload.sign == "transfer":
        src = _get_account(db, payload.account_id)
        dst = _get_account(db, payload.account_id_to)
        if not src or not dst:
            raise HTTPException(400, "account_id or account_id_to not found")
        if src.budget_id != step.budget_id or dst.budget_id != step.budget_id:
            raise HTTPException(400, "transfer accounts must belong to step's budget")

    if payload.category_id:
        cat = _get_category(db, payload.category_id)
        if not cat:
            raise HTTPException(400, "category_id not found")
        if cat.budget_id != step.budget_id:
            raise HTTPException(400, "category belongs to another budget")

    if payload.kind == "actual" and payload.planned_ref_id:
        planned = db.query(models.Operation).filter(models.Operation.id == payload.planned_ref_id).first()
        if not planned:
            raise HTTPException(400, "planned_ref_id not found")
        if planned.kind != "planned":
            raise HTTPException(400, "planned_ref_id must refer to a planned operation")
        if planned.step_id != payload.step_id:
            raise HTTPException(400, "planned and actual must belong to the same step")

    op = models.Operation(
        budget_id=step.budget_id,
        step_id=payload.step_id,
        kind=payload.kind,
        sign=payload.sign,
        amount=Decimal(payload.amount),
        currency=payload.currency,
        date=payload.date or datetime.now(timezone.utc),
        account_id=payload.account_id,
        account_id_to=payload.account_id_to,
        category_id=payload.category_id,
        comment=payload.comment,
        planned_ref_id=payload.planned_ref_id,
        created_at=datetime.now(timezone.utc),
    )
    db.add(op)
    db.commit()
    db.refresh(op)
    return op

@router.get("", response_model=list[OperationRead])
def list_operations(
    db: Session = Depends(get_db),
    step_id: int = Query(...),
    kind: str | None = Query(default=None, pattern="^(planned|actual)$"),
):
    q = db.query(models.Operation).filter(models.Operation.step_id == step_id)
    if kind:
        q = q.filter(models.Operation.kind == kind)
    return q.order_by(models.Operation.id.asc()).all()

@router.post("/copy_planned", response_model=dict, status_code=status.HTTP_201_CREATED)
def copy_planned_operations(
    source_step_id: int = Query(...),
    target_step_id: int = Query(...),
    db: Session = Depends(get_db),
):
    if source_step_id == target_step_id:
        raise HTTPException(400, "source_step_id and target_step_id must differ")

    src = _get_step(db, source_step_id)
    dst = _get_step(db, target_step_id)
    if not src or not dst:
        raise HTTPException(400, "source or target step not found")
    if src.budget_id != dst.budget_id:
        raise HTTPException(400, "steps must belong to the same budget")

    planned_ops = db.query(models.Operation).filter(
        models.Operation.step_id == source_step_id,
        models.Operation.kind == "planned"
    ).all()

    created = 0
    for p in planned_ops:
        clone = models.Operation(
            budget_id=dst.budget_id,
            step_id=target_step_id,
            kind="planned",
            sign=p.sign,
            amount=p.amount,
            currency=p.currency,
            date=dst.date_start or datetime.now(timezone.utc),
            account_id=p.account_id,
            account_id_to=p.account_id_to,
            category_id=p.category_id,
            comment=p.comment,
            planned_ref_id=None,
            created_at=datetime.now(timezone.utc),
        )
        db.add(clone)
        created += 1

    db.commit()
    return {"copied": created}