from __future__ import annotations

import numpy as np
import pandas as pd


# ══════════════════════════════════════════════════════════════════════════════
# TECHNICAL INDICATORS  (Agent 1 core)
# ══════════════════════════════════════════════════════════════════════════════

def compute_indicators(df: pd.DataFrame) -> dict:
    close = df["Close"]
    n = len(close)

    ma20_s  = close.rolling(20).mean()
    ma50_s  = close.rolling(50).mean()
    ma200_s = close.rolling(200).mean()

    ma20  = float(ma20_s.iloc[-1])
    ma50  = float(ma50_s.iloc[-1]) if n >= 50  else None
    ma200 = float(ma200_s.iloc[-1]) if n >= 200 else None

    # RSI-14
    delta = close.diff()
    gain  = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
    loss  = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    rsi_s = 100 - 100 / (1 + gain / loss.replace(0, 1e-9))
    rsi   = float(rsi_s.iloc[-1])

    # MACD(12,26,9)
    ema12   = close.ewm(span=12, adjust=False).mean()
    ema26   = close.ewm(span=26, adjust=False).mean()
    macd_s  = ema12 - ema26
    sig_s   = macd_s.ewm(span=9, adjust=False).mean()
    hist_s  = macd_s - sig_s

    # Bollinger(20,2)
    bb_mid_s = close.rolling(20).mean()
    bb_std   = close.rolling(20).std()
    bb_up_s  = bb_mid_s + 2 * bb_std
    bb_lo_s  = bb_mid_s - 2 * bb_std

    last   = float(close.iloc[-1])
    bb_up  = float(bb_up_s.iloc[-1])
    bb_lo  = float(bb_lo_s.iloc[-1])
    bb_mid = float(bb_mid_s.iloc[-1])

    if last > bb_up:
        bb_pos = "上軌突破"
    elif last < bb_lo:
        bb_pos = "下軌跌破"
    elif last > bb_mid:
        bb_pos = "中軌上方"
    else:
        bb_pos = "中軌下方"

    # ── Short-term additions ─────────────────────────────────────────────────
    ma5_s  = close.rolling(5).mean()
    ma10_s = close.rolling(10).mean()
    ma5  = float(ma5_s.iloc[-1])  if n >= 5  else None
    ma10 = float(ma10_s.iloc[-1]) if n >= 10 else None

    gain7 = delta.clip(lower=0).ewm(alpha=1/7, adjust=False).mean()
    loss7 = (-delta.clip(upper=0)).ewm(alpha=1/7, adjust=False).mean()
    rsi7  = float((100 - 100 / (1 + gain7 / loss7.replace(0, 1e-9))).iloc[-1])

    ema5_   = close.ewm(span=5,  adjust=False).mean()
    ema13_  = close.ewm(span=13, adjust=False).mean()
    mf_line = ema5_ - ema13_
    mf_hist = float((mf_line - mf_line.ewm(span=5, adjust=False).mean()).iloc[-1])

    bb10_m_s  = close.rolling(10).mean()
    bb10_up_  = float((bb10_m_s + 2 * close.rolling(10).std()).iloc[-1])
    bb10_lo_  = float((bb10_m_s - 2 * close.rolling(10).std()).iloc[-1])
    bb10_mid_ = float(bb10_m_s.iloc[-1])
    if   last > bb10_up_:    bb_fast_pos = "上軌突破"
    elif last < bb10_lo_:    bb_fast_pos = "下軌跌破"
    elif last > bb10_mid_:   bb_fast_pos = "中軌上方"
    else:                    bb_fast_pos = "中軌下方"

    # ── Long-term additions ───────────────────────────────────────────────────
    gain21 = delta.clip(lower=0).ewm(alpha=1/21, adjust=False).mean()
    loss21 = (-delta.clip(upper=0)).ewm(alpha=1/21, adjust=False).mean()
    rsi21  = float((100 - 100 / (1 + gain21 / loss21.replace(0, 1e-9))).iloc[-1])

    ma100_s = close.rolling(100).mean()
    ma100   = float(ma100_s.iloc[-1]) if n >= 100 else None

    if n >= 50:
        bb50_m_s = close.rolling(50).mean()
        bb50_up_ = float((bb50_m_s + 2 * close.rolling(50).std()).iloc[-1])
        bb50_lo_ = float((bb50_m_s - 2 * close.rolling(50).std()).iloc[-1])
        bb50_mid_= float(bb50_m_s.iloc[-1])
        if   last > bb50_up_:  bb_slow_pos = "上軌突破"
        elif last < bb50_lo_:  bb_slow_pos = "下軌跌破"
        elif last > bb50_mid_: bb_slow_pos = "中軌上方"
        else:                  bb_slow_pos = "中軌下方"
    else:
        bb_slow_pos = "N/A（資料不足）"

    # ATR-14
    high_s = df["High"]
    low_s  = df["Low"]
    tr_s   = pd.concat([
        high_s - low_s,
        (high_s - close.shift(1)).abs(),
        (low_s  - close.shift(1)).abs(),
    ], axis=1).max(axis=1)
    atr14 = float(tr_s.rolling(14).mean().iloc[-1])

    support    = float(df["Low"].iloc[-20:].min())
    resistance = float(df["High"].iloc[-20:].max())

    trend = (
        "bull"    if (ma50 and last > ma20 and last > ma50 and rsi < 72)
        else "bear"    if (ma50 and last < ma20 and last < ma50 and rsi > 28)
        else "neutral"
    )

    return {
        "last": last,
        "ma20": round(ma20, 2),
        "ma50": round(ma50, 2) if ma50 else None,
        "ma200": round(ma200, 2) if ma200 else None,
        "rsi": round(rsi, 2),
        "macd": round(float(macd_s.iloc[-1]), 4),
        "macd_signal": round(float(sig_s.iloc[-1]), 4),
        "macd_hist": round(float(hist_s.iloc[-1]), 4),
        "bb_upper": round(bb_up, 2),
        "bb_mid": round(bb_mid, 2),
        "bb_lower": round(bb_lo, 2),
        "bb_pos": bb_pos,
        "ma5": round(ma5, 2) if ma5 else None,
        "ma10": round(ma10, 2) if ma10 else None,
        "rsi7": round(rsi7, 2),
        "macd_fast_hist": round(mf_hist, 4),
        "bb_fast_pos": bb_fast_pos,
        "rsi21": round(rsi21, 2),
        "ma100": round(ma100, 2) if ma100 else None,
        "bb_slow_pos": bb_slow_pos,
        "atr14": round(atr14, 4),
        "support": round(support, 2),
        "resistance": round(resistance, 2),
        "trend": trend,
        # Series for charts
        "_s_close": close,
        "_s_open": df["Open"],
        "_s_high": df["High"],
        "_s_low": df["Low"],
        "_s_vol": df["Volume"],
        "_s_ma20": ma20_s,
        "_s_ma50": ma50_s if n >= 50 else None,
        "_s_ma200": ma200_s if n >= 200 else None,
        "_s_bb_up": bb_up_s,
        "_s_bb_mid": bb_mid_s,
        "_s_bb_lo": bb_lo_s,
        "_s_rsi": rsi_s,
        "_s_macd": macd_s,
        "_s_macd_sig": sig_s,
        "_s_macd_hist": hist_s,
    }
