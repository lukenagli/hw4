"""Accounts: sign up, log in, log out and "who is logged in".

Passwords
    Stored as  pbkdf2_sha256$<salt>$<hex digest>, matching the rows already in
    the users table: PBKDF2-HMAC-SHA256, 120,000 iterations, the salt used as
    UTF-8 text, a 32-byte digest written as hex. New users get a fresh random
    16-hex-character salt.

Sessions
    After login the browser holds an HttpOnly cookie containing the user id,
    an expiry time and an HMAC signature. The server checks the signature on
    every request, so the cookie can't be edited to become another user.
    Routes that need the user (such as the chatbot) depend on
    `current_user_id` or `optional_user_id`.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import re
import secrets
import sqlite3
import time
from pathlib import Path

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from pydantic import BaseModel

from db import connect_readonly, connect_readwrite
from models import CustomerInfo

router = APIRouter(prefix="/api/auth", tags=["auth"])

# --- Password hashing ---------------------------------------------------------

HASH_ALGO = "pbkdf2_sha256"
HASH_ITERATIONS = 120_000
MIN_PASSWORD_LENGTH = 8


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(8)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), HASH_ITERATIONS)
    return f"{HASH_ALGO}${salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, salt, _ = stored.split("$")
    except ValueError:
        return False
    if algo != HASH_ALGO:
        return False
    return hmac.compare_digest(hash_password(password, salt), stored)


# Checked when the email doesn't exist, so a wrong email takes as long as a
# wrong password and response timing doesn't reveal which emails are registered.
_DUMMY_HASH = hash_password(secrets.token_hex(16))

# --- Session cookie -----------------------------------------------------------

SESSION_COOKIE = "cc_session"
SESSION_MAX_AGE = 7 * 24 * 60 * 60  # one week
_SECRET_FILE = Path(__file__).resolve().parent / ".session_secret"


def _load_secret() -> bytes:
    """SESSION_SECRET env var if set, else a random key kept in a git-ignored file."""
    if env := os.environ.get("SESSION_SECRET"):
        return env.encode()
    if not _SECRET_FILE.exists():
        _SECRET_FILE.write_text(secrets.token_hex(32))
    return _SECRET_FILE.read_text().strip().encode()


_SECRET = _load_secret()


def _sign(payload: str) -> str:
    sig = hmac.new(_SECRET, payload.encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(sig).decode().rstrip("=")


def make_session_token(user_id: int) -> str:
    payload = f"{user_id}.{int(time.time()) + SESSION_MAX_AGE}"
    return f"{payload}.{_sign(payload)}"


def read_session_token(token: str | None) -> int | None:
    if not token:
        return None
    try:
        user_id, expires, sig = token.split(".")
        payload = f"{user_id}.{expires}"
        if not hmac.compare_digest(sig, _sign(payload)) or int(expires) < time.time():
            return None
        return int(user_id)
    except ValueError:
        return None


def optional_user_id(cc_session: str | None = Cookie(default=None)) -> int | None:
    """The logged-in user's id, or None for guests."""
    return read_session_token(cc_session)


def current_user_id(user_id: int | None = Depends(optional_user_id)) -> int:
    """The logged-in user's id; responds 401 if nobody is logged in."""
    if user_id is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Please log in.")
    return user_id


def _set_session(response: Response, user_id: int) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        make_session_token(user_id),
        max_age=SESSION_MAX_AGE,
        httponly=True,  # page scripts can't read it
        samesite="lax",
        secure=False,  # set True when served over HTTPS
        path="/",
    )


# --- Models -------------------------------------------------------------------


class SignupRequest(BaseModel):
    first_name: str
    last_name: str
    email: str
    password: str
    confirm_password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class PublicUser(BaseModel):
    """What the front end sees. Never includes password_hash."""

    id: int
    first_name: str
    last_name: str
    name: str
    email: str


class MeResponse(BaseModel):
    user: PublicUser | None


def _public(row: sqlite3.Row) -> PublicUser:
    # first_name/last_name are nullable, so fall back to splitting name.
    first, _, last = row["name"].partition(" ")
    return PublicUser(
        id=row["id"],
        first_name=row["first_name"] or first,
        last_name=row["last_name"] or last,
        name=row["name"],
        email=row["email"],
    )


def _find_user(con: sqlite3.Connection, *, email: str | None = None, user_id: int | None = None):
    if email is not None:
        return con.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    return con.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def load_customer(user_id: int) -> CustomerInfo | None:
    """Name and email for the agent. Selects only those columns, so the
    password hash is never even read into memory for the chat."""
    with connect_readonly() as con:
        row = con.execute("SELECT name, first_name, last_name, email FROM users WHERE id = ?", (user_id,)).fetchone()
    if row is None:
        return None
    first, _, last = row["name"].partition(" ")
    return CustomerInfo(first_name=row["first_name"] or first, last_name=row["last_name"] or last, email=row["email"])


# --- Routes -------------------------------------------------------------------


@router.post("/signup", response_model=PublicUser, status_code=status.HTTP_201_CREATED)
def signup(body: SignupRequest, response: Response) -> PublicUser:
    first, last = body.first_name.strip(), body.last_name.strip()
    email = _normalize_email(body.email)

    if not first or not last:
        raise HTTPException(400, "Please enter your first and last name.")
    if not EMAIL_RE.match(email):
        raise HTTPException(400, "Please enter a valid email address.")
    if len(body.password) < MIN_PASSWORD_LENGTH:
        raise HTTPException(400, f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
    if body.password != body.confirm_password:
        raise HTTPException(400, "Passwords don't match.")

    with connect_readwrite() as con:
        if _find_user(con, email=email):
            raise HTTPException(409, "An account with that email already exists. Try logging in.")
        try:
            cur = con.execute(
                "INSERT INTO users (name, email, password_hash, first_name, last_name) VALUES (?, ?, ?, ?, ?)",
                (f"{first} {last}", email, hash_password(body.password), first, last),
            )
        except sqlite3.IntegrityError:  # lost a race with another signup
            raise HTTPException(409, "An account with that email already exists. Try logging in.")
        row = _find_user(con, user_id=cur.lastrowid)

    _set_session(response, row["id"])
    return _public(row)


@router.post("/login", response_model=PublicUser)
def login(body: LoginRequest, response: Response) -> PublicUser:
    with connect_readonly() as con:
        row = _find_user(con, email=_normalize_email(body.email))

    stored = row["password_hash"] if row else _DUMMY_HASH
    if not verify_password(body.password, stored) or row is None:
        # Same message for unknown email and wrong password.
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password.")

    _set_session(response, row["id"])
    return _public(row)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/")


@router.get("/me", response_model=MeResponse)
def me(user_id: int | None = Depends(optional_user_id)) -> MeResponse:
    if user_id is None:
        return MeResponse(user=None)
    with connect_readonly() as con:
        row = _find_user(con, user_id=user_id)
    return MeResponse(user=_public(row) if row else None)
