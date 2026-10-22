"""Authentication: user accounts, password hashing, and JWT tokens.

This is real auth, not a cosmetic gate:
  * Passwords are hashed with bcrypt (never stored in plain text).
  * On login we issue a signed JWT; the client sends it as a Bearer token.
  * Protected endpoints verify the token before running.

Users are stored in the same PostgreSQL database used for the vector store, in a `users`
table managed with SQLAlchemy. This mirrors the JWT auth pattern from the ResuMate project.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from sqlalchemy import Column, Integer, String, create_engine, select
from sqlalchemy.orm import Session, declarative_base

log = logging.getLogger("graminsahay.auth")

Base = declarative_base()


class User(Base):
    """A registered citizen/user. We store only a username and the bcrypt password hash."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)


class AuthError(Exception):
    """Raised for any authentication failure (bad credentials, duplicate user, bad token)."""


class AuthService:
    """Handles registration, login, and token verification against the users table."""

    def __init__(self, db_url: str, jwt_secret: str, jwt_algorithm: str, expire_minutes: int) -> None:
        self._engine = create_engine(db_url, pool_pre_ping=True)
        self._secret = jwt_secret
        self._algorithm = jwt_algorithm
        self._expire_minutes = expire_minutes

    def ensure_schema(self) -> None:
        Base.metadata.create_all(self._engine)

    # ---- password helpers ----
    # We use the `bcrypt` library directly (rather than via passlib) to avoid a known
    # passlib/bcrypt version incompatibility that crashes on some setups. bcrypt also has a
    # 72-byte input limit, so we truncate the encoded password to stay within it.
    @staticmethod
    def _hash_password(password: str) -> str:
        pw_bytes = password.encode("utf-8")[:72]
        return bcrypt.hashpw(pw_bytes, bcrypt.gensalt()).decode("utf-8")

    @staticmethod
    def _verify_password(password: str, password_hash: str) -> bool:
        try:
            pw_bytes = password.encode("utf-8")[:72]
            return bcrypt.checkpw(pw_bytes, password_hash.encode("utf-8"))
        except (ValueError, TypeError):
            return False

    # ---- registration / login ----
    def register(self, username: str, password: str) -> str:
        """Create a new user and return a JWT. Raises AuthError if the username is taken."""
        username = username.strip().lower()
        if len(username) < 3:
            raise AuthError("Username must be at least 3 characters.")
        if len(password) < 6:
            raise AuthError("Password must be at least 6 characters.")

        with Session(self._engine) as session:
            existing = session.scalar(select(User).where(User.username == username))
            if existing is not None:
                raise AuthError("That username is already taken.")
            user = User(username=username, password_hash=self._hash_password(password))
            session.add(user)
            session.commit()
            session.refresh(user)
            return self._issue_token(user.username)

    def login(self, username: str, password: str) -> str:
        """Verify credentials and return a JWT. Raises AuthError on bad credentials."""
        username = username.strip().lower()
        with Session(self._engine) as session:
            user = session.scalar(select(User).where(User.username == username))
            if user is None or not self._verify_password(password, user.password_hash):
                raise AuthError("Invalid username or password.")
            return self._issue_token(user.username)

    # ---- token helpers ----
    def _issue_token(self, username: str) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": username,
            "iat": now,
            "exp": now + timedelta(minutes=self._expire_minutes),
        }
        return jwt.encode(payload, self._secret, algorithm=self._algorithm)

    def verify_token(self, token: str) -> str:
        """Return the username encoded in a valid token, or raise AuthError."""
        try:
            payload = jwt.decode(token, self._secret, algorithms=[self._algorithm])
            username = payload.get("sub")
            if not username:
                raise AuthError("Invalid token.")
            return username
        except jwt.ExpiredSignatureError as exc:
            raise AuthError("Session expired. Please log in again.") from exc
        except jwt.PyJWTError as exc:
            raise AuthError("Invalid token.") from exc
