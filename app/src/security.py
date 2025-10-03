import base64
import hashlib
import re
from datetime import datetime, timedelta
from typing import Optional

from jose import jwt
from passlib.hash import bcrypt

JWT_SECRET = "CHANGE_ME_SECRET"  # лучше брать из ENV
JWT_ALG = "HS256"
JWT_TTL_MIN = 60 * 24 * 14  # 14 дней

def hash_password(p: str) -> str:
    return bcrypt.hash(p)

def verify_password(p: str, ph: str) -> bool:
    return bcrypt.verify(p, ph)

def create_jwt(user_id: int) -> str:
    now = datetime.utcnow()
    payload = {"sub": str(user_id), "iat": now, "exp": now + timedelta(minutes=JWT_TTL_MIN)}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)

def decode_jwt(token: str) -> Optional[int]:
    try:
        data = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        return int(data["sub"])
    except Exception:
        return None

_SSH_HEADER_FP = re.compile(r"^SHA256:([A-Za-z0-9+/=]+)$")

def ssh_fingerprint_sha256(pubkey: str) -> str:
    # ожидаем ключ вида: "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIH... user@host"
    parts = pubkey.strip().split()
    if len(parts) < 2:
        raise ValueError("invalid ssh public key")
    raw = base64.b64decode(parts[1])
    fp = hashlib.sha256(raw).digest()
    return "SHA256:" + base64.b64encode(fp).decode("ascii").rstrip("=")

def parse_fp_header(val: str) -> Optional[str]:
    # принимаем в заголовке X-SSH-Key-Fingerprint именно "SHA256:base64"
    m = _SSH_HEADER_FP.match(val.strip())
    if not m:
        return None
    # нормализуем без '=' в конце (как в OpenSSH)
    return "SHA256:" + m.group(1).rstrip("=")