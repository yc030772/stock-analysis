from __future__ import annotations

import streamlit as st

from agents import quick_signal
from data import fetch_stock_name
from db import save_db, save_groups, lookup_name


# ── Verdict → CSS class mapping ────────────────────────────────────────────────

_VERDICT_CLS = {
    "強烈看多":     "v-strong-bull",
    "偏多":         "v-bull",
    "盤整觀望":     "v-neu",
    "偏空":         "v-bear",
    "強烈看空":     "v-strong-bear",
    "看多型態主導": "v-strong-bull",
    "看空型態主導": "v-strong-bear",
    "多空型態交錯": "v-neu",
    "無明顯型態":   "v-neu",
    "N/A":          "v-neu",
}


def _vcell(text: str) -> str:
    cls = _VERDICT_CLS.get(text, "v-neu")
    return f'<span class="{cls}">{text}</span>'


def _price_target(price: float | None, last: float | None) -> str:
    if price is None or last is None:
        return "—"
    pct = (price - last) / last * 100
    col = "var(--green)" if pct > 0 else "var(--red)" if pct < 0 else "var(--muted)"
    sign = "+" if pct > 0 else ""
    return (f'<b>{price:.2f}</b>'
            f'<span style="color:{col};font-size:10px;margin-left:3px">{sign}{pct:.1f}%</span>')


def _pct_html(pct: float | None) -> str:
    if pct is None:
        return '<span style="color:var(--muted)">—</span>'
    col = "var(--red)" if pct > 0 else "var(--green)" if pct < 0 else "var(--muted)"
    arrow = "▲" if pct > 0 else "▼" if pct < 0 else "–"
    return f'<span style="color:{col}">{arrow} {abs(pct):.2f}%</span>'


# ── HTML table builder ─────────────────────────────────────────────────────────

def _build_table_html(rows_data: list) -> str:
    rows_html = ""
    for s, r in rows_data:
        last = r.get("last")
        price_str = f"{last:.2f}" if last is not None else "—"
        held = (
            ' <span style="font-size:9px;background:var(--blue);color:#fff;'
            'padding:1px 5px;border-radius:3px;vertical-align:middle;'
            'font-weight:600">持有</span>'
            if s["holding_status"] else ""
        )
        rows_html += (
            "<tr>"
            f'<td class="wl-col-name">{s["stock_name"]}{held}</td>'
            f'<td style="color:var(--muted);font-size:12px">{s["stock_id"]}</td>'
            f'<td class="wl-col-num"><b>{price_str}</b>'
            f'<span style="margin-left:4px">{_pct_html(r.get("pct"))}</span></td>'
            f'<td class="wl-col-num">{_price_target(r.get("target1"), last)}</td>'
            f'<td class="wl-col-num">{_price_target(r.get("target2"), last)}</td>'
            f'<td>{_vcell(r.get("short_verdict",   "N/A"))}</td>'
            f'<td>{_vcell(r.get("mid_verdict",     "N/A"))}</td>'
            f'<td>{_vcell(r.get("long_verdict",    "N/A"))}</td>'
            f'<td>{_vcell(r.get("pattern_verdict", "無明顯型態"))}</td>'
            "</tr>"
        )

    return (
        '<div class="wl-pure-tbl-wrap">'
        '<table class="wl-pure-tbl"><thead><tr>'
        '<th class="wl-col-name">名稱</th>'
        '<th>代號</th>'
        '<th class="wl-col-num">現價</th>'
        '<th class="wl-col-num">短期目標價</th>'
        '<th class="wl-col-num">長期目標價</th>'
        '<th>短期技術</th>'
        '<th>中期技術</th>'
        '<th>長期技術</th>'
        '<th>K 線型態</th>'
        '</tr></thead>'
        f'<tbody>{rows_html}</tbody>'
        '</table></div>'
    )


# ── DB helpers ──────────────────────────────────────────────────────────────────

def _do_delete(stock_id: str, display_stocks: list[dict],
               group: dict | None, groups: list[dict] | None) -> None:
    if group is not None:
        group["stocks"] = [s for s in group["stocks"] if s != stock_id]
        save_groups(groups)
    else:
        save_db([s for s in display_stocks if s["stock_id"] != stock_id])
        st.cache_data.clear()


def _do_add(ticker: str, display_stocks: list[dict],
            main_stocks: list[dict] | None,
            group: dict | None, groups: list[dict] | None) -> None:
    effective = main_stocks if main_stocks is not None else display_stocks
    if ticker not in {s["stock_id"] for s in effective}:
        name = lookup_name(ticker) or fetch_stock_name(ticker)
        effective.append({"stock_id": ticker, "stock_name": name, "holding_status": False})
        save_db(effective)
        st.cache_data.clear()
    if group is not None and ticker not in group["stocks"]:
        group["stocks"].append(ticker)
        save_groups(groups)


# ── Public API ──────────────────────────────────────────────────────────────────

def render_watchlist_table(
    display_stocks: list[dict],
    tab_key: str,
    title: str = "",
    main_stocks: list[dict] | None = None,
    group: dict | None = None,
    groups: list[dict] | None = None,
) -> None:

    sel_key  = f"{tab_key}_sel"
    edit_key = f"{tab_key}_edit"
    edit_mode = st.session_state.get(edit_key, False)

    # ── Title bar ──────────────────────────────────────────────────────────────
    tl, tr = st.columns([8, 1])
    with tl:
        if title:
            st.markdown(
                f'<div class="sec-title" style="margin-bottom:0">{title}</div>',
                unsafe_allow_html=True,
            )
    with tr:
        if st.button(
            "✓ 完成" if edit_mode else "✏ 編輯",
            key=f"{tab_key}_edit_btn",
            type="primary" if edit_mode else "secondary",
            use_container_width=True,
        ):
            st.session_state[edit_key] = not edit_mode
            st.rerun()

    # ── Add-ticker form ────────────────────────────────────────────────────────
    with st.form(key=f"{tab_key}_add_form", clear_on_submit=True):
        fa, fb = st.columns([6, 1])
        with fa:
            new_id = st.text_input(
                "新增",
                placeholder="輸入代號，例如 2330.TW 或 AAPL",
                label_visibility="collapsed",
            )
        with fb:
            added = st.form_submit_button("＋ 新增", use_container_width=True, type="primary")
        if added and new_id.strip():
            _do_add(new_id.strip(), display_stocks, main_stocks, group, groups)
            st.rerun()

    # ── Empty state ────────────────────────────────────────────────────────────
    if not display_stocks:
        st.markdown(
            '<div style="color:var(--muted);padding:24px 0;text-align:center;font-size:13px;">'
            '此清單尚無股票</div>',
            unsafe_allow_html=True,
        )
        return

    # ── Load signals ───────────────────────────────────────────────────────────
    with st.spinner("載入訊號…"):
        rows_data = [
            (s, quick_signal(s["stock_id"], s["holding_status"]))
            for s in display_stocks
        ]

    # ── Pure HTML table ────────────────────────────────────────────────────────
    st.markdown(_build_table_html(rows_data), unsafe_allow_html=True)

    # ── Edit mode: delete panel ────────────────────────────────────────────────
    if edit_mode:
        st.markdown(
            '<div style="margin-top:10px;padding:10px 14px;background:var(--surf2);'
            'border:1px solid var(--bdr);border-radius:8px;">'
            '<div style="font-size:11px;font-weight:600;color:var(--muted);'
            'margin-bottom:8px;letter-spacing:.4px">點擊刪除個股</div></div>',
            unsafe_allow_html=True,
        )
        ncols = min(len(display_stocks), 4) or 1
        del_cols = st.columns(ncols)
        for i, s in enumerate(display_stocks):
            with del_cols[i % ncols]:
                if st.button(
                    f"✕  {s['stock_name']}",
                    key=f"{tab_key}_del_{i}",
                    use_container_width=True,
                ):
                    st.session_state.pop(sel_key, None)
                    _do_delete(s["stock_id"], display_stocks, group, groups)
                    st.rerun()

    # ── Strategy report picker ─────────────────────────────────────────────────
    opts = [""] + [s["stock_id"] for s in display_stocks]
    labels = {s["stock_id"]: f"{s['stock_name']} ({s['stock_id']})" for s in display_stocks}
    labels[""] = "— 選擇個股查看策略報告 —"

    prev_sel = st.session_state.get(sel_key, "")
    chosen = st.selectbox(
        "策略報告",
        options=opts,
        format_func=lambda k: labels.get(k, k),
        index=opts.index(prev_sel) if prev_sel in opts else 0,
        key=f"{tab_key}_picker",
        label_visibility="collapsed",
    )
    if chosen != prev_sel:
        st.session_state[sel_key] = chosen
        st.rerun()

    if chosen:
        info = next((s for s in display_stocks if s["stock_id"] == chosen), None)
        if info:
            st.markdown("---")
            rh, rc = st.columns([9, 1])
            with rh:
                st.markdown(
                    f'<div class="sec-title">策略報告 — '
                    f'{info["stock_name"]} ({chosen})</div>',
                    unsafe_allow_html=True,
                )
            with rc:
                if st.button("✕ 關閉", key=f"{tab_key}_close"):
                    st.session_state[sel_key] = ""
                    st.rerun()
            from ui_analysis import render_strategy_report
            render_strategy_report(chosen, info["holding_status"])


# ── Group tab ───────────────────────────────────────────────────────────────────

def render_group_tab(
    all_stocks: list[dict],
    group_idx: int,
    groups: list[dict],
) -> None:
    group = groups[group_idx]

    with st.expander("設定群組", expanded=not bool(group["stocks"])):
        new_name = st.text_input(
            "群組名稱", value=group["name"], key=f"gname_{group_idx}",
        )
        if new_name.strip() and new_name.strip() != group["name"]:
            groups[group_idx]["name"] = new_name.strip()
            save_groups(groups)
            st.rerun()

        st.markdown("**選擇加入此群組的股票：**")
        changed = False
        n_cols  = min(len(all_stocks), 4) or 1
        gcols   = st.columns(n_cols)
        for j, s in enumerate(all_stocks):
            with gcols[j % n_cols]:
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
