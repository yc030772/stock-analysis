from __future__ import annotations

import streamlit as st

from db import save_db
from data import fetch_stock_name
from agents import quick_signal


# ══════════════════════════════════════════════════════════════════════════════
# UI — SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════

def render_sidebar(stocks: list[dict]) -> None:
    with st.sidebar:
        st.markdown(
            '<div style="font-size:17px;font-weight:700;padding:10px 0 6px;'
            'border-bottom:1px solid var(--bdr);margin-bottom:10px;">追蹤名單</div>',
            unsafe_allow_html=True,
        )

        # Signal counts
        counts   = {"entry": 0, "exit": 0, "watch": 0}
        sigs: dict[str, dict] = {}
        with st.spinner("載入訊號..."):
            for s in stocks:
                sig = quick_signal(s["stock_id"], s["holding_status"])
                sigs[s["stock_id"]] = sig
                counts[sig["sig_class"]] += 1

        st.markdown(
            f'<div style="display:flex;gap:5px;margin:0 0 12px;">'
            f'<span class="sbadge sb-entry"><span style="color:#3fb950">●</span> {counts["entry"]}</span>'
            f'<span class="sbadge sb-exit"><span style="color:#f85149">●</span> {counts["exit"]}</span>'
            f'<span class="sbadge sb-watch"><span style="color:#8b949e">●</span> {counts["watch"]}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # Stock list — one row per stock: colored dot + name button
        selected = st.session_state.get("selected_stock",
                                        stocks[0]["stock_id"] if stocks else "")
        for i, s in enumerate(stocks):
            tid  = s["stock_id"]
            name = s["stock_name"]
            sc   = sigs[tid]["sig_class"]

            dot_color = "#3fb950" if sc == "entry" else "#f85149" if sc == "exit" else "#8b949e"
            is_active = tid == selected
            dot_glyph = "◉" if is_active else "●"

            cc = st.columns([1, 6])
            with cc[0]:
                st.markdown(
                    f'<div style="color:{dot_color};font-size:18px;'
                    f'text-align:center;margin-top:7px;line-height:1;">{dot_glyph}</div>',
                    unsafe_allow_html=True,
                )
            with cc[1]:
                if st.button(name, key=f"sel_{i}", use_container_width=True):
                    st.session_state.selected_stock = tid
                    st.session_state.stock_search   = tid
                    st.session_state["stock_sel"]   = f"{tid} — {name}"
                    st.session_state._nav_step      = 1
                    st.rerun()

        st.markdown('<div class="sec-title" style="margin-top:16px;">管理</div>',
                    unsafe_allow_html=True)

        with st.expander("➕ 新增股票"):
            new_id   = st.text_input("股票代碼", placeholder="2330.TW", key="ni")
            new_name = st.text_input("名稱",     placeholder="台積電",   key="nn")
            new_held = st.checkbox("目前持有", key="nh")
            if st.button("新增", key="btn_add", use_container_width=True):
                if new_id.strip():
                    sid  = new_id.strip()
                    name = new_name.strip() or fetch_stock_name(sid)
                    stocks.append({"stock_id": sid,
                                   "stock_name": name,
                                   "holding_status": new_held})
                    save_db(stocks)
                    st.cache_data.clear()
                    st.rerun()

        with st.expander("🔧 持有狀態 / 刪除"):
            changed = False
            for i, s in enumerate(stocks):
                c1, c2, c3 = st.columns([4, 2, 1])
                c1.caption(f"{s['stock_id'].replace('.TW','')} {s['stock_name']}")
                new_held = c2.checkbox("持有", value=s["holding_status"],
                                       key=f"h_{i}", label_visibility="collapsed")
                if new_held != s["holding_status"]:
                    stocks[i]["holding_status"] = new_held
                    changed = True
                if c3.button("🗑", key=f"del_{i}"):
                    stocks.pop(i)
                    save_db(stocks)
                    st.cache_data.clear()
                    st.rerun()
            if changed:
                save_db(stocks)

        if st.button("🔄 重新整理訊號", use_container_width=True, key="btn_refresh"):
            st.cache_data.clear()
            st.rerun()
