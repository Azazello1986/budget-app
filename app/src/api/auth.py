from fastapi import APIRouter, Depends, HTTPException, Response, Cookie, Header
from sqlalchemy.orm import Session

from app.db.deps import get_db
from app.db import models
from app.src import schemas
from app.src.security import (
    hash_password, verify_password, create_jwt, decode_jwt,
    ssh_fingerprint_sha256, parse_fp_header
)

router = APIRouter(prefix="/auth", tags=["auth"])

COOKIE_NAME = "session"

def set_session_cookie(resp: Response, token: str):
    resp.set_cookie(
        key=COOKIE_NAME, value=token, httponly=True, secure=True,
        samesite="lax", max_age=60*60*24*14, path="/"
    )

def clear_session_cookie(resp: Response):
    resp.delete_cookie(COOKIE_NAME, path="/")

def current_user(
    db: Session = Depends(get_db),
    session: str | None = Cookie(default=None, alias=COOKIE_NAME),
    x_ssh_fp: str | None = Header(default=None, alias="X-SSH-Key-Fingerprint"),
    authorization: str | None = Header(default=None, alias="Authorization"),
):
    # 0) Bearer token in Authorization header
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        uid = decode_jwt(token)
        if uid:
            user = db.get(models.User, uid)
            if user:
                return user

    # 1) JWT from cookie
    if session:
        uid = decode_jwt(session)
        if uid:
            user = db.get(models.User, uid)
            if user:
                return user

    # 2) SSH fingerprint header
    if x_ssh_fp:
        fp = parse_fp_header(x_ssh_fp)
        if fp:
            user = db.query(models.User).filter(models.User.ssh_fingerprint == fp).first()
            if user:
                return user

    raise HTTPException(status_code=401, detail="auth required")

@router.post("/register", response_model=schemas.UserRead, status_code=201)
def register(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    if db.query(models.User).filter(models.User.email == payload.email).first():
        raise HTTPException(409, "email already registered")

    ssh_fp = None
    if payload.ssh_public_key:
        try:
            ssh_fp = ssh_fingerprint_sha256(payload.ssh_public_key)
        except Exception:
            raise HTTPException(400, "invalid ssh public key")

    user = models.User(
        email=payload.email, name=payload.name,
        password_hash=hash_password(payload.password),
        ssh_public_key=payload.ssh_public_key, ssh_fingerprint=ssh_fp
    )
    db.add(user); db.commit(); db.refresh(user)
    return user

@router.post("/login", response_model=schemas.UserRead)
def login(payload: schemas.LoginPayload, response: Response, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user or not user.password_hash or not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, "invalid credentials")
    token = create_jwt(user.id)
    set_session_cookie(response, token)
    return user

@router.post("/refresh", response_model=schemas.UserRead)
def refresh(response: Response, db: Session = Depends(get_db), session: str | None = Cookie(default=None, alias=COOKIE_NAME), authorization: str | None = Header(default=None, alias="Authorization")):
    uid = None
    if authorization and authorization.lower().startswith("bearer "):
        uid = decode_jwt(authorization.split(" ", 1)[1].strip())
    if not uid and session:
        uid = decode_jwt(session)
    if not uid:
        raise HTTPException(401, "auth required")

    user = db.get(models.User, uid)
    if not user:
        raise HTTPException(401, "auth required")

    # Issue a fresh cookie
    token = create_jwt(user.id)
    set_session_cookie(response, token)
    return user

@router.post("/logout")
def logout(response: Response):
    clear_session_cookie(response)
    return {"ok": True}

@router.get("/me", response_model=schemas.MeRead)
def me(user: models.User = Depends(current_user)):
    return user