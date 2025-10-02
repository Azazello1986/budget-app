# app/src/schemas.py
from datetime import date
from pydantic import BaseModel, EmailStr, Field

# USERS
class UserCreate(BaseModel):
    email: EmailStr
    name: str | None = None

class UserRead(BaseModel):
    id: int
    email: EmailStr
    name: str | None = None
    class Config:
        from_attributes = True  # Pydantic v2 для работы с ORM

# BUDGETS
class BudgetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    currency: str = Field(min_length=3, max_length=3)  # ISO-4217 типа "EUR"
    owner_user_id: int

class BudgetRead(BaseModel):
    id: int
    name: str
    currency: str
    owner_user_id: int
    class Config:
        from_attributes = True

# ACCOUNTS
class AccountCreate(BaseModel):
    budget_id: int
    name: str
    currency: str

class AccountRead(BaseModel):
    id: int
    budget_id: int
    name: str
    currency: str
    class Config: from_attributes = True

# CATEGORIES
class CategoryCreate(BaseModel):
    budget_id: int
    name: str

class CategoryRead(BaseModel):
    id: int
    budget_id: int
    name: str
    class Config: from_attributes = True

class StepCreate(BaseModel):
    budget_id: int
    granularity: str = Field(pattern="^(day|week|month|year)$")
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

# ---- OPERATIONS ----
from pydantic import BaseModel, Field, field_validator
from decimal import Decimal

class OperationCreate(BaseModel):
    budget_step_id: int
    kind: str = Field(pattern="^(planned|actual)$")
    sign: str = Field(pattern="^(income|expense|transfer)$")
    amount: Decimal = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)
    account_id: int | None = None              # для income/expense
    from_account_id: int | None = None         # для transfer
    to_account_id: int | None = None           # для transfer
    category_id: int | None = None
    comment: str | None = None
    planned_id: int | None = None              # фактическая может ссылаться на плановую

    @field_validator("account_id")
    @classmethod
    def validate_account_for_non_transfer(cls, v, values):
        # если не transfer, нужен account_id
        if values.get("sign") in {"income", "expense"} and not v:
            raise ValueError("account_id is required for income/expense")
        return v

    @field_validator("from_account_id", "to_account_id")
    @classmethod
    def validate_accounts_for_transfer(cls, v, values, field):
        # для transfer нужны оба счета
        if values.get("sign") == "transfer":
            if not values.get("from_account_id") or not values.get("to_account_id"):
                raise ValueError("from_account_id and to_account_id are required for transfer")
            if values.get("from_account_id") == values.get("to_account_id"):
                raise ValueError("from_account_id and to_account_id must be different")
        return v


class OperationRead(BaseModel):
    id: int
    budget_step_id: int
    kind: str
    sign: str
    amount: Decimal
    currency: str
    account_id: int | None = None
    from_account_id: int | None = None
    to_account_id: int | None = None
    category_id: int | None = None
    comment: str | None = None
    planned_id: int | None = None

    class Config:
        from_attributes = True