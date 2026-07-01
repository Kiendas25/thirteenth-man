"""Authentication: JWT-based login/register with SQLite user storage."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import aiosqlite
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from app.config import settings

log = logging.getLogger(__name__)

SECRET_KEY = "thirteenth-man-secret-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


class UserCreate(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    created_at: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str


async def init_auth_db() -> None:
    """Create users table if needed."""
    async with aiosqlite.connect(settings.db_path) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()
    log.info("Auth database initialised")


def _hash_password(password: str) -> str:
    return pwd_context.hash(password)


def _verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def _create_token(username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    return jwt.encode(
        {"sub": username, "exp": expire},
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


async def register_user(data: UserCreate) -> UserResponse:
    """Register a new user."""
    async with aiosqlite.connect(settings.db_path) as db:
        try:
            cursor = await db.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (data.username, _hash_password(data.password)),
            )
            await db.commit()
            user_id = cursor.lastrowid
        except Exception:
            raise HTTPException(
                status_code=400,
                detail="Username already exists",
            )

        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT id, username, created_at FROM users WHERE id = ?",
            (user_id,),
        )
        row = await cursor.fetchone()
        return UserResponse(
            id=row["id"],
            username=row["username"],
            created_at=row["created_at"],
        )


async def authenticate_user(username: str, password: str) -> Token:
    """Authenticate and return a JWT token."""
    async with aiosqlite.connect(settings.db_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT id, username, password_hash FROM users WHERE username = ?",
            (username,),
        )
        row = await cursor.fetchone()

    if not row or not _verify_password(password, row["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    token = _create_token(username)
    return Token(access_token=token, username=username)


async def get_current_user(token: str | None = Depends(oauth2_scheme)) -> str | None:
    """Extract current user from JWT. Returns None if not authenticated."""
    if token is None:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str | None = payload.get("sub")
        return username
    except JWTError:
        return None
