import hashlib
import hmac
import os
import secrets
import time
from collections import defaultdict

from fastapi import HTTPException, Request, Response
from sqlalchemy import delete, insert, select

from . import storage as store

COOKIE = "saly_session"
ATTEMPTS = defaultdict(list)


def password_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    return (
        salt + ":" + hashlib.scrypt(password.encode(), salt=salt.encode(), n=16384, r=8, p=1).hex()
    )


def set_owner(password):
    if len(password) < 12:
        raise ValueError("Use pelo menos 12 caracteres")
    with store.db() as c:
        c.execute(delete(store.owner_access))
        c.execute(insert(store.owner_access).values(id=1, password_hash=password_hash(password)))
        c.execute(delete(store.sessions))


def throttle(key, limit=12, seconds=60):
    stamp = time.monotonic()
    # Bound attacker-controlled keys; use fixed keys for login/chat.
    ATTEMPTS[key] = [t for t in ATTEMPTS[key] if t > stamp - seconds]
    if len(ATTEMPTS[key]) >= limit:
        raise HTTPException(
            429, "Limite temporário atingido. Aguarde.", headers={"Retry-After": str(seconds)}
        )
    ATTEMPTS[key].append(stamp)


def owner(request: Request):
    token = hashlib.sha256(request.cookies.get(COOKIE, "").encode()).hexdigest()
    with store.db() as c:
        r = c.execute(
            select(store.sessions.c.token).where(
                store.sessions.c.token == token, store.sessions.c.expires > time.time()
            )
        ).first()
    if not r:
        raise HTTPException(401, "Desbloqueie o espaço da proprietária")
    return True


def unlock(password, response: Response):
    throttle("login")
    with store.db() as c:
        record = c.execute(
            select(store.owner_access.c.password_hash).where(store.owner_access.c.id == 1)
        ).first()
    if not record:
        raise HTTPException(503, "Acesso privado ainda não configurado pela proprietária")
    expected = record[0]
    if not hmac.compare_digest(password_hash(password, expected.split(":")[0]), expected):
        raise HTTPException(401, "Senha inválida")
    token = secrets.token_urlsafe(32)
    with store.db() as c:
        c.execute(delete(store.sessions).where(store.sessions.c.expires < time.time()))
        c.execute(
            insert(store.sessions).values(
                token=hashlib.sha256(token.encode()).hexdigest(), expires=time.time() + 86400
            )
        )
    response.set_cookie(
        COOKIE,
        token,
        httponly=True,
        samesite="strict",
        secure=os.environ.get("SALY_SECURE_COOKIE") == "1",
        max_age=86400,
    )
    store.audit("access", "Espaço da proprietária desbloqueado")
