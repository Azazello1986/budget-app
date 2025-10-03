from fastapi import APIRouter, Depends, HTTPException, Response, Cookie, Header, Request
import os
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.db.deps import get_db
from app.db import models
from app.src import schemas
from app.src.security import (
    hash_password, verify_password, create_jwt, decode_jwt,
    # ssh_fingerprint_sha256, parse_fp_header,  # ← временно не используем, чтобы не падать, пока нет колонки в БД
)

router = APIRouter(tags=["auth"])  # prefix задаётся при include_router в main.py

COOKIE_NAME = os.getenv("COOKIE_NAME", "session")


def _env_bool(name: str, default: bool) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "y", "on"}


def set_session_cookie(resp: Response, token: str):
    cookie_secure = _env_bool("COOKIE_SECURE", True)
    cookie_samesite = os.getenv("COOKIE_SAMESITE", "lax").lower()
    if cookie_samesite not in {"lax", "strict", "none"}:
        cookie_samesite = "lax"
    cookie_domain = os.getenv("COOKIE_DOMAIN") or None
    # Max-Age в секундах: по умолчанию равен JWT_TTL_MIN из security.py
    from app.src.security import JWT_TTL_MIN
    max_age = int(os.getenv("COOKIE_MAX_AGE", str(JWT_TTL_MIN * 60)))

    resp.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=cookie_secure,
        samesite=cookie_samesite,  # "none" требует secure=true в проде
        max_age=max_age,
        domain=cookie_domain,
        path="/",
    )


def clear_session_cookie(resp: Response):
    resp.delete_cookie(COOKIE_NAME, path="/")


def current_user(
    db: Session = Depends(get_db),
    session: str | None = Cookie(default=None, alias=COOKIE_NAME),
    x_ssh_fp: str | None = Header(default=None, alias="X-SSH-Key-Fingerprint"),
    authorization: str | None = Header(default=None, alias="Authorization"),
):
    """
    Достаём пользователя из одного из источников (в порядке приоритета):
    1) Bearer JWT из Authorization
    2) JWT из cookie
    3) (временно отключено) Отпечаток SSH-ключа
    """
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

    # 2) SSH fingerprint header (ОТКЛЮЧЕНО до появления колонки ssh_fingerprint в БД)
    # if x_ssh_fp:
    #     fp = parse_fp_header(x_ssh_fp)
    #     if fp:
    #         user = db.query(models.User).filter(models.User.ssh_fingerprint == fp).first()
    #         if user:
    #             return user

    raise HTTPException(status_code=401, detail="auth required")


@router.post("/register", response_model=schemas.UserRead, status_code=201)
async def register(request: Request, db: Session = Depends(get_db)):
    """
    Принимает JSON (application/json) и формы (application/x-www-form-urlencoded или multipart/form-data).
    Ожидаемые поля: name, email, password, ssh_public_key (optional)
    """
    ctype = request.headers.get("content-type", "").lower()
    if ctype.startswith("application/json"):
        data = await request.json()
    else:
        form = await request.form()
        data = {k: (v if v != "" else None) for k, v in form.items()}

    # Валидируем схему
    try:
        payload = schemas.UserCreate(**data)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))

    email_norm = payload.email.strip().lower()

    # Уникальность email
    if db.query(models.User).filter(models.User.email == email_norm).first():
        raise HTTPException(409, "email already registered")

    # Опциональный SSH ключ — сохраняем как есть (без отпечатка пока)
    user = models.User(
        email=email_norm,
        name=payload.name,
        hashed_password=hash_password(payload.password),  # ← ВАЖНО: поле в БД называется hashed_password
        ssh_public_key=payload.ssh_public_key,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        # Разбираем тип ошибки: 23505 — unique_violation, 23502 — not_null_violation и т.п.
        pgcode = getattr(getattr(e, 'orig', None), 'pgcode', None)
        msg = str(getattr(e, 'orig', e))
        if pgcode == '23505' or 'unique' in msg.lower():
            raise HTTPException(409, 'email already registered')
        raise HTTPException(400, f'register failed: {msg}')
    db.refresh(user)
    return user


@router.post("/login", response_model=schemas.UserRead)
def login(payload: schemas.LoginPayload, response: Response, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user or not getattr(user, "hashed_password", None) or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(401, "invalid credentials")
    token = create_jwt(user.id)
    set_session_cookie(response, token)
    return user


@router.post("/refresh", response_model=schemas.UserRead)
def refresh(
    response: Response,
    db: Session = Depends(get_db),
    session: str | None = Cookie(default=None, alias=COOKIE_NAME),
    authorization: str | None = Header(default=None, alias="Authorization"),
):
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

    # Выдаём новый cookie
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


@router.get("/health")
def health():
    return {"status": "ok", "scope": "auth"}