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