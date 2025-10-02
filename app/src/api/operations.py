# ---- OPERATIONS ----
from pydantic import BaseModel, Field, field_validator
from decimal import Decimal

class OperationCreate(BaseModel):
    step_id: int
    kind: str = Field(pattern="^(planned|actual)$")
    sign: str = Field(pattern="^(income|expense|transfer)$")
    amount: Decimal = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)
    # для income/expense и источник для transfer
    account_id: int | None = None
    # для transfer (получатель)
    account_id_to: int | None = None
    category_id: int | None = None
    comment: str | None = None
    # ссылка фактической на плановую
    planned_ref_id: int | None = None

    @field_validator("account_id")
    @classmethod
    def validate_account_non_transfer(cls, v, values):
        if values.get("sign") in {"income", "expense"} and not v:
            raise ValueError("account_id is required for income/expense")
        return v

    @field_validator("account_id_to")
    @classmethod
    def validate_accounts_transfer(cls, v, values):
        if values.get("sign") == "transfer":
            if not values.get("account_id") or not values.get("account_id_to"):
                raise ValueError("account_id and account_id_to are required for transfer")
            if values.get("account_id") == values.get("account_id_to"):
                raise ValueError("account_id and account_id_to must be different")
        return v


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