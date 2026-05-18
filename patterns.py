from __future__ import annotations

import numpy as np
import pandas as pd


# ══════════════════════════════════════════════════════════════════════════════
# 20 CANDLESTICK PATTERN DETECTION  (Agent 2 core)
# ══════════════════════════════════════════════════════════════════════════════

def detect_patterns(df: pd.DataFrame, lookback: int = 6) -> list[dict]:
    o = df["Open"].values.astype(float)
    h = df["High"].values.astype(float)
    l = df["Low"].values.astype(float)
    c = df["Close"].values.astype(float)
    n = len(c)
    found: list[dict] = []

    def body(i):  return abs(c[i] - o[i])
    def rng(i):   return max(h[i] - l[i], 1e-8)
    def ush(i):   return h[i] - max(c[i], o[i])
    def lsh(i):   return min(c[i], o[i]) - l[i]
    def bull(i):  return c[i] > o[i]
    def bear(i):  return c[i] < o[i]
    def mid(i):   return (o[i] + c[i]) / 2

    def add(name, ptype, days_ago, desc, strength=2):
        found.append({"name": name, "type": ptype, "days_ago": days_ago,
                      "desc": desc, "strength": strength})

    start = max(4, n - lookback - 4)

    for i in range(start, n):
        da = n - 1 - i
        br = body(i) / rng(i)

        # ── 1 & 11. Hammer / Hanging Man ─────────────────────────────────────
        if br < 0.35 and lsh(i) > 2 * body(i) and ush(i) < 0.5 * body(i) and body(i) > 0:
            if i >= 3:
                if c[i - 3] > c[i - 1]:  # falling prior trend
                    add("錘子線 (Hammer)", "bull", da,
                        "下降趨勢末端，下影線長 → 賣壓被買方吸收，底部反轉訊號", 3)
                else:
                    add("吊頸線 (Hanging Man)", "bear", da,
                        "上升趨勢末端出現錘形 → 頭部警示，需隔日確認", 2)

        # ── 2 & 12. Inverted Hammer / Shooting Star ───────────────────────────
        if br < 0.35 and ush(i) > 2 * body(i) and lsh(i) < 0.5 * body(i) and body(i) > 0:
            if i >= 3:
                if c[i - 3] > c[i - 1]:
                    add("倒錘子線 (Inverted Hammer)", "bull", da,
                        "底部出現，上影長 → 買方試圖推高，潛在反轉需確認", 2)
                else:
                    add("流星線 (Shooting Star)", "bear", da,
                        "頭部出現，上衝遭賣壓壓回 → 強烈看空反轉訊號", 3)

        # ── 20. Tombstone Doji ────────────────────────────────────────────────
        if br < 0.1 and ush(i) > 0.65 * rng(i) and lsh(i) < 0.12 * rng(i):
            add("墓碑十字 (Tombstone Doji)", "bear", da,
                "開收盤接近低點，上影極長 → 強烈看空十字星", 3)

        # ── Two-candle patterns ───────────────────────────────────────────────
        if i >= 1:
            # 4. Bullish Engulfing
            if bear(i - 1) and bull(i):
                if o[i] <= c[i - 1] and c[i] >= o[i - 1] and body(i) > body(i - 1):
                    add("多頭吞噬 (Bullish Engulfing)", "bull", da,
                        "陽線完全吞噬前日陰線 → 強力底部反轉訊號", 3)

            # 14. Bearish Engulfing
            if bull(i - 1) and bear(i):
                if o[i] >= c[i - 1] and c[i] <= o[i - 1] and body(i) > body(i - 1):
                    add("空頭吞噬 (Bearish Engulfing)", "bear", da,
                        "陰線完全吞噬前日陽線 → 強力頭部反轉訊號", 3)

            # 5. Piercing Line
            if bear(i - 1) and bull(i) and body(i - 1) > rng(i - 1) * 0.4:
                if o[i] < l[i - 1] and c[i] > mid(i - 1) and c[i] < o[i - 1]:
                    add("曙光初現 (Piercing Line)", "bull", da,
                        "陽線開低走高，收超前日中點 → 底部反轉", 2)

            # 6. Thrusting Pattern
            if bear(i - 1) and bull(i) and body(i - 1) > rng(i - 1) * 0.4:
                if o[i] < l[i - 1] and c[i] > c[i - 1] and c[i] <= mid(i - 1):
                    add("貫穿線 (Thrusting Pattern)", "bull", da,
                        "陽線開低走高但未過中點，偏弱看多訊號", 1)

            # 15. Dark Cloud Cover
            if bull(i - 1) and bear(i) and body(i - 1) > rng(i - 1) * 0.4:
                if o[i] > h[i - 1] and c[i] < mid(i - 1) and c[i] > o[i - 1]:
                    add("烏雲罩頂 (Dark Cloud Cover)", "bear", da,
                        "陰線開高走低收入前日陽線中點以下 → 頭部反轉", 2)

        # ── Three-candle patterns ─────────────────────────────────────────────
        if i >= 2:
            # 3. Morning Star
            if (bear(i - 2) and body(i - 2) / rng(i - 2) > 0.45
                    and body(i - 1) / rng(i - 1) < 0.3
                    and bull(i) and c[i] > mid(i - 2)):
                add("晨星 (Morning Star)", "bull", da,
                    "大陰→小實體→大陽，底部三日反轉組合，強力看多", 3)

            # 13. Evening Star
            if (bull(i - 2) and body(i - 2) / rng(i - 2) > 0.45
                    and body(i - 1) / rng(i - 1) < 0.3
                    and bear(i) and c[i] < mid(i - 2)):
                add("暮星 (Evening Star)", "bear", da,
                    "大陽→小實體→大陰，頭部三日反轉組合，強力看空", 3)

            # 7. Three White Soldiers
            if (all(bull(j) for j in [i - 2, i - 1, i])
                    and c[i - 2] < c[i - 1] < c[i]
                    and all(body(j) / rng(j) > 0.5 for j in [i - 2, i - 1, i])):
                add("三個白兵 (Three White Soldiers)", "bull", da,
                    "三連大陽線，收盤逐步墊高 → 強力多頭延續", 3)

            # 16. Three Black Crows
            if (all(bear(j) for j in [i - 2, i - 1, i])
                    and c[i - 2] > c[i - 1] > c[i]
                    and all(body(j) / rng(j) > 0.5 for j in [i - 2, i - 1, i])):
                add("三隻烏鴉 (Three Black Crows)", "bear", da,
                    "三連大陰線，收盤逐步下滑 → 強力空頭延續", 3)

        # ── Five-candle patterns ──────────────────────────────────────────────
        if i >= 4:
            # 10. Rising Three Methods
            if (bull(i - 4) and body(i - 4) / rng(i - 4) > 0.5
                    and all(bear(j) for j in [i - 3, i - 2, i - 1])
                    and all(l[j] > l[i - 4] and h[j] < h[i - 4] for j in [i - 3, i - 2, i - 1])
                    and bull(i) and c[i] > c[i - 4]):
                add("上升三法 (Rising Three Methods)", "bull", da,
                    "大陽→三小陰回調→大陽突破，多頭格局延續訊號", 3)

            # 19. Falling Three Methods
            if (bear(i - 4) and body(i - 4) / rng(i - 4) > 0.5
                    and all(bull(j) for j in [i - 3, i - 2, i - 1])
                    and all(l[j] > l[i - 4] and h[j] < h[i - 4] for j in [i - 3, i - 2, i - 1])
                    and bear(i) and c[i] < c[i - 4]):
                add("下降三法 (Falling Three Methods)", "bear", da,
                    "大陰→三小陽反彈→大陰跌破，空頭格局延續訊號", 3)

    # Chart patterns (need >= 20 candles)
    if n >= 20:
        found.extend(_chart_patterns(h, l, c, n))

    # Deduplicate by name, keep first (smallest days_ago)
    seen: dict[str, dict] = {}
    for p in found:
        if p["name"] not in seen:
            seen[p["name"]] = p
    return sorted(seen.values(), key=lambda x: x["days_ago"])


def _chart_patterns(h: np.ndarray, l: np.ndarray, c: np.ndarray, n: int) -> list[dict]:
    found = []
    win = min(40, n)
    rh, rl, rc = h[-win:], l[-win:], c[-win:]
    wn = len(rh)

    peaks   = [(i, rh[i]) for i in range(1, wn - 1) if rh[i] > rh[i - 1] and rh[i] > rh[i + 1]]
    troughs = [(i, rl[i]) for i in range(1, wn - 1) if rl[i] < rl[i - 1] and rl[i] < rl[i + 1]]

    tol    = 0.027
    last_p = rc[-1]

    # 17. Double Top
    if len(peaks) >= 2:
        p1, p2 = peaks[-2], peaks[-1]
        if p2[0] - p1[0] >= 4 and abs(p1[1] - p2[1]) / p2[1] < tol and last_p < p2[1] * 0.985:
            neck = float(np.min(rc[p1[0]: p2[0] + 1])) if p1[0] < p2[0] else rc[p1[0]]
            da = wn - 1 - p2[0]
            found.append({"name": "雙頂/M頂 (Double Top)", "type": "bear", "days_ago": da,
                          "desc": f"兩峰相近 ({p1[1]:.1f}↔{p2[1]:.1f})，頸線≈{neck:.1f}，跌破確認看空",
                          "strength": 3})

    # 8. Double Bottom
    if len(troughs) >= 2:
        t1, t2 = troughs[-2], troughs[-1]
        if t2[0] - t1[0] >= 4 and abs(t1[1] - t2[1]) / t2[1] < tol and last_p > t2[1] * 1.015:
            da = wn - 1 - t2[0]
            found.append({"name": "雙底/W底 (Double Bottom)", "type": "bull", "days_ago": da,
                          "desc": f"兩谷相近 ({t1[1]:.1f}↔{t2[1]:.1f})，支撐確認，突破頸線看多",
                          "strength": 3})

    # 18. Head and Shoulders Top
    if len(peaks) >= 3:
        s1, head, s2 = peaks[-3], peaks[-2], peaks[-1]
        if (head[1] > s1[1] * 1.01 and head[1] > s2[1] * 1.01
                and abs(s1[1] - s2[1]) / s1[1] < 0.04):
            da = wn - 1 - s2[0]
            found.append({"name": "頭肩頂 (Head and Shoulders Top)", "type": "bear", "days_ago": da,
                          "desc": f"左肩{s1[1]:.1f} 頭{head[1]:.1f} 右肩{s2[1]:.1f}，頸線跌破確認",
                          "strength": 3})

    # 9. Head and Shoulders Bottom
    if len(troughs) >= 3:
        s1, head, s2 = troughs[-3], troughs[-2], troughs[-1]
        if (head[1] < s1[1] * 0.99 and head[1] < s2[1] * 0.99
                and abs(s1[1] - s2[1]) / s1[1] < 0.04):
            da = wn - 1 - s2[0]
            found.append({"name": "頭肩底 (Head and Shoulders Bottom)", "type": "bull", "days_ago": da,
                          "desc": f"左肩{s1[1]:.1f} 頭{head[1]:.1f} 右肩{s2[1]:.1f}，倒頭肩底部反轉",
                          "strength": 3})

    return found
