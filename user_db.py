from __future__ import annotations

import hashlib
import secrets
from pathlib import Path

import streamlit as st
from supabase import create_client


def _client():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])


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
        _client().table("users").insert({
            "username": username,
            "salt": salt,
            "hash": hashed,
        }).execute()
    except Exception as e:
        msg = str(e).lower()
        if "duplicate" in msg or "unique" in msg or "23505" in msg:
            return False, "此帳號已存在。"
        return False, f"註冊失敗：{e}"
    portfolio_dir(username).mkdir(parents=True, exist_ok=True)
    return True, "註冊成功！"


def verify(username: str, password: str) -> bool:
    username = username.strip().lower()
    result = _client().table("users").select("salt, hash").eq("username", username).execute()
    if not result.data:
        return False
    row = result.data[0]
    return row["hash"] == _hash(password, row["salt"])


def portfolio_dir(username: str) -> Path:
    d = Path(__file__).parent / "data" / "portfolios" / username.strip().lower()
    d.mkdir(parents=True, exist_ok=True)
    return d
