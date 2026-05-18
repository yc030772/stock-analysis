"""Signed-token helpers for persistent login via browser cookie."""
from __future__ import annotations

import base64
import hashlib
import hmac
import time

import streamlit as st

COOKIE_NAME = "sa_session"
COOKIE_DAYS = 30


def _secret() -> bytes:
    return st.secrets.get("COOKIE_SECRET", "dev-only-insecure-fallback").encode()


def _sign(payload: str) -> str:
    return hmac.new(_secret(), payload.encode(), hashlib.sha256).hexdigest()


def make_token(username: str) -> str:
    expiry = int(time.time()) + COOKIE_DAYS * 86400
    payload = f"{username}|{expiry}"
    return base64.urlsafe_b64encode(f"{payload}|{_sign(payload)}".encode()).decode()


def verify_token(token: str) -> str | None:
    """Return username if signature is valid and token is not expired."""
    try:
        raw = base64.urlsafe_b64decode(token.encode()).decode()
        username, expiry_str, sig = raw.split("|", 2)
        payload = f"{username}|{expiry_str}"
        if not hmac.compare_digest(sig, _sign(payload)):
            return None
        if time.time() > int(expiry_str):
            return None
        return username
    except Exception:
        return None
