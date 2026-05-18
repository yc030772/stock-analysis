from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from db import MOCK_MARKET
from charts import _DARK_LAYOUT


# ══════════════════════════════════════════════════════════════════════════════
# UI — TAB 1: HEATMAP
# ══════════════════════════════════════════════════════════════════════════════

def _pool_tech_note(pct: float) -> str:
    if pct > 4:   return "急漲強勢，短線超買，注意追高風險"
    if pct > 2:   return "放量突破，均線多頭排列，動能強勁"
    if pct > 1:   return "溫和偏多，MACD 柱體轉正，可留意"
    if pct > 0:   return "短線小漲，均線偏多，量能待觀察"
    if pct > -1:  return "短線回測，留意支撐是否有效"
    if pct > -2:  return "均線偏空排列，MACD 柱體偏負"
    if pct > -4:  return "放量下跌，空方動能強，避免接刀"
    return "急跌弱勢，超賣區間，止損為先"


def render_heatmap_tab() -> None:
    st.markdown('<div class="sec-title">Pool Filter 篩選器</div>', unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    f_bull = c1.toggle("看多型態標的", key="f_bull", value=False)
    f_inst = c2.toggle("法人強勢股 (漲>1.5%)", key="f_inst", value=False)
    f_bear = c3.toggle("看空型態標的", key="f_bear", value=False)

    rows = []
    for cat, sec, ticker, name, mcap, pct in MOCK_MARKET:
        if f_bull and pct <= 0:
            continue
        if f_bear and pct >= 0:
            continue
        if f_inst and pct < 1.5:
            continue
        rows.append({
            "類別": cat, "板塊": sec,
            "標籤": f"{name}\n{pct:+.1f}%",
            "市值": mcap, "漲跌": pct,
            "股票": ticker, "名稱": name,
        })

    if not rows:
        st.info("目前篩選條件下無符合標的。")
        return

    df = pd.DataFrame(rows)

    fig = px.treemap(
        df,
        path=["類別", "板塊", "標籤"],
        values="市值",
        color="漲跌",
        # Taiwan: red=up, green=down
        color_continuous_scale=[(0, "#3fb950"), (0.5, "#21262d"), (1, "#f85149")],
        range_color=[-6, 6],
        hover_data={"股票": True, "漲跌": ":.2f%"},
        title="",
    )
    fig.update_traces(
        textinfo="label",
        textfont=dict(size=11),
        hovertemplate="<b>%{label}</b><br>漲跌：%{color:.2f}%<br>市值代理：%{value:.0f} 億",
    )
    fig.update_coloraxes(colorbar=dict(
        title="漲跌%", tickvals=[-6, -3, 0, 3, 6], len=0.4, thickness=12,
    ))
    fig.update_layout(
        **_DARK_LAYOUT,
        height=520,
        margin=dict(l=4, r=4, t=8, b=4),   # overrides _DARK_LAYOUT (no margin key)
    )
    st.plotly_chart(fig, use_container_width=True)

    # Pool filter stock table — shown only when a filter is active
    if f_bull or f_bear or f_inst:
        label = ("看多型態標的" if f_bull else "") or ("看空型態標的" if f_bear else "") or "法人強勢股"
        st.markdown(f'<div class="sec-title">{label} 篩選清單</div>', unsafe_allow_html=True)
        pct_col = []
        for r in rows:
            pct_val = r["漲跌"]
            dot_c   = "#f85149" if pct_val > 0 else "#3fb950" if pct_val < 0 else "#8b949e"
            pct_col.append(f'<span style="color:{dot_c};font-weight:600">{pct_val:+.1f}%</span>')
        pool_df = pd.DataFrame({
            "代碼": [r["股票"] for r in rows],
            "名稱": [r["名稱"] for r in rows],
            "板塊": [r["板塊"] for r in rows],
            "漲跌%": [f"{r['漲跌']:+.1f}%" for r in rows],
            "技術簡析": [_pool_tech_note(r["漲跌"]) for r in rows],
        })
        st.dataframe(pool_df, hide_index=True, use_container_width=True)

    # Sector averages
    st.markdown('<div class="sec-title">板塊強弱排行</div>', unsafe_allow_html=True)
    sec_avg = df.groupby("板塊")["漲跌"].mean().sort_values(ascending=False).round(2)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**強勢板塊 Top 5**")
        st.dataframe(sec_avg.head(5).reset_index().rename(
            columns={"板塊": "板塊", "漲跌": "平均漲幅%"}),
            hide_index=True, use_container_width=True)
    with c2:
        st.markdown("**弱勢板塊 Bottom 5**")
        st.dataframe(sec_avg.tail(5).reset_index().rename(
            columns={"板塊": "板塊", "漲跌": "平均漲幅%"}),
            hide_index=True, use_container_width=True)
