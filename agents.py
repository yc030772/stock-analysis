from __future__ import annotations

import streamlit as st

from data import fetch_ohlcv
from indicators import compute_indicators
from patterns import detect_patterns


# ══════════════════════════════════════════════════════════════════════════════
# AGENT 1: QUANT INDICATOR AGENT
# ══════════════════════════════════════════════════════════════════════════════

def quant_agent_report(ind: dict) -> dict:
    last, ma20, ma50 = ind["last"], ind["ma20"], ind["ma50"]
    rsi, hist, bb_pos = ind["rsi"], ind["macd_hist"], ind["bb_pos"]
    score   = 0.0
    bullets: list[str] = []

    if ma50 and last > ma20 > ma50:
        bullets.append("均線多頭排列：股價 > MA20 > MA50")
        score += 2
    elif ma50 and last < ma20 < ma50:
        bullets.append("均線空頭排列：股價 < MA20 < MA50")
        score -= 2
    else:
        bullets.append("均線盤整：排列尚未明確")

    if rsi >= 60:
        bullets.append(f"RSI {rsi:.1f} — 強勢區間，多頭主導")
        score += 1
    elif rsi <= 40:
        bullets.append(f"RSI {rsi:.1f} — 弱勢區間，空頭主導")
        score -= 1
    elif rsi >= 50:
        bullets.append(f"RSI {rsi:.1f} — 中性偏強")
        score += 0.5
    else:
        bullets.append(f"RSI {rsi:.1f} — 中性偏弱")
        score -= 0.5

    if hist > 0:
        bullets.append(f"MACD Hist {hist:+.4f} — 動能轉強")
        score += 1
    else:
        bullets.append(f"MACD Hist {hist:+.4f} — 動能轉弱")
        score -= 1

    if "上軌突破" in bb_pos:
        bullets.append(f"布林：{bb_pos} — 強勢但留意超買")
        score += 0.5
    elif "下軌跌破" in bb_pos:
        bullets.append(f"布林：{bb_pos} — 超賣但留意繼續破底")
        score -= 0.5
    elif "上方" in bb_pos:
        bullets.append(f"布林：{bb_pos} — 偏多格局")
        score += 0.5
    else:
        bullets.append(f"布林：{bb_pos} — 偏空格局")
        score -= 0.5

    if score >= 3:
        verdict = "強烈看多"
    elif score >= 1:
        verdict = "偏多"
    elif score <= -3:
        verdict = "強烈看空"
    elif score <= -1:
        verdict = "偏空"
    else:
        verdict = "盤整觀望"

    return {"score": score, "bullets": bullets, "verdict": verdict}


# ══════════════════════════════════════════════════════════════════════════════
# QUANT TIMEFRAME REPORTS  (short / mid / long horizon breakdown)
# ══════════════════════════════════════════════════════════════════════════════

def _grade(score: float) -> tuple[str, str, str]:
    """Return (verdict_str, css_class, hex_color) for a numeric score."""
    if score >= 2:
        return "強烈看多", "rpt-bull", "#3fb950"
    elif score >= 0.5:
        return "偏多",     "rpt-bull", "#85d498"
    elif score <= -2:
        return "強烈看空", "rpt-bear", "#f85149"
    elif score <= -0.5:
        return "偏空",     "rpt-bear", "#f97c77"
    else:
        return "盤整觀望", "rpt-neu",  "#8b949e"


def quant_timeframe_reports(
    ind: dict, q: dict
) -> tuple[dict, dict, dict]:
    """
    Returns (short_report, mid_report, long_report).
    Each report dict has keys: verdict, cls, color, bullets (list[str]), action (str).

    short  — 1 週: uses ma5, ma10, rsi7, macd_fast_hist, bb_fast_pos
    mid    — 1 月: reuses q["score"] and q["bullets"] directly
    long   — 半年: uses ma50, ma200, rsi21, bb_slow_pos
    """
    last = ind["last"]

    # ── Short-term (1 週) ────────────────────────────────────────────────────
    s_score = 0.0
    s_bullets: list[str] = []

    ma5  = ind.get("ma5")
    ma10 = ind.get("ma10")
    if ma5 and ma10:
        if last > ma5 > ma10:
            s_bullets.append("短均多頭：股價 > MA5 > MA10")
            s_score += 2
        elif last < ma5 < ma10:
            s_bullets.append("短均空頭：股價 < MA5 < MA10")
            s_score -= 2
        else:
            s_bullets.append("MA5/MA10 尚未明確排列")
    else:
        s_bullets.append("短均資料不足")

    rsi7 = ind.get("rsi7", 50.0)
    if rsi7 >= 65:
        s_bullets.append(f"RSI7 {rsi7:.1f} — 短線強勢")
        s_score += 1
    elif rsi7 <= 35:
        s_bullets.append(f"RSI7 {rsi7:.1f} — 短線弱勢")
        s_score -= 1
    elif rsi7 >= 50:
        s_bullets.append(f"RSI7 {rsi7:.1f} — 短線偏強")
        s_score += 0.5
    else:
        s_bullets.append(f"RSI7 {rsi7:.1f} — 短線偏弱")
        s_score -= 0.5

    mf_hist = ind.get("macd_fast_hist", 0.0)
    if mf_hist > 0:
        s_bullets.append(f"快速MACD Hist {mf_hist:+.4f} — 短線動能轉強")
        s_score += 1
    else:
        s_bullets.append(f"快速MACD Hist {mf_hist:+.4f} — 短線動能轉弱")
        s_score -= 1

    bb_fast = ind.get("bb_fast_pos", "中軌下方")
    if "上軌突破" in bb_fast:
        s_bullets.append(f"短期布林：{bb_fast} — 強勢但留意超買")
        s_score += 0.5
    elif "下軌跌破" in bb_fast:
        s_bullets.append(f"短期布林：{bb_fast} — 超賣留意支撐")
        s_score -= 0.5
    elif "上方" in bb_fast:
        s_bullets.append(f"短期布林：{bb_fast} — 偏多")
        s_score += 0.5
    else:
        s_bullets.append(f"短期布林：{bb_fast} — 偏空")
        s_score -= 0.5

    s_verdict, s_cls, s_color = _grade(s_score)
    if s_score >= 1:
        s_action = "短線可考慮佈局，設好停損後積極追蹤"
    elif s_score <= -1:
        s_action = "短線偏弱，觀望為主，避免追空"
    else:
        s_action = "短線方向不明，等待突破訊號確認"

    short_report = {
        "verdict": s_verdict,
        "cls": s_cls,
        "color": s_color,
        "bullets": s_bullets,
        "action": s_action,
        "score": s_score,
    }

    # ── Mid-term (1 月) — reuse quant_agent_report output ───────────────────
    m_score = q["score"]
    m_verdict, m_cls, m_color = _grade(m_score)
    if m_score >= 1:
        m_action = "中期偏多，可分批布局，留意均線支撐"
    elif m_score <= -1:
        m_action = "中期偏空，降低部位，等待均線翻多訊號"
    else:
        m_action = "中期盤整，縮手等待趨勢明朗化"

    mid_report = {
        "verdict": m_verdict,
        "cls": m_cls,
        "color": m_color,
        "bullets": list(q["bullets"]),
        "action": m_action,
        "score": m_score,
    }

    # ── Long-term (半年) ─────────────────────────────────────────────────────
    l_score = 0.0
    l_bullets: list[str] = []

    ma50  = ind.get("ma50")
    ma200 = ind.get("ma200")
    if ma50 and ma200:
        if last > ma50 > ma200:
            l_bullets.append("長均多頭排列：股價 > MA50 > MA200（黃金排列）")
            l_score += 2
        elif last < ma50 < ma200:
            l_bullets.append("長均空頭排列：股價 < MA50 < MA200（死亡排列）")
            l_score -= 2
        elif last > ma200:
            l_bullets.append("股價在 MA200 上方，長線偏多但 MA50 未配合")
            l_score += 0.5
        else:
            l_bullets.append("股價在 MA200 下方，長線偏空")
            l_score -= 0.5
    elif ma50:
        if last > ma50:
            l_bullets.append("股價在 MA50 上方（MA200 資料不足）")
            l_score += 0.5
        else:
            l_bullets.append("股價在 MA50 下方（MA200 資料不足）")
            l_score -= 0.5
    else:
        l_bullets.append("長均資料不足，無法判斷長期趨勢")

    rsi21 = ind.get("rsi21", 50.0)
    if rsi21 >= 60:
        l_bullets.append(f"RSI21 {rsi21:.1f} — 長線強勢")
        l_score += 1
    elif rsi21 <= 40:
        l_bullets.append(f"RSI21 {rsi21:.1f} — 長線弱勢")
        l_score -= 1
    elif rsi21 >= 50:
        l_bullets.append(f"RSI21 {rsi21:.1f} — 長線偏強")
        l_score += 0.5
    else:
        l_bullets.append(f"RSI21 {rsi21:.1f} — 長線偏弱")
        l_score -= 0.5

    bb_slow = ind.get("bb_slow_pos", "N/A（資料不足）")
    if "上軌突破" in bb_slow:
        l_bullets.append(f"長期布林：{bb_slow} — 強勢，留意高檔壓力")
        l_score += 0.5
    elif "下軌跌破" in bb_slow:
        l_bullets.append(f"長期布林：{bb_slow} — 超賣，留意長線底部")
        l_score -= 0.5
    elif "上方" in bb_slow:
        l_bullets.append(f"長期布林：{bb_slow} — 長線偏多格局")
        l_score += 0.5
    elif "下方" in bb_slow:
        l_bullets.append(f"長期布林：{bb_slow} — 長線偏空格局")
        l_score -= 0.5
    else:
        l_bullets.append(f"長期布林：{bb_slow}")

    l_verdict, l_cls, l_color = _grade(l_score)
    if l_score >= 1:
        l_action = "長期趨勢向好，持股待漲，逢回補倉"
    elif l_score <= -1:
        l_action = "長期趨勢偏弱，輕倉觀望，待均線重新多頭排列"
    else:
        l_action = "長線方向模糊，維持現有部位，等待突破確認"

    long_report = {
        "verdict": l_verdict,
        "cls": l_cls,
        "color": l_color,
        "bullets": l_bullets,
        "action": l_action,
        "score": l_score,
    }

    return short_report, mid_report, long_report


# ══════════════════════════════════════════════════════════════════════════════
# AGENT 2: CANDLESTICK PATTERN AGENT
# ══════════════════════════════════════════════════════════════════════════════

def pattern_agent_report(patterns: list[dict]) -> dict:
    bull_pts = sum(p["strength"] for p in patterns if p["type"] == "bull")
    bear_pts = sum(p["strength"] for p in patterns if p["type"] == "bear")
    recent   = [p for p in patterns if p["days_ago"] <= 3]

    if bull_pts > bear_pts + 2:
        verdict = "看多型態主導"
    elif bear_pts > bull_pts + 2:
        verdict = "看空型態主導"
    elif bull_pts > 0 or bear_pts > 0:
        verdict = "多空型態交錯"
    else:
        verdict = "無明顯型態"

    return {"bull_score": bull_pts, "bear_score": bear_pts,
            "recent": recent, "all": patterns, "verdict": verdict}


# ══════════════════════════════════════════════════════════════════════════════
# MASTER ORCHESTRATOR
# ══════════════════════════════════════════════════════════════════════════════

def run_orchestrator(held: bool, ind: dict, q: dict, p: dict,
                     combined_score: float | None = None) -> dict:
    pb, pbe = p["bull_score"], p["bear_score"]
    last = ind["last"]
    support, resistance = ind["support"], ind["resistance"]

    qs       = q["score"]
    combined = combined_score if combined_score is not None else qs

    strong_entry = not held and combined >= 2 and pb > pbe
    weak_entry   = not held and combined >= 1 and pb >= pbe
    strong_exit  = held     and combined <= -2 and pbe > pb
    weak_exit    = held     and combined <= -1 and pbe >= pb

    if strong_entry:
        signal, sig_class = "強烈入場訊號", "entry"
    elif strong_exit:
        signal, sig_class = "強烈出場訊號", "exit"
    elif weak_entry:
        signal, sig_class = "入場訊號", "entry"
    elif weak_exit:
        signal, sig_class = "出場訊號", "exit"
    else:
        signal, sig_class = "監控中", "watch"

    stop_loss = round(support * 0.98, 2)
    key_level = round((support + resistance) / 2, 2)

    # 短期目標：BB(20) 上軌 = MA20 + 2σ，統計上 95% 波動極限
    target1 = ind["bb_upper"]

    # 長期目標：近 120 日（或現有資料）最高收盤價；若已在歷史高點上方則用 ATR×3 延伸
    close_s  = ind["_s_close"]
    n_rows   = len(close_s)
    lookback = 120 if n_rows >= 120 else 60 if n_rows >= 60 else n_rows
    hist_max = float(close_s.iloc[-lookback:].max())
    if last >= hist_max:
        target2 = round(last + 3 * ind["atr14"], 2)
    else:
        target2 = round(hist_max, 2)

    recent_names = [pt["name"].split("(")[0].strip() for pt in p["recent"][:3]]
    reasons = []
    if recent_names:
        reasons.append(f"近期 K 線型態：{'、'.join(recent_names)}")
    reasons.append(f"量化評分：{q['verdict']} (分數 {qs:+.1f})")
    reasons.append(f"型態評分：{p['verdict']} (看多 {pb} / 看空 {pbe})")

    if sig_class == "entry":
        rec = (f"**建議積極觀察進場**。當前 {last:.2f}，"
               f"關鍵支撐 **{support}**，嚴守停損 **{stop_loss}**（支撐下 2%），"
               f"第一目標壓力 **{target1}**，擴展目標 **{target2}**。")
    elif sig_class == "exit":
        rec = (f"**建議考慮減倉或出場**。若跌破支撐 {support} 則執行停損 **{stop_loss}**，"
               f"當前壓力 {resistance}，請嚴格觀察多空訊號變化。")
    else:
        rec = (f"**訊號混沌，建議觀望等待確認**。"
               f"關鍵支撐 **{support}**，壓力 **{resistance}**，中間軸 **{key_level}**。"
               f"突破 {resistance} 轉多，跌破 {support} 轉空。")

    return {
        "signal": signal, "sig_class": sig_class,
        "reasons": reasons, "recommendation": rec,
        "stop_loss": stop_loss, "support": support,
        "resistance": resistance, "target1": target1,
        "target2": target2, "key_level": key_level,
    }


# ══════════════════════════════════════════════════════════════════════════════
# QUICK SIGNAL FOR SIDEBAR  (cached per ticker+held combo)
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=300, show_spinner=False)
def quick_signal(ticker: str, held: bool) -> dict:
    df = fetch_ohlcv(ticker, "90d")
    if df is None or len(df) < 20:
        return {
            "signal": "監控中", "sig_class": "watch",
            "last": None, "pct": None,
            "target1": None, "target2": None,
            "short_verdict": "N/A", "mid_verdict": "N/A", "long_verdict": "N/A",
            "pattern_verdict": "無明顯型態",
        }
    ind      = compute_indicators(df)
    patterns = detect_patterns(df)
    q        = quant_agent_report(ind)
    p        = pattern_agent_report(patterns)
    short_r, mid_r, long_r = quant_timeframe_reports(ind, q)
    combined = short_r["score"] * 0.25 + mid_r["score"] * 0.50 + long_r["score"] * 0.25
    orch     = run_orchestrator(held, ind, q, p, combined_score=combined)
    last = ind["last"]
    pct  = (last - float(df["Close"].iloc[-2])) / float(df["Close"].iloc[-2]) * 100 if len(df) >= 2 else 0.0
    return {
        "signal":          orch["signal"],
        "sig_class":       orch["sig_class"],
        "last":            last,
        "pct":             pct,
        "target1":         orch["target1"],
        "target2":         orch["target2"],
        "short_verdict":   short_r["verdict"],
        "mid_verdict":     mid_r["verdict"],
        "long_verdict":    long_r["verdict"],
        "pattern_verdict": p["verdict"],
    }
