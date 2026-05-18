from __future__ import annotations

import hashlib
import json
import secrets
from pathlib import Path

_DATA_DIR  = Path(__file__).parent / "data"
_USERS_FILE = _DATA_DIR / "users.json"


def _load() -> dict:
    try:
        with open(_USERS_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save(users: dict) -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(_USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


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
    users = _load()
    if username in users:
        return False, "此帳號已存在。"
    salt = secrets.token_hex(16)
    users[username] = {"salt": salt, "hash": _hash(password, salt)}
    _save(users)
    portfolio_dir(username).mkdir(parents=True, exist_ok=True)
    return True, "註冊成功！"


def verify(username: str, password: str) -> bool:
    username = username.strip().lower()
    users = _load()
    rec = users.get(username)
    if not rec:
        return False
    return rec["hash"] == _hash(password, rec["salt"])


def portfolio_dir(username: str) -> Path:
    d = _DATA_DIR / "portfolios" / username.strip().lower()
    d.mkdir(parents=True, exist_ok=True)
    return d
