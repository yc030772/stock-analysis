from __future__ import annotations

import hashlib
import secrets
from pathlib import Path

import psycopg2
import streamlit as st


def _conn():
    return psycopg2.connect(st.secrets["DATABASE_URL"])


def _hash(password: str, salt: str) -> str:
    return hashlib.sha256((salt + password).encode()).hexdigest()


def register(username: str, password: str) -> tuple[bool, str]:
    username = username.strip().lower()
    if not username or not password:
        return False, "帳號與密碼不可為空。"
    if len(username) < 3:
        return False, "帳號至少需要 3 個字元。"
    if len(password) < 6:
        return False, "密碼至少需要 6 個字元。"
    salt = secrets.token_hex(16)
    hashed = _hash(password, salt)
    try:
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO users (username, salt, hash) VALUES (%s, %s, %s)",
                    (username, salt, hashed),
                )
    except psycopg2.errors.UniqueViolation:
        return False, "此帳號已存在。"
    portfolio_dir(username).mkdir(parents=True, exist_ok=True)
    return True, "註冊成功！"


def verify(username: str, password: str) -> bool:
    username = username.strip().lower()
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT salt, hash FROM users WHERE username = %s", (username,))
            row = cur.fetchone()
    if not row:
        return False
    salt, stored_hash = row
    return stored_hash == _hash(password, salt)


def portfolio_dir(username: str) -> Path:
    d = Path(__file__).parent / "data" / "portfolios" / username.strip().lower()
    d.mkdir(parents=True, exist_ok=True)
    return d
