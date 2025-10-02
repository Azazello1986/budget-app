from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from decimal import Decimal

from app.src.deps import get_db
from app.db import models
from app.src.schemas import OperationCreate, OperationRead

router = APIRouter()

def _ensure_step_budget_exists(db: Session, budget_step_id: int) -> models.BudgetStep | None:
    return db.query(models.BudgetStep).filter(models.BudgetStep.id == budget_step_id).first()

def _ensure_account(db: Session, account_id: int | None) -> models.Account | None:
    if not account_id:
        return None
    return db.query(models.Account).filter(models.Account.id == account_id).first()

def _ensure_category(db: Session, category_id: int | None) -> models.Category | None:
    if not category_id:
        return None
    return db.query(models.Category).filter(models.Category.id == category_id).first()

@router.post("", response_model=OperationRead, status_code=status.HTTP_201_CREATED)
def create_operation(payload: OperationCreate, db: Session = Depends(get_db)):
    # шаг должен существовать
    step = _ensure_step_budget_exists(db, payload.budget_step_id)
    if not step:
        raise HTTPException(400, "budget_step_id not found")

    # базовые проверки счетов и категорий
    if payload.sign in {"income", "expense"}:
        acc = _ensure_account(db, payload.account_id)
        if not acc:
            raise HTTPException(400, "account_id not found")
        # счёт должен принадлежать бюджету шага
        if acc.budget_id != step.budget_id:
            raise HTTPException(400, "account belongs to another budget")

    if payload.sign == "transfer":
        src = _ensure_account(db, payload.from_account_id)
        dst = _ensure_account(db, payload.to_account_id)
        if not src or not dst:
            raise HTTPException(400, "from_account_id or to_account_id not found")
        if src.budget_id != step.budget_id or dst.budget_id != step.budget_id:
            raise HTTPException(400, "transfer accounts must belong to the same budget as step")

    if payload.category_id:
        cat = _ensure_category(db, payload.category_id)
        if not cat:
            raise HTTPException(400, "category_id not found")
        if cat.budget_id != step.budget_id:
            raise HTTPException(400, "category belongs to another budget")

    # если фактическая ссылается на плановую — проверим
    if payload.kind == "actual" and payload.planned_id:
        planned = db.query(models.Operation).filter(models.Operation.id == payload.planned_id).first()
        if not planned:
            raise HTTPException(400, "planned_id not found")
        if planned.kind != "planned":
            raise HTTPException(400, "planned_id must refer to a planned operation")
        if planned.budget_step_id != payload.budget_step_id:
            raise HTTPException(400, "planned and actual must belong to the same step")

    # создаём операцию
    op = models.Operation(
        budget_step_id=payload.budget_step_id,
        kind=payload.kind,
        sign=payload.sign,
        amount=Decimal(payload.amount),
        currency=payload.currency,
        account_id=payload.account_id,
        from_account_id=payload.from_account_id,
        to_account_id=payload.to_account_id,
        category_id=payload.category_id,
        comment=payload.comment,
        planned_id=payload.planned_id,
        created_at=datetime.now(timezone.utc),  # пока ставим явно; позже переведём на server_default
    )
    db.add(op)
    db.commit()
    db.refresh(op)
    return op


@router.get("", response_model=list[OperationRead])
def list_operations(
    db: Session = Depends(get_db),
    budget_step_id: int = Query(...),
    kind: str | None = Query(default=None, pattern="^(planned|actual)$"),
):
    q = db.query(models.Operation).filter(models.Operation.budget_step_id == budget_step_id)
    if kind:
        q = q.filter(models.Operation.kind == kind)
    return q.order_by(models.Operation.id.asc()).all()


@router.post("/copy_planned", response_model=dict, status_code=status.HTTP_201_CREATED)
def copy_planned_operations(
    source_step_id: int = Query(..., description="Откуда копируем плановые"),
    target_step_id: int = Query(..., description="Куда копируем плановые"),
    db: Session = Depends(get_db),
):
    if source_step_id == target_step_id:
        raise HTTPException(400, "source_step_id and target_step_id must differ")

    src = _ensure_step_budget_exists(db, source_step_id)
    dst = _ensure_step_budget_exists(db, target_step_id)
    if not src or not dst:
        raise HTTPException(400, "source or target step not found")

    if src.budget_id != dst.budget_id:
        raise HTTPException(400, "steps must belong to the same budget")

    planned_ops = db.query(models.Operation).filter(
        models.Operation.budget_step_id == source_step_id,
        models.Operation.kind == "planned"
    ).all()

    created = 0
    for p in planned_ops:
        clone = models.Operation(
            budget_step_id=target_step_id,
            kind="planned",
            sign=p.sign,
            amount=p.amount,
            currency=p.currency,
            account_id=p.account_id,
            from_account_id=p.from_account_id,
            to_account_id=p.to_account_id,
            category_id=p.category_id,
            comment=p.comment,
            planned_id=None,
            created_at=datetime.now(timezone.utc),
        )
        db.add(clone)
        created += 1

    db.commit()
    return {"copied": created}