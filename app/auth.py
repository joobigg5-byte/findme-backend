"""
Real authentication: bcrypt password hashing + JWT bearer tokens.

SECRET_KEY MUST be overridden via environment variable in any real
deployment — the default here is only for local development and is
intentionally obvious so nobody mistakes it for something safe to ship.
"""
import os
import secrets
import datetime
from typing import Optional

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from . import models
from .database import get_db

SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-only-secret-change-me-before-deploying")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days
RESET_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# Shared rate limiter — keyed by client IP. In-memory by default, which is
# correct for a single instance; if you ever run multiple backend
# instances behind a load balancer, point this at Redis instead
# (Limiter(key_func=..., storage_uri="redis://...")) so limits are shared
# across instances rather than reset per-instance.
limiter = Limiter(key_func=get_remote_address)


def hash_password(password: str) -> str:
    # bcrypt has a hard 72-byte input limit — truncate defensively rather
    # than letting a long password 500-error the signup endpoint.
    pw_bytes = password.encode("utf-8")[:72]
    return bcrypt.hashpw(pw_bytes, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    pw_bytes = plain_password.encode("utf-8")[:72]
    return bcrypt.checkpw(pw_bytes, hashed_password.encode("utf-8"))


def generate_reset_token() -> str:
    """Cryptographically random, URL-safe — safe to put in an email link."""
    return secrets.token_urlsafe(32)


def create_access_token(user_id: int, organization_id: int) -> str:
    expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "org": organization_id, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    """
    FastAPI dependency: verifies the bearer token and returns the real User
    row from the database (not just trusting whatever the token claims) —
    this is what every protected route depends on.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception
    user = db.query(models.User).filter(models.User.id == int(user_id)).first()
    if user is None:
        raise credentials_exception
    return user
