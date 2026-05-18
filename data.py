from __future__ import annotations

import contextlib
import io
from typing import Optional

import pandas as pd
import streamlit as st
import yfinance as yf


# ══════════════════════════════════════════════════════════════════════════════
# DATA FETCHING
# ══════════════════════════════════════════════════════════════════════════════

def _quiet_fetch(ticker: str, **kwargs) -> pd.DataFrame:
    """Fetch yfinance history while suppressing delisted/no-data stderr warnings."""
    buf = io.StringIO()
    with contextlib.redirect_stderr(buf):
        return yf.Ticker(ticker).history(**kwargs)


def _ticker_variants(ticker: str) -> list[str]:
    """Return ticker + alternate suffix (.TW ↔ .TWO) so OTC stocks resolve."""
    t = ticker.strip().upper()
    variants = [ticker]
    if t.endswith(".TWO"):
        variants.append(ticker[:-4] + ".TW")
    elif t.endswith(".TW"):
        variants.append(ticker[:-3] + ".TWO")
    return variants


@st.cache_data(ttl=300, show_spinner=False)
def fetch_ohlcv(ticker: str, period: str = "180d") -> Optional[pd.DataFrame]:
    """Try original ticker + alternate suffix, then shorter periods on failure."""
    for t in _ticker_variants(ticker):
        for p in (period, "90d", "60d"):
            try:
                df = _quiet_fetch(t, period=p, interval="1d")
                if not df.empty and len(df) >= 20:
                    return df
            except Exception:
                continue
    return None


@st.cache_data(ttl=86400, show_spinner=False)
@st.cache_data(ttl=86400, show_spinner=False)
def _twse_name_map() -> dict[str, str]:
    """Fetch all TWSE-listed stock Chinese names from TWSE OpenAPI (cached 24h)."""
    import requests
    names: dict[str, str] = {}
    for url in [
        "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL",
        "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_peratio_analysis",
    ]:
        try:
            r = requests.get(url, timeout=8)
            for item in r.json():
                code = item.get("Code") or item.get("SecuritiesCompanyCode") or ""
                name = item.get("Name") or item.get("CompanyName") or ""
                if code and name:
                    names[code] = name
        except Exception:
            continue
    return names


def fetch_stock_name(ticker: str) -> str:
    """Return best display name: DB → TWSE Chinese name → yfinance → ticker."""
    from db import lookup_name
    known = lookup_name(ticker)
    if known:
        return known
    upper = ticker.upper()
    if ".TW" in upper:
        code = upper.split(".")[0]
        tw_name = _twse_name_map().get(code)
        if tw_name:
            return tw_name
    try:
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            info = yf.Ticker(ticker).info
        return info.get("shortName") or info.get("longName") or ticker
    except Exception:
        return ticker


@st.cache_data(ttl=60, show_spinner=False)
def fetch_index() -> tuple[str, str]:
    try:
        df = _quiet_fetch("^TWII", period="5d", interval="1d")
        if df is None or len(df) < 2:
            return "N/A", ""
        last = float(df["Close"].iloc[-1])
        prev = float(df["Close"].iloc[-2])
        chg  = last - prev
        pct  = chg / prev * 100
        return f"{last:,.2f}", f"{chg:+,.2f} ({pct:+.2f}%)"
    except Exception:
        return "N/A", ""
