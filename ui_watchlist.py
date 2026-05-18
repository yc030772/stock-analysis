from __future__ import annotations

import streamlit as st

from agents import quick_signal
from data import fetch_stock_name
from db import save_db, save_groups, lookup_name


# ── Colour helpers ─────────────────────────────────────────────────────────────

_VERDICT_COLOR = {
    "強烈看多":     "#3fb950",
    "偏多":         "#85d498",
    "盤整觀望":     "#8b949e",
    "偏空":         "#f97c77",
    "強烈看空":     "#f85149",
    "看多型態主導": "#3fb950",
    "看空型態主導": "#f85149",
    "多空型態交錯": "#e3b341",
    "無明顯型態":   "#8b949e",
}


def _v(text: str) -> str:
    color = _VERDICT_COLOR.get(text, "#8b949e")
    return f'<span style="color:{color};font-weight:600">{text}</span>'


def _pct_html(pct: float | None) -> str:
    if pct is None:
        return '<span style="color:#8b949e">—</span>'
    color = "#f85149" if pct > 0 else "#3fb950" if pct < 0 else "#8b949e"
    return f'<span style="color:{color}">{pct:+.2f}%</span>'


def _target_cell(price: float | None, last: float | None) -> str:
    if price is None or last is None:
        return "—"
    pct = (price - last) / last * 100
    col = "#3fb950" if pct > 0 else "#f85149" if pct < 0 else "#8b949e"
    return (f"<span style='font-weight:700'>{price:.2f}</span>"
            f"<span style='color:{col};font-size:11px;margin-left:4px'>{pct:+.1f}%</span>")


# ── Layout ─────────────────────────────────────────────────────────────────────

_COL_SPEC = [3.5, 2.5, 2, 3, 3, 2, 2, 2, 3, 0.8]
_HEADERS  = ["名稱", "代號", "現價", "短期目標價", "長期目標價",
             "短期技術", "中期技術", "長期技術", "K 線型態", ""]

_TH = ('font-size:10px;font-weight:600;color:var(--muted);text-transform:uppercase;'
       'letter-spacing:.6px;padding:6px 0 8px;border-bottom:2px solid var(--bdr);'
       'white-space:nowrap;')
_TD = ('font-size:13px;border-bottom:1px solid var(--bdr);'
       'height:46px;padding:0 4px;'
       'display:flex;flex-direction:column;justify-content:center;overflow:hidden;')


# ── DB helpers ─────────────────────────────────────────────────────────────────

def _do_delete(
    stock_id: str,
    display_stocks: list[dict],
    group: dict | None,
    groups: list[dict] | None,
) -> None:
    if group is not None:
        group["stocks"] = [sid for sid in group["stocks"] if sid != stock_id]
        save_groups(groups)
    else:
        save_db([s for s in display_stocks if s["stock_id"] != stock_id])
        st.cache_data.clear()


def _do_add(
    ticker: str,
    display_stocks: list[dict],
    main_stocks: list[dict] | None,
    group: dict | None,
    groups: list[dict] | None,
) -> None:
    effective_main = main_stocks if main_stocks is not None else display_stocks
    if ticker not in {s["stock_id"] for s in effective_main}:
        name = lookup_name(ticker) or fetch_stock_name(ticker)
        effective_main.append({"stock_id": ticker, "stock_name": name, "holding_status": False})
        save_db(effective_main)
        st.cache_data.clear()
    if group is not None and ticker not in group["stocks"]:
        group["stocks"].append(ticker)
        save_groups(groups)


# ── Public API ─────────────────────────────────────────────────────────────────

def render_watchlist_table(
    display_stocks: list[dict],
    tab_key: str,
    title: str = "",
    main_stocks: list[dict] | None = None,
    group: dict | None = None,
    groups: list[dict] | None = None,
) -> None:
    if title:
        st.markdown(f'<div class="sec-title">{title}</div>', unsafe_allow_html=True)

    sel_key = f"{tab_key}_sel"

    # ── Search bar (add ticker) ────────────────────────────────────────────────
    with st.form(key=f"{tab_key}_add_form", clear_on_submit=True):
        fc1, fc2 = st.columns([6, 1])
        with fc1:
            new_id = st.text_input(
                "新增股票",
                placeholder="輸入代號後按 Enter 新增，例如 2330.TW 或 MU",
                label_visibility="collapsed",
            )
        with fc2:
            submitted = st.form_submit_button("＋ 新增", use_container_width=True, type="primary")
        if submitted and new_id.strip():
            _do_add(new_id.strip(), display_stocks, main_stocks, group, groups)
            st.rerun()

    # ── Table (header + rows inside container so CSS scoping works) ────────────
    with st.container():
        # Marker div: CSS in app.py uses :has(.wlt-start) to scope button styles
        st.markdown('<div class="wlt-start"></div>', unsafe_allow_html=True)

        # Header row
        hcols = st.columns(_COL_SPEC)
        for col, h in zip(hcols, _HEADERS):
            col.markdown(f'<div style="{_TH}">{h}</div>', unsafe_allow_html=True)

        if not display_stocks:
            st.markdown(
                f'<div style="{_TD}color:var(--muted);padding-top:12px;">此清單尚無股票。</div>',
                unsafe_allow_html=True,
            )
        else:
            with st.spinner("載入分析資料..."):
                rows_data = [
                    (s, quick_signal(s["stock_id"], s["holding_status"]))
                    for s in display_stocks
                ]

            for i, (s, r) in enumerate(rows_data):
                last     = r["last"]
                is_sel   = st.session_state.get(sel_key) == s["stock_id"]
                sel_bg   = "background:rgba(88,166,255,0.06);" if is_sel else ""
                td_style = f"{_TD}{sel_bg}"

                t1_s  = _target_cell(r.get("target1"), last)
                t2_s  = _target_cell(r.get("target2"), last)
                sv_h  = _v(r.get("short_verdict",   "N/A"))
                mv_h  = _v(r.get("mid_verdict",     "N/A"))
                lv_h  = _v(r.get("long_verdict",    "N/A"))
                pat_h = _v(r.get("pattern_verdict", "無明顯型態"))
                price_s = f"{last:.2f}" if last is not None else "—"
                pct_h   = _pct_html(r.get("pct"))
                held_tag = ' <span class="held-tag">持有</span>' if s["holding_status"] else ""

                cols = st.columns(_COL_SPEC)
                with cols[0]:
                    label = f"▸ {s['stock_name']}" if is_sel else s["stock_name"]
                    if st.button(label, key=f"{tab_key}_row_{i}", use_container_width=True):
                        st.session_state[sel_key] = None if is_sel else s["stock_id"]
                        st.rerun()

                for col, html in zip(cols[1:9], [
                    f'<div style="{td_style}color:var(--muted);">{s["stock_id"]}{held_tag}</div>',
                    f'<div style="{td_style}"><b>{price_s}</b><span style="font-size:11px;margin-left:4px">{pct_h}</span></div>',
                    f'<div style="{td_style}">{t1_s}</div>',
                    f'<div style="{td_style}">{t2_s}</div>',
                    f'<div style="{td_style}">{sv_h}</div>',
                    f'<div style="{td_style}">{mv_h}</div>',
                    f'<div style="{td_style}">{lv_h}</div>',
                    f'<div style="{td_style}">{pat_h}</div>',
                ]):
                    col.markdown(html, unsafe_allow_html=True)

                with cols[9]:
                    if st.button("✕", key=f"{tab_key}_del_{i}", use_container_width=True):
                        if st.session_state.get(sel_key) == s["stock_id"]:
                            st.session_state.pop(sel_key, None)
                        _do_delete(s["stock_id"], display_stocks, group, groups)
                        st.rerun()

    # ── Strategy report ───────────────────────────────────────────────────────
    selected = st.session_state.get(sel_key)
    if selected:
        info = next((s for s in display_stocks if s["stock_id"] == selected), None)
        if info:
            st.markdown("---")
            hdr_c, close_c = st.columns([9, 1])
            with hdr_c:
                st.markdown(
                    f'<div class="sec-title">策略交叉驗證報告 — '
                    f'{info["stock_name"]} ({selected})</div>',
                    unsafe_allow_html=True,
                )
            with close_c:
                if st.button("關閉", key=f"{tab_key}_close"):
                    st.session_state.pop(sel_key, None)
                    st.rerun()
            from ui_analysis import render_strategy_report
            render_strategy_report(selected, info["holding_status"])


def render_group_tab(
    all_stocks: list[dict],
    group_idx: int,
    groups: list[dict],
) -> None:
    group = groups[group_idx]

    with st.expander("設定群組", expanded=not bool(group["stocks"])):
        new_name = st.text_input(
            "群組名稱", value=group["name"],
            key=f"gname_{group_idx}",
        )
        if new_name.strip() and new_name.strip() != group["name"]:
            groups[group_idx]["name"] = new_name.strip()
            save_groups(groups)
            st.rerun()

        st.markdown("**選擇加入此群組的股票：**")
        changed = False
        n_cols  = min(len(all_stocks), 4) or 1
        cols    = st.columns(n_cols)
        for j, s in enumerate(all_stocks):
            with cols[j % n_cols]:
                in_group = s["stock_id"] in group["stocks"]
                checked  = st.checkbox(
                    f"{s['stock_name']} ({s['stock_id']})",
                    value=in_group,
                    key=f"g{group_idx}_s{j}",
                )
                if checked != in_group:
                    if checked:
                        group["stocks"].append(s["stock_id"])
                    else:
                        group["stocks"].remove(s["stock_id"])
                    changed = True
        if changed:
            save_groups(groups)

    group_stocks = [s for s in all_stocks if s["stock_id"] in group["stocks"]]
    render_watchlist_table(
        display_stocks=group_stocks,
        tab_key=f"g{group_idx}",
        title=group["name"],
        main_stocks=all_stocks,
        group=group,
        groups=groups,
    )
