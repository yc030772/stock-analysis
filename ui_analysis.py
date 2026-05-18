from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from data import fetch_ohlcv
from indicators import compute_indicators
from patterns import detect_patterns
from agents import (
    quant_agent_report,
    quant_timeframe_reports,
    pattern_agent_report,
    run_orchestrator,
)
from charts import _DARK_LAYOUT, build_candle_chart, build_quant_chart


# ══════════════════════════════════════════════════════════════════════════════
# UI — TAB 2: STOCK ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════

def _kpi(label: str, value: str, delta: str = "", delta_class: str = "neu") -> str:
    return (f'<div class="kbox"><div class="klabel">{label}</div>'
            f'<div class="kval">{value}</div>'
            f'<div class="kdelta {delta_class}">{delta}</div></div>')


def _build_level_chart(
    orch: dict,
    last: float,
    df: pd.DataFrame | None = None,
    ind: dict | None = None,
) -> go.Figure:
    stop    = float(orch["stop_loss"])
    sup     = float(orch["support"])
    mid_lvl = float(orch["key_level"])
    t1      = float(orch["target1"])
    t2      = float(orch["target2"])

    pct_t1   = (t1   - last) / last * 100
    pct_t2   = (t2   - last) / last * 100
    pct_stop = (stop - last) / last * 100
    pct_sup  = (sup  - last) / last * 100

    levels = [
        (stop,    f"嚴格停損  {pct_stop:+.1f}%", "#f85149", "dash",    1.5),
        (sup,     f"關鍵支撐  {pct_sup:+.1f}%",  "#f97c77", "dot",     1.5),
        (mid_lvl, "中間軸",                        "#8b949e", "dashdot", 1.5),
        (last,    "當前價",                         "#f0883e", "solid",   2.5),
        (t1,      f"第一目標  {pct_t1:+.1f}%",   "#58a6ff", "dot",     1.5),
        (t2,      f"擴展目標  {pct_t2:+.1f}%",   "#bc8cff", "dot",     1.5),
    ]

    if df is not None:
        # ── Candlestick background (6-month default) ─────────────────────────
        fig = go.Figure()

        fig.add_trace(go.Candlestick(
            x=df.index,
            open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"],
            increasing=dict(line=dict(color="#f85149"), fillcolor="#f85149"),
            decreasing=dict(line=dict(color="#3fb950"), fillcolor="#3fb950"),
            name="K 線", showlegend=False,
        ))

        if ind is not None:
            for s_key, color, lbl in [
                ("_s_ma20", "#e3b341", "MA20"),
                ("_s_ma50", "#58a6ff", "MA50"),
            ]:
                if ind.get(s_key) is not None:
                    fig.add_trace(go.Scatter(
                        x=df.index, y=ind[s_key], mode="lines",
                        line=dict(color=color, width=1.0),
                        name=lbl, opacity=0.6, showlegend=True,
                    ))

        # Level lines span full plot width; labels sit outside right edge
        for price, label, color, dash, lw in levels:
            fig.add_shape(
                type="line", x0=0, x1=1, xref="paper",
                y0=price, y1=price, yref="y",
                line=dict(color=color, width=lw, dash=dash),
            )
            fig.add_annotation(
                x=1.01, xref="paper", y=price, yref="y",
                text=f"<b>{label}</b>",
                showarrow=False,
                font=dict(color=color, size=10),
                xanchor="left", yanchor="middle",
            )

        fig.add_trace(go.Scatter(
            x=[df.index[-1]], y=[last],
            mode="markers",
            marker=dict(color="#f0883e", size=12, symbol="diamond",
                        line=dict(color="#ffffff", width=1.5)),
            showlegend=False, hoverinfo="skip",
        ))

        fig.update_layout(
            **_DARK_LAYOUT,
            height=440,
            margin=dict(l=10, r=175, t=20, b=14),
            xaxis=dict(
                rangeslider_visible=False,
                showgrid=False, zeroline=False,
            ),
            yaxis=dict(
                tickformat=",.2f",
                tickcolor="#8b949e",
                gridcolor="rgba(48,54,61,0.5)",
                zeroline=False,
            ),
            showlegend=True,
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02,
                        xanchor="left", x=0, font=dict(size=10)),
        )
        return fig

    # ── Fallback: horizontal-lines-only (no OHLCV) ───────────────────────────
    all_p  = sorted([stop, sup, mid_lvl, last, t1, t2])
    spread = all_p[-1] - all_p[0]
    pad    = spread * 0.10
    y_min  = all_p[0]  - pad
    y_max  = all_p[-1] + pad

    fig = go.Figure()
    fig.add_hrect(y0=y_min, y1=stop,  fillcolor="rgba(248,81,73,0.10)", line_width=0)
    fig.add_hrect(y0=stop,  y1=sup,   fillcolor="rgba(248,81,73,0.05)", line_width=0)
    fig.add_hrect(y0=t1,    y1=y_max, fillcolor="rgba(63,185,80,0.10)", line_width=0)

    for price, label, color, dash, lw in levels:
        fig.add_shape(
            type="line", x0=0.02, x1=0.72, xref="paper",
            y0=price, y1=price, yref="y",
            line=dict(color=color, width=lw, dash=dash),
        )
        fig.add_annotation(
            x=0.74, xref="paper", y=price, yref="y",
            text=f"<b>{label}</b>",
            showarrow=False,
            font=dict(color=color, size=11),
            xanchor="left", yanchor="middle",
        )

    fig.add_trace(go.Scatter(
        x=[0.37], y=[last], mode="markers",
        marker=dict(color="#f0883e", size=14, symbol="diamond",
                    line=dict(color="#ffffff", width=1.5)),
        showlegend=False, hoverinfo="skip",
    ))

    for x_pos, target, pct, color in [
        (0.54, t1, pct_t1, "#58a6ff"),
        (0.63, t2, pct_t2, "#bc8cff"),
    ]:
        fig.add_annotation(
            x=x_pos, xref="x", y=target, yref="y",
            ax=x_pos, axref="x", ay=last, ayref="y",
            text=f"<b>{pct:+.1f}%</b>",
            showarrow=True, arrowhead=2, arrowsize=1.2, arrowwidth=2,
            arrowcolor=color, font=dict(color=color, size=11),
            xanchor="center",
            yanchor="bottom" if target > last else "top",
            bgcolor="rgba(22,27,34,0.88)",
            bordercolor=color, borderwidth=1, borderpad=4,
        )

    fig.update_layout(
        **_DARK_LAYOUT,
        height=320,
        margin=dict(l=10, r=10, t=14, b=14),
        xaxis=dict(visible=False, range=[0, 1], fixedrange=True),
        yaxis=dict(
            tickformat=",.2f", tickcolor="#8b949e",
            gridcolor="rgba(48,54,61,0.5)", zeroline=False,
            range=[y_min, y_max],
        ),
        showlegend=False, hovermode=False,
    )
    return fig


def render_analysis_tab(stocks: list[dict]) -> None:
    if not stocks:
        st.info("請先在左側新增追蹤股票。")
        return

    stock_map = {s["stock_id"]: s for s in stocks}

    st.markdown('<div class="sec-title">搜尋分析標的</div>', unsafe_allow_html=True)
    default_val = st.session_state.get("selected_stock", stocks[0]["stock_id"] if stocks else "")
    if "stock_search" not in st.session_state:
        st.session_state.stock_search = default_val
    query = st.text_input(
        "搜尋股票代碼", placeholder="輸入股票代碼，例如 2330.TW",
        label_visibility="collapsed", key="stock_search",
    )
    ticker = query.strip() if query.strip() else default_val

    # Watchlist suggestions (shown when query partially matches)
    if query.strip():
        suggs = [s for s in stocks
                 if query.upper() in s["stock_id"].upper() or query in s["stock_name"]]
        # Only show suggestions if query isn't already an exact match
        if suggs and query.strip().upper() not in {s["stock_id"].upper() for s in suggs}:
            sugg_cols = st.columns(min(len(suggs), 4))
            for col, sg in zip(sugg_cols, suggs[:4]):
                with col:
                    if st.button(f"{sg['stock_id']}  {sg['stock_name']}",
                                 key=f"sq_{sg['stock_id']}", use_container_width=True):
                        st.session_state.selected_stock = sg["stock_id"]
                        st.session_state.stock_search = sg["stock_id"]
                        st.rerun()

    st.session_state.selected_stock = ticker
    stock_info = stock_map.get(ticker)
    held = stock_info["holding_status"] if stock_info else False

    with st.spinner(f"⚙️ 分析 {ticker} 中，請稍候..."):
        df = fetch_ohlcv(ticker, "180d")

    if df is None or len(df) < 20:
        st.error(
            f"無法取得 **{ticker}** 的歷史資料。\n\n"
            "請確認代碼格式，例如台股需加 `.TW`：`2330.TW`"
        )
        return

    ind               = compute_indicators(df)
    patterns          = detect_patterns(df, lookback=10)
    q                 = quant_agent_report(ind)
    p                 = pattern_agent_report(patterns)
    short_r, mid_r, long_r = quant_timeframe_reports(ind, q)
    combined          = short_r["score"] * 0.25 + mid_r["score"] * 0.50 + long_r["score"] * 0.25
    orch              = run_orchestrator(held, ind, q, p, combined_score=combined)

    last    = ind["last"]
    prev    = float(df["Close"].iloc[-2])
    day_chg = last - prev
    day_pct = day_chg / prev * 100
    pct_cls = "pos" if day_pct > 0 else "neg" if day_pct < 0 else "neu"

    # ── Sub-tabs ──────────────────────────────────────────────────────────────
    ta, tb, tc = st.tabs([
        "量化與籌碼特徵",
        "K 線型態視覺化",
        "策略交叉驗證報告",
    ])

    # ════════════════════════════════ TAB A ══════════════════════════════════
    with ta:
        st.markdown(
            '<div class="kgrid">'
            + _kpi("收盤價", f"{last:.2f}",
                   f"{day_chg:+.2f} ({day_pct:+.2f}%)", pct_cls)
            + _kpi("RSI (14)", f"{ind['rsi']:.1f}", "",
                   "pos" if ind["rsi"] >= 60 else "neg" if ind["rsi"] <= 40 else "neu")
            + _kpi("MACD Hist", f"{ind['macd_hist']:+.4f}", "",
                   "pos" if ind["macd_hist"] > 0 else "neg")
            + _kpi("MA20", f"{ind['ma20']:.2f}",
                   "股價上方" if last > ind["ma20"] else "股價下方",
                   "pos" if last > ind["ma20"] else "neg")
            + _kpi("MA50", f"{ind['ma50']:.2f}" if ind["ma50"] else "N/A",
                   ("上方" if last > ind["ma50"] else "下方") if ind["ma50"] else "",
                   "pos" if ind["ma50"] and last > ind["ma50"] else "neg")
            + _kpi("布林位置", ind["bb_pos"].split()[0],
                   " ".join(ind["bb_pos"].split()[1:]))
            + _kpi("近20日支撐", f"{ind['support']:.2f}", "", "neg")
            + _kpi("近20日壓力", f"{ind['resistance']:.2f}", "", "pos")
            + '</div>',
            unsafe_allow_html=True,
        )

        st.markdown('<div class="sec-title">Agent 1：多時間框架量化分析</div>',
                    unsafe_allow_html=True)
        for h_label, h_sub, hr in [
            ("短期", "1 週操作", short_r),
            ("中期", "1 月操作", mid_r),
            ("長期", "半年操作", long_r),
        ]:
            with st.expander(f"{h_label}（{h_sub}）— {hr['verdict']}", expanded=True):
                bul_html = "".join(f"<div style='margin:3px 0;'>• {b}</div>" for b in hr["bullets"])
                act_html = f'<div style="margin-top:10px;padding:8px 12px;background:#21262d;border-radius:6px;color:{hr["color"]};font-weight:600;">操作建議：{hr["action"]}</div>'
                st.markdown(f'<div class="rpt {hr["cls"]}">{bul_html}{act_html}</div>', unsafe_allow_html=True)

        st.markdown('<div class="sec-title">MACD + 成交量圖表</div>', unsafe_allow_html=True)
        st.plotly_chart(build_quant_chart(df, ind), use_container_width=True,
                        key=f"ta_quant_{ticker}")

        # RSI gauge
        st.markdown('<div class="sec-title">RSI 狀態</div>', unsafe_allow_html=True)
        fig_rsi = go.Figure(go.Indicator(
            mode="gauge+number",
            value=ind["rsi"],
            number={"font": {"color": "#c9d1d9"}},
            gauge={
                "axis": {"range": [0, 100], "tickcolor": "#8b949e"},
                "bar":  {"color": "#f0883e"},
                "steps": [
                    {"range": [0, 30],  "color": "rgba(63,185,80,0.15)"},
                    {"range": [30, 70], "color": "rgba(139,148,158,0.08)"},
                    {"range": [70, 100],"color": "rgba(248,81,73,0.15)"},
                ],
                "threshold": {"line": {"color": "#58a6ff", "width": 2},
                              "thickness": 0.75, "value": ind["rsi"]},
            },
        ))
        fig_rsi.update_layout(**_DARK_LAYOUT, height=200, margin=dict(l=20, r=20, t=10, b=10))
        st.plotly_chart(fig_rsi, use_container_width=True, key=f"ta_rsi_{ticker}")

    # ════════════════════════════════ TAB B ══════════════════════════════════
    with tb:
        st.markdown('<div class="sec-title">K 線圖 + 均線 + 布林帶 + 型態標注</div>',
                    unsafe_allow_html=True)
        st.plotly_chart(build_candle_chart(df, ind, patterns), use_container_width=True,
                        key=f"tb_candle_{ticker}")

        st.markdown('<div class="sec-title">Agent 2：K 線型態大師偵測結果</div>',
                    unsafe_allow_html=True)

        if not patterns:
            st.info("近期未偵測到明顯 K 線型態組合（可能處於盤整或走勢不明確）。")
        else:
            # Pills summary
            pills = ""
            for pat in patterns:
                cls = "pp-bull" if pat["type"] == "bull" else "pp-bear"
                short = pat["name"].split("(")[0].strip()
                pills += f'<span class="pp {cls}">{short}</span>'
            st.markdown(pills, unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            # Detail table
            pat_df = pd.DataFrame([{
                "型態名稱": p["name"],
                "多空屬性": "看多" if p["type"] == "bull" else "看空",
                "距今 (天)": p["days_ago"],
                "強度": "★" * p["strength"],
                "說明": p["desc"],
            } for p in patterns])
            st.dataframe(pat_df, hide_index=True, use_container_width=True)

            # Highlight recent
            recent = [p for p in patterns if p["days_ago"] <= 3]
            if recent:
                st.markdown('<div class="sec-title">近 3 日重要型態提示</div>',
                            unsafe_allow_html=True)
                for pat in recent:
                    rc_cls = "rpt-bull" if pat["type"] == "bull" else "rpt-bear"
                    da_str = "今日" if pat["days_ago"] == 0 else f"{pat['days_ago']} 天前"
                    dot_c  = "#3fb950" if pat["type"] == "bull" else "#f85149"
                    st.markdown(
                        f'<div class="rpt {rc_cls}">'
                        f'<b><span style="color:{dot_c}">●</span> {da_str}偵測到：{pat["name"]}</b><br>'
                        f'<span style="color:#8b949e;">{pat["desc"]}</span>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

    # ════════════════════════════════ TAB C ══════════════════════════════════
    with tc:
        # Signal banner
        banner_cls_map = {"entry": "sig-entry", "exit": "sig-exit", "watch": "sig-watch"}
        b_cls    = banner_cls_map[orch["sig_class"]]
        held_str = "（持有中）" if held else "（未持有）"
        st.markdown(
            f'<div class="sig-banner {b_cls}">{orch["signal"]}&nbsp;&nbsp;{held_str}</div>',
            unsafe_allow_html=True,
        )

        # Key levels chart
        st.plotly_chart(_build_level_chart(orch, last, df=df, ind=ind),
                        use_container_width=True, key=f"tc_level_{ticker}")

        # Agent 1 report
        st.markdown('<div class="sec-title">Agent 1：量化指標官</div>', unsafe_allow_html=True)
        cls1 = "rpt-bull" if q["score"] > 0 else "rpt-bear" if q["score"] < 0 else "rpt-neu"
        v_cls1 = ("v-strong-bull" if q["score"] >= 3 else "v-bull" if q["score"] >= 1
                  else "v-strong-bear" if q["score"] <= -3 else "v-bear" if q["score"] <= -1 else "v-neu")
        bul  = "".join(f"<div style='margin:2px 0;'>{b}</div>" for b in q["bullets"])
        st.markdown(
            f'<div class="rpt {cls1}"><b>結論：<span class="{v_cls1}">{q["verdict"]}</span></b><br><br>{bul}</div>',
            unsafe_allow_html=True,
        )

        # Agent 2 report
        st.markdown('<div class="sec-title">Agent 2：K 線型態大師</div>',
                    unsafe_allow_html=True)
        cls2  = ("rpt-bull" if p["bull_score"] > p["bear_score"]
                 else "rpt-bear" if p["bear_score"] > p["bull_score"]
                 else "rpt-neu")
        r_names = "、".join(pt["name"].split("(")[0].strip() for pt in p["recent"]) or "近期無顯著型態"
        st.markdown(
            f'<div class="rpt {cls2}">'
            f'<b>結論：{p["verdict"]}</b><br><br>'
            f'近 3 日型態：{r_names}<br>'
            f'看多積分：<b>{p["bull_score"]}</b>&nbsp;&nbsp;|&nbsp;&nbsp;'
            f'看空積分：<b>{p["bear_score"]}</b>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # Orchestrator cross-validation
        st.markdown('<div class="sec-title">主控 Agent：策略交叉驗證</div>',
                    unsafe_allow_html=True)
        cls3 = banner_cls_map[orch["sig_class"]].replace("sig-", "rpt-").replace(
            "entry", "bull").replace("exit", "bear").replace("watch", "neu")
        reasons_html = "".join(f"<div style='margin:3px 0;'>• {r}</div>" for r in orch["reasons"])
        st.markdown(f'<div class="rpt {cls3}">{reasons_html}</div>', unsafe_allow_html=True)

        # Final recommendation
        st.markdown('<div class="sec-title">最終操作建議</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="rpt {cls3}" style="font-size:21px;line-height:1.9;">'
            f'{orch["recommendation"]}'
            f'</div>',
            unsafe_allow_html=True,
        )

        # Directional bias
        st.markdown('<div class="sec-title">多空方向導向</div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        trend = ind["trend"]
        sb_cls  = "v-bull" if trend == "bull" else "v-bear" if trend == "bear" else "v-neu"
        sb_text = "看多" if trend == "bull" else "看空" if trend == "bear" else "盤整"
        lb_cls  = ("v-bull" if ind["ma200"] and last > ind["ma200"]
                   else "v-bear" if ind["ma200"] else "v-neu")
        lb_text = ("長多" if ind["ma200"] and last > ind["ma200"]
                   else "長空" if ind["ma200"] else "資料不足")
        with c1:
            st.markdown("**短期 (均線+型態)**")
            st.markdown(f'<div style="font-size:36px;font-weight:700;" class="{sb_cls}">{sb_text}</div>',
                        unsafe_allow_html=True)
        with c2:
            st.markdown("**長期 (MA200)**")
            st.markdown(f'<div style="font-size:36px;font-weight:700;" class="{lb_cls}">{lb_text}</div>',
                        unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# SHARED: strategy report (reused by watchlist tabs)
# ══════════════════════════════════════════════════════════════════════════════

def render_strategy_report(ticker: str, held: bool) -> None:
    """Render 策略交叉驗證報告 inline for a single ticker."""
    with st.spinner(f"分析 {ticker}..."):
        df = fetch_ohlcv(ticker, "180d")
    if df is None or len(df) < 20:
        st.error(f"無法取得 **{ticker}** 的歷史資料。")
        return

    ind               = compute_indicators(df)
    patterns          = detect_patterns(df, lookback=10)
    q                 = quant_agent_report(ind)
    p                 = pattern_agent_report(patterns)
    short_r, mid_r, long_r = quant_timeframe_reports(ind, q)
    combined          = short_r["score"] * 0.25 + mid_r["score"] * 0.50 + long_r["score"] * 0.25
    orch              = run_orchestrator(held, ind, q, p, combined_score=combined)
    last              = ind["last"]

    banner_cls_map = {"entry": "sig-entry", "exit": "sig-exit", "watch": "sig-watch"}
    b_cls    = banner_cls_map[orch["sig_class"]]
    held_str = "（持有中）" if held else "（未持有）"
    st.markdown(
        f'<div class="sig-banner {b_cls}">{orch["signal"]}&nbsp;&nbsp;{held_str}</div>',
        unsafe_allow_html=True,
    )

    st.plotly_chart(_build_level_chart(orch, last, df=df, ind=ind),
                    use_container_width=True, key=f"sr_level_{ticker}")

    st.markdown('<div class="sec-title">Agent 1：量化指標官</div>', unsafe_allow_html=True)
    cls1  = "rpt-bull" if q["score"] > 0 else "rpt-bear" if q["score"] < 0 else "rpt-neu"
    v_cls = ("v-strong-bull" if q["score"] >= 3 else "v-bull" if q["score"] >= 1
             else "v-strong-bear" if q["score"] <= -3 else "v-bear" if q["score"] <= -1 else "v-neu")
    bul   = "".join(f"<div style='margin:2px 0;'>{b}</div>" for b in q["bullets"])
    st.markdown(
        f'<div class="rpt {cls1}"><b>結論：<span class="{v_cls}">{q["verdict"]}</span></b><br><br>{bul}</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="sec-title">Agent 2：K 線型態大師</div>', unsafe_allow_html=True)
    cls2    = ("rpt-bull" if p["bull_score"] > p["bear_score"]
               else "rpt-bear" if p["bear_score"] > p["bull_score"] else "rpt-neu")
    r_names = "、".join(pt["name"].split("(")[0].strip() for pt in p["recent"]) or "近期無顯著型態"
    st.markdown(
        f'<div class="rpt {cls2}">'
        f'<b>結論：{p["verdict"]}</b><br><br>'
        f'近 3 日型態：{r_names}<br>'
        f'看多積分：<b>{p["bull_score"]}</b>&nbsp;&nbsp;|&nbsp;&nbsp;'
        f'看空積分：<b>{p["bear_score"]}</b>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="sec-title">主控 Agent：策略交叉驗證</div>', unsafe_allow_html=True)
    cls3 = banner_cls_map[orch["sig_class"]].replace("sig-", "rpt-").replace(
        "entry", "bull").replace("exit", "bear").replace("watch", "neu")
    reasons_html = "".join(f"<div style='margin:3px 0;'>• {r}</div>" for r in orch["reasons"])
    st.markdown(f'<div class="rpt {cls3}">{reasons_html}</div>', unsafe_allow_html=True)

    st.markdown('<div class="sec-title">最終操作建議</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="rpt {cls3}" style="font-size:21px;line-height:1.9;">'
        f'{orch["recommendation"]}'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="sec-title">多空方向導向</div>', unsafe_allow_html=True)
    c1, c2  = st.columns(2)
    trend   = ind["trend"]
    sb_cls  = "v-bull" if trend == "bull" else "v-bear" if trend == "bear" else "v-neu"
    sb_text = "看多" if trend == "bull" else "看空" if trend == "bear" else "盤整"
    lb_cls  = ("v-bull" if ind["ma200"] and last > ind["ma200"]
               else "v-bear" if ind["ma200"] else "v-neu")
    lb_text = ("長多" if ind["ma200"] and last > ind["ma200"]
               else "長空" if ind["ma200"] else "資料不足")
    with c1:
        st.markdown("**短期 (均線+型態)**")
        st.markdown(f'<div style="font-size:36px;font-weight:700;" class="{sb_cls}">{sb_text}</div>',
                    unsafe_allow_html=True)
    with c2:
        st.markdown("**長期 (MA200)**")
        st.markdown(f'<div style="font-size:36px;font-weight:700;" class="{lb_cls}">{lb_text}</div>',
                    unsafe_allow_html=True)
