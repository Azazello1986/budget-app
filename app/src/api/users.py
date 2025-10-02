# app/src/api/users.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.src.deps import get_db
from app.db import models
from app.src.schemas import UserCreate, UserRead

router = APIRouter()

@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    exists = db.query(models.User).filter(models.User.email == payload.email).first()
    if exists:
        raise HTTPException(status_code=400, detail="User with this email already exists")
    user = models.User(email=payload.email, name=payload.name)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.get("", response_model=list[UserRead])
def list_users(db: Session = Depends(get_db)):
    users = db.query(models.User).order_by(models.User.id.desc()).all()
    return users