from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, Field, EmailStr, model_validator

# ------------------ USERS ------------------
class UserCreate(BaseModel):
    email: EmailStr
    name: str

class UserRead(BaseModel):
    id: int
    email: EmailStr
    name: str

    class Config:
        from_attributes = True

# ------------------ BUDGETS ------------------
class BudgetCreate(BaseModel):
    name: str
    currency: str = Field(min_length=3, max_length=3)
    owner_user_id: int

class BudgetRead(BaseModel):
    id: int
    name: str
    currency: str
    owner_user_id: int

    class Config:
        from_attributes = True

# ------------------ ACCOUNTS ------------------
class AccountCreate(BaseModel):
    budget_id: int
    name: str
    currency: str = Field(min_length=3, max_length=3)

class AccountRead(BaseModel):
    id: int
    budget_id: int
    name: str
    currency: str

    class Config:
        from_attributes = True

# ------------------ CATEGORIES ------------------
class CategoryCreate(BaseModel):
    budget_id: int
    name: str

class CategoryRead(BaseModel):
    id: int
    budget_id: int
    name: str

    class Config:
        from_attributes = True

# ------------------ STEPS ------------------
class StepCreate(BaseModel):
    budget_id: int
    granularity: str = Field(pattern=r"^(day|week|month|year)$")
    name: str
    date_start: date
    date_end: date

class StepRead(BaseModel):
    id: int
    budget_id: int
    granularity: str
    name: str
    date_start: date
    date_end: date

    class Config:
        from_attributes = True

# ------------------ OPERATIONS ------------------
class OperationCreate(BaseModel):
    step_id: int
    kind: str = Field(pattern=r"^(planned|actual)$")
    sign: str = Field(pattern=r"^(income|expense|transfer)$")
    amount: Decimal = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)

    # дата операции (если не передана — выставляется на сервере)
    date: datetime | None = None

    # для income/expense и источник для transfer
    account_id: int | None = None
    # для transfer (получатель)
    account_id_to: int | None = None

    category_id: int | None = None
    comment: str | None = None

    # ссылка фактической на плановую
    planned_ref_id: int | None = None

    @model_validator(mode="after")
    def _check_consistency(self):
        if self.sign in {"income", "expense"}:
            if not self.account_id:
                raise ValueError("account_id is required for income/expense")

        if self.sign == "transfer":
            if not self.account_id or not self.account_id_to:
                raise ValueError("account_id and account_id_to are required for transfer")
            if self.account_id == self.account_id_to:
                raise ValueError("account_id and account_id_to must be different")
        return self

class OperationRead(BaseModel):
    id: int
    step_id: int
    kind: str
    sign: str
    amount: Decimal
    currency: str
    account_id: int | None = None
    account_id_to: int | None = None
    category_id: int | None = None
    comment: str | None = None
    planned_ref_id: int | None = None

    class Config:
        from_attributes = True