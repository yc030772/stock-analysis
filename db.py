from __future__ import annotations

import json
import os

# ══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════
_LEGACY_DB_FILE = os.path.join(os.path.dirname(__file__), "stocks_db.json")


def _db_file() -> str:
    """Return per-user db path when logged in, else legacy fallback."""
    try:
        import streamlit as st
        username = st.session_state.get("username")
        if username:
            from user_db import portfolio_dir
            return str(portfolio_dir(username) / "stocks_db.json")
    except Exception:
        pass
    return _LEGACY_DB_FILE

# Mock Taiwan market data: (category, sector, ticker, name, mcap_bn, pct_change)
# Taiwan convention: positive pct_change = red (上漲), negative = green (下跌)
MOCK_MARKET: list[tuple] = [
    ("電子", "半導體", "2330", "台積電",   15200, +2.3),
    ("電子", "半導體", "2454", "聯發科",    2800, +1.7),
    ("電子", "半導體", "2303", "聯電",       820, -0.5),
    ("電子", "半導體", "3443", "創意",       380, +3.1),
    ("電子", "半導體", "6415", "矽力-KY",   230, +1.2),
    ("電子", "半導體", "3661", "世芯-KY",   320, +2.8),
    ("電子", "半導體", "2408", "南亞科",    160, -1.3),
    ("電子", "半導體", "5269", "祥碩",      140, +0.9),
    ("電子", "AI/伺服器", "2382", "廣達",   1200, +3.5),
    ("電子", "AI/伺服器", "3231", "緯創",    580, +4.2),
    ("電子", "AI/伺服器", "2317", "鴻海",   1680, +1.4),
    ("電子", "AI/伺服器", "6669", "緯穎",    430, +5.6),
    ("電子", "AI/伺服器", "3017", "奇鋐",    320, +3.2),
    ("電子", "AI/伺服器", "2356", "英業達",  240, +2.1),
    ("電子", "AI/伺服器", "2059", "川湖",    280, +2.4),
    ("電子", "電子零組件", "2357", "華碩",   260, -0.8),
    ("電子", "電子零組件", "2376", "技嘉",   180, -1.5),
    ("電子", "電子零組件", "4938", "和碩",   190, -0.3),
    ("電子", "電子零組件", "2385", "群光",    95, +0.4),
    ("電子", "網通/PCB",   "6285", "啟碁",  130, +1.8),
    ("電子", "網通/PCB",   "3034", "聯詠",  160, +0.7),
    ("金融", "銀行/保險", "2881", "富邦金",  780, +0.5),
    ("金融", "銀行/保險", "2882", "國泰金",  620, +0.3),
    ("金融", "銀行/保險", "2891", "中信金",  430, +0.7),
    ("金融", "銀行/保險", "2885", "元大金",  290, +0.2),
    ("金融", "銀行/保險", "5880", "合庫金",  210, -0.1),
    ("金融", "銀行/保險", "2886", "兆豐金",  280, +0.4),
    ("傳產", "電信",       "2412", "中華電", 690, +0.1),
    ("傳產", "電信",       "3045", "台灣大", 180, -0.3),
    ("傳產", "電信",       "4904", "遠傳",   150, +0.2),
    ("傳產", "航運",       "2603", "長榮",   460, -2.1),
    ("傳產", "航運",       "2615", "萬海",   180, -3.4),
    ("傳產", "航運",       "2609", "陽明",   230, -2.8),
    ("傳產", "鋼鐵/石化",  "2002", "中鋼",  350, -0.8),
    ("傳產", "鋼鐵/石化",  "1301", "台塑",  320, -1.2),
    ("傳產", "鋼鐵/石化",  "1303", "南亞",  280, -0.9),
    ("生技", "生技醫療",   "6446", "藥華藥",  90, +2.4),
    ("生技", "生技醫療",   "6472", "保瑞",    72, +1.8),
    ("生技", "生技醫療",   "4142", "國光生",  40, -0.6),
    ("生技", "生技醫療",   "1795", "美時",    55, +1.1),
]


# ══════════════════════════════════════════════════════════════════════════════
# DB HELPERS
# ══════════════════════════════════════════════════════════════════════════════

_DEFAULT_GROUPS = [
    {"name": "自選群組 1", "stocks": []},
    {"name": "自選群組 2", "stocks": []},
]


def _read_raw() -> dict:
    """Read JSON, migrating legacy array format to {stocks, groups} on the fly."""
    try:
        with open(_db_file(), "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):          # legacy: plain array of stocks
            return {"stocks": data, "groups": [g.copy() for g in _DEFAULT_GROUPS]}
        return data
    except Exception:
        return {"stocks": [], "groups": [g.copy() for g in _DEFAULT_GROUPS]}


def load_db() -> list[dict]:
    return _read_raw().get("stocks", [])


def save_db(stocks: list[dict]) -> None:
    raw = _read_raw()
    raw["stocks"] = stocks
    with open(_db_file(), "w", encoding="utf-8") as f:
        json.dump(raw, f, ensure_ascii=False, indent=2)


def lookup_name(ticker: str) -> str | None:
    """Return Chinese name from MOCK_MARKET for a known ticker, else None."""
    code = ticker.upper().replace(".TWO", "").replace(".TW", "").strip()
    for _, _, t, name, _, _ in MOCK_MARKET:
        if t == code:
            return name
    return None


def load_groups() -> list[dict]:
    groups = _read_raw().get("groups", [])
    while len(groups) < 2:
        groups.append({"name": f"自選群組 {len(groups) + 1}", "stocks": []})
    return groups


def save_groups(groups: list[dict]) -> None:
    raw = _read_raw()
    raw["groups"] = groups
    with open(_db_file(), "w", encoding="utf-8") as f:
        json.dump(raw, f, ensure_ascii=False, indent=2)
