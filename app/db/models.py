from __future__ import annotations
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import (
    String, DateTime, Date, Boolean, Text, Enum,
    ForeignKey, Numeric, CheckConstraint, Integer, BigInteger
)
from sqlalchemy.sql import func
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base

Role = Enum("viewer", "editor", name="role_enum", native_enum=False)
Granularity = Enum("day", "week", "month", "year", name="granularity_enum", native_enum=False)
Kind = Enum("planned", "actual", name="kind_enum", native_enum=False)
Sign = Enum("income", "expense", "transfer", name="sign_enum", native_enum=False)

class User(Base):
    __tablename__ = "user"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(200))
    hashed_password: Mapped[str | None] = mapped_column(String(255))  # bcrypt/argon2 hash
    ssh_public_key: Mapped[str | None] = mapped_column(Text)          # optional SSH public key
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class Budget(Base):
    __tablename__ = "budget"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="RESTRICT"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class BudgetShare(Base):
    __tablename__ = "budget_share"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    budget_id: Mapped[int] = mapped_column(ForeignKey("budget.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(Role, nullable=False)
    __table_args__ = (CheckConstraint("role in ('viewer','editor')"),)

class BudgetStep(Base):
    __tablename__ = "budget_step"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    budget_id: Mapped[int] = mapped_column(ForeignKey("budget.id", ondelete="CASCADE"), nullable=False)
    granularity: Mapped[str] = mapped_column(Granularity, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    date_start: Mapped[date] = mapped_column(Date, nullable=False)
    date_end: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class Account(Base):
    __tablename__ = "account"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    budget_id: Mapped[int] = mapped_column(ForeignKey("budget.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class Category(Base):
    __tablename__ = "category"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    budget_id: Mapped[int] = mapped_column(ForeignKey("budget.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class Operation(Base):
    __tablename__ = "operation"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    budget_id: Mapped[int] = mapped_column(ForeignKey("budget.id", ondelete="CASCADE"), nullable=False)
    step_id: Mapped[int] = mapped_column(ForeignKey("budget_step.id", ondelete="RESTRICT"), nullable=False)
    kind: Mapped[str] = mapped_column(Kind, nullable=False)      # planned | actual
    sign: Mapped[str] = mapped_column(Sign, nullable=False)      # income | expense | transfer
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    account_id: Mapped[int] = mapped_column(ForeignKey("account.id", ondelete="RESTRICT"), nullable=False)
    account_id_to: Mapped[int | None] = mapped_column(ForeignKey("account.id", ondelete="RESTRICT"))
    category_id: Mapped[int | None] = mapped_column(ForeignKey("category.id", ondelete="SET NULL"))
    comment: Mapped[str | None] = mapped_column(Text)
    planned_ref_id: Mapped[int | None] = mapped_column(ForeignKey("operation.id", ondelete="RESTRICT"))
    created_by: Mapped[int | None] = mapped_column(ForeignKey("user.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    __table_args__ = (CheckConstraint("amount > 0", name="ck_amount_positive"),)
