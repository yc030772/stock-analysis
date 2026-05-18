from __future__ import annotations

import streamlit as st

from agents import quick_signal
from data import fetch_stock_name
from db import save_db, save_groups, lookup_name


# ── Value formatters ────────────────────────────────────────────────────────────

def _arrow_cls(pct: float | None) -> tuple[str, str]:
    if pct is None:  return ("—", "neu")
    if pct > 0:      return ("▲", "pos")
    if pct < 0:      return ("▼", "neg")
    return ("–", "neu")


def _fmt_price(v: float | None) -> str:
    return f"{v:,.2f}" if v is not None else "—"


def _fmt_abs(last: float | None, pct: float | None) -> str:
    if last is None or pct is None:
        return '<span class="neu">—</span>'
    chg = last * pct / 100
    arrow, cls = _arrow_cls(pct)
    return f'<span class="{cls}">{arrow}&thinsp;{abs(chg):.2f}</span>'


def _fmt_pct(pct: float | None) -> str:
    if pct is None:
        return '<span class="neu">—</span>'
    arrow, cls = _arrow_cls(pct)
    return f'<span class="{cls}">{arrow}&thinsp;{abs(pct):.2f}%</span>'


_SIG_LABEL = {"entry": "入場", "exit": "出場", "watch": "觀察"}
_SIG_CLASS = {"entry": "pos",  "exit": "neg",  "watch": "neu"}


def _fmt_sig(r: dict) -> str:
    sc = r.get("sig_class", "watch")
    return (f'<span class="{_SIG_CLASS[sc]}" style="font-weight:700">'
            f'{_SIG_LABEL[sc]}</span>')


# ── Cell style constants ────────────────────────────────────────────────────────

_TH_L = (
    'font-size:11px;font-weight:600;color:var(--muted);'
    'text-transform:uppercase;letter-spacing:.5px;'
    'padding:10px 10px;border-bottom:2px solid var(--bdr);'
    'white-space:nowrap;background:var(--surf);text-align:left;'
)
_TH_R = _TH_L.replace('text-align:left;', 'text-align:right;')

_TD   = (
    'font-size:13px;border-bottom:1px solid var(--bdr);'
    'height:46px;padding:0 10px;display:flex;align-items:center;'
    'overflow:hidden;background:var(--surf);'
)
_TD_R   = _TD + 'justify-content:flex-end;'
_TD_SEL = _TD + 'justify-content:flex-end;background:rgba(13,110,253,.04);'


# ── DB helpers ──────────────────────────────────────────────────────────────────

def _do_delete(stock_id, display_stocks, group, groups):
    if group is not None:
        group["stocks"] = [s for s in group["stocks"] if s != stock_id]
        save_groups(groups)
    else:
        save_db([s for s in display_stocks if s["stock_id"] != stock_id])
        st.cache_data.clear()


def _do_add(ticker, display_stocks, main_stocks, group, groups):
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
    view_key = f"{tab_key}_view"

    edit_mode = st.session_state.get(edit_key, False)
    card_view = st.session_state.get(view_key, False)

    # ── Control bar ────────────────────────────────────────────────────────────
    ctrl_l, ctrl_r = st.columns([7, 1])
    with ctrl_l:
        if title:
            st.markdown(
                f'<div class="sec-title" style="margin-bottom:0;">{title}</div>',
                unsafe_allow_html=True,
            )
    with ctrl_r:
        ic1, ic2 = st.columns(2)
        with ic1:
            if st.button(
                "≡" if card_view else "⊞",
                key=f"{tab_key}_layout",
                help="切換卡片 / 表格",
                use_container_width=True,
            ):
                st.session_state[view_key] = not card_view
                st.rerun()
        with ic2:
            if st.button(
                "✓" if edit_mode else "✏",
                key=f"{tab_key}_edit_btn",
                help="完成" if edit_mode else "編輯清單",
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
                placeholder="輸入代號，例如 2330.TW",
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

    # ── Render ─────────────────────────────────────────────────────────────────
    if card_view:
        _render_cards(rows_data, tab_key, edit_mode, display_stocks, group, groups)
    else:
        _render_table(rows_data, tab_key, edit_mode, display_stocks, group, groups)

    # ── Strategy report ────────────────────────────────────────────────────────
    selected = st.session_state.get(sel_key)
    if selected:
        info = next((s for s in display_stocks if s["stock_id"] == selected), None)
        if info:
            st.markdown("---")
            rh, rc = st.columns([9, 1])
            with rh:
                st.markdown(
                    f'<div class="sec-title">策略報告 — '
                    f'{info["stock_name"]} ({selected})</div>',
                    unsafe_allow_html=True,
                )
            with rc:
                if st.button("✕ 關閉", key=f"{tab_key}_close"):
                    st.session_state.pop(sel_key, None)
                    st.rerun()
            from ui_analysis import render_strategy_report
            render_strategy_report(selected, info["holding_status"])


# ── Table view ──────────────────────────────────────────────────────────────────

def _render_table(rows_data, tab_key, edit_mode, display_stocks, group, groups):
    sel_key  = f"{tab_key}_sel"
    col_spec = [3, 2, 2, 2, 2, 0.6] if edit_mode else [3, 2, 2, 2, 2]
    headers  = ["名稱", "現價", "漲跌", "漲跌%", "訊號"]
    if edit_mode:
        headers.append("")

    marker = "wlt2-start wlt2-edit" if edit_mode else "wlt2-start"

    with st.container():
        st.markdown(f'<div class="{marker}"></div>', unsafe_allow_html=True)

        hcols = st.columns(col_spec)
        for i, (col, h) in enumerate(zip(hcols, headers)):
            col.markdown(
                f'<div style="{_TH_L if i == 0 else _TH_R}">{h}</div>',
                unsafe_allow_html=True,
            )

        for i, (s, r) in enumerate(rows_data):
            is_sel = st.session_state.get(sel_key) == s["stock_id"]
            last   = r.get("last")
            pct    = r.get("pct")
            td_r   = _TD_SEL if is_sel else _TD_R

            rcols = st.columns(col_spec)

            with rcols[0]:
                label = f"▸ {s['stock_name']}" if is_sel else s["stock_name"]
                if st.button(label, key=f"{tab_key}_r{i}", use_container_width=True):
                    st.session_state[sel_key] = None if is_sel else s["stock_id"]
                    st.rerun()

            rcols[1].markdown(
                f'<div style="{td_r}"><b>{_fmt_price(last)}</b></div>',
                unsafe_allow_html=True,
            )
            rcols[2].markdown(
                f'<div style="{td_r}">{_fmt_abs(last, pct)}</div>',
                unsafe_allow_html=True,
            )
            rcols[3].markdown(
                f'<div style="{td_r}">{_fmt_pct(pct)}</div>',
                unsafe_allow_html=True,
            )
            rcols[4].markdown(
                f'<div style="{td_r}">{_fmt_sig(r)}</div>',
                unsafe_allow_html=True,
            )

            if edit_mode:
                with rcols[5]:
                    if st.button("✕", key=f"{tab_key}_d{i}", use_container_width=True):
                        if st.session_state.get(sel_key) == s["stock_id"]:
                            st.session_state.pop(sel_key, None)
                        _do_delete(s["stock_id"], display_stocks, group, groups)
                        st.rerun()


# ── Card view ───────────────────────────────────────────────────────────────────

def _render_cards(rows_data, tab_key, edit_mode, display_stocks, group, groups):
    sel_key = f"{tab_key}_sel"
    n_cols  = min(len(rows_data), 3) or 1
    cols    = st.columns(n_cols)

    for i, (s, r) in enumerate(rows_data):
        is_sel     = st.session_state.get(sel_key) == s["stock_id"]
        last       = r.get("last")
        pct        = r.get("pct")
        sc         = r.get("sig_class", "watch")
        arrow, cls = _arrow_cls(pct)
        pct_str    = f"{arrow}&thinsp;{abs(pct):.2f}%" if pct is not None else "—"
        held_dot   = "&nbsp;·&nbsp;持有" if s["holding_status"] else ""

        with cols[i % n_cols]:
            sel_cls = " wl-card2-sel" if is_sel else ""
            st.markdown(
                f'<div class="wl-card2{sel_cls}">'
                f'<div class="wl-card2-name">{s["stock_name"]}</div>'
                f'<div class="wl-card2-id">{s["stock_id"]}{held_dot}</div>'
                f'<div class="wl-card2-price">{_fmt_price(last)}</div>'
                f'<div class="wl-card2-pct"><span class="{cls}">{pct_str}</span></div>'
                f'<div class="wl-card2-sig">'
                f'<span class="{_SIG_CLASS[sc]}">{_SIG_LABEL[sc]}</span>'
                f'</div></div>',
                unsafe_allow_html=True,
            )
            if st.button(
                "▸ 收起" if is_sel else "詳細",
                key=f"{tab_key}_c{i}",
                use_container_width=True,
            ):
                st.session_state[sel_key] = None if is_sel else s["stock_id"]
                st.rerun()
            if edit_mode:
                if st.button("刪除", key=f"{tab_key}_cd{i}", use_container_width=True):
                    if st.session_state.get(sel_key) == s["stock_id"]:
                        st.session_state.pop(sel_key, None)
                    _do_delete(s["stock_id"], display_stocks, group, groups)
                    st.rerun()


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
