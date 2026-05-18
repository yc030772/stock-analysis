from __future__ import annotations

from datetime import datetime as _dt

import streamlit as st
import streamlit.components.v1 as _components

from db import load_db, save_db, load_groups
from data import fetch_index
from ui_login import render_login_page
from ui_sidebar import render_sidebar
from ui_heatmap import render_heatmap_tab
from ui_analysis import render_analysis_tab
from ui_watchlist import render_watchlist_table, render_group_tab

# ══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="雙Agent 智能監控儀表板",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ══════════════════════════════════════════════════════════════════════════════
# THEME
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
:root {
  --bg:     #f8f9fa;
  --surf:   #ffffff;
  --surf2:  #f1f3f5;
  --bdr:    #dee2e6;
  --txt:    #212529;
  --muted:  #6c757d;
  --green:  #198754;
  --red:    #dc3545;
  --blue:   #0d6efd;
  --yellow: #d97706;
  --purple: #7c3aed;
  --orange: #f97316;
  --r:      10px;
}
html[data-theme="dark"] {
  --bg:     #0d1117;
  --surf:   #161b22;
  --surf2:  #21262d;
  --bdr:    #30363d;
  --txt:    #c9d1d9;
  --muted:  #8b949e;
  --green:  #3fb950;
  --red:    #f85149;
  --blue:   #58a6ff;
  --yellow: #e3b341;
  --purple: #bc8cff;
  --orange: #f0883e;
}

/* ── base ── */
body, .stApp { background: var(--bg) !important; color: var(--txt); }
.block-container { padding: 1.2rem 2rem 1rem !important; max-width: 100% !important; }
* { box-sizing: border-box; }

/* ── sidebar ── */
section[data-testid="stSidebar"] > div:first-child {
  background: var(--surf) !important;
  border-right: 1px solid var(--bdr);
}
section[data-testid="stSidebar"] { width: 260px !important; }
section[data-testid="stSidebar"] .block-container { padding: 1rem !important; }

/* ── tabs ── */
.stTabs [data-baseweb="tab-list"] {
  background: var(--surf2);
  border-radius: var(--r);
  padding: 4px; gap: 3px;
  border: 1px solid var(--bdr);
}
.stTabs [data-baseweb="tab"] {
  border-radius: 7px;
  color: var(--muted);
  padding: 8px 22px;
  font-size: 13px; font-weight: 500;
}
.stTabs [aria-selected="true"] {
  background: var(--blue) !important;
  color: #fff !important;
}

/* ── stock card ── */
.scard {
  background: var(--surf2);
  border: 1px solid var(--bdr);
  border-radius: var(--r);
  padding: 9px 12px;
  margin-bottom: 3px;
}
.scard.active { border-color: var(--blue); background: var(--surf2); }
.scard-row1 { display: flex; justify-content: space-between; align-items: center; }
.scard-id   { font-size: 14px; font-weight: 700; color: var(--txt); }
.scard-sig  { font-size: 14px; }
.scard-name { font-size: 11px; color: var(--muted); margin-top: 1px; }
.scard-row2 { display: flex; justify-content: space-between; margin-top: 4px; font-size: 11px; }
.held-tag   { background: rgba(13,110,253,.1); color: var(--blue);
              border: 1px solid rgba(13,110,253,.25); border-radius: 4px;
              padding: 0px 6px; font-size: 10px; }

/* ── kpi grid ── */
.kgrid { display: grid; grid-template-columns: repeat(auto-fill, minmax(130px,1fr)); gap: 8px; margin: 10px 0; }
.kbox  { background: var(--surf); border: 1px solid var(--bdr); border-radius: var(--r);
         padding: 12px; text-align: center; }
.klabel { font-size: 10px; color: var(--muted); text-transform: uppercase; letter-spacing: .5px; }
.kval   { font-size: 20px; font-weight: 700; color: var(--txt); line-height: 1.3; margin-top: 3px; }
.kdelta { font-size: 11px; margin-top: 2px; }

/* ── Taiwan convention: red = up, green = down ── */
.pos { color: var(--red); }
.neg { color: var(--green); }
.neu { color: var(--muted); }

/* ── signal banner ── */
.sig-banner { border-radius: var(--r); padding: 14px 24px; margin: 12px 0;
              font-size: 17px; font-weight: 700; text-align: center; }
.sig-entry  { background: rgba(63,185,80,.1);  border: 1.5px solid var(--green); color: var(--green); }
.sig-exit   { background: rgba(248,81,73,.1);  border: 1.5px solid var(--red);   color: var(--red); }
.sig-watch  { background: rgba(139,148,158,.07); border: 1.5px solid var(--bdr); color: var(--muted); }

/* ── pattern pill ── */
.pp      { display:inline-block; border-radius:5px; padding:3px 9px;
           font-size:11px; font-weight:600; margin:3px 2px; }
.pp-bull { background:rgba(63,185,80,.12); color:var(--green); border:1px solid rgba(63,185,80,.3); }
.pp-bear { background:rgba(248,81,73,.12); color:var(--red);   border:1px solid rgba(248,81,73,.3); }

/* ── section title ── */
.sec-title { font-size:11px; font-weight:600; color:var(--muted); text-transform:uppercase;
             letter-spacing:1px; margin:18px 0 8px; border-bottom:1px solid var(--bdr); padding-bottom:5px; }

/* ── report card ── */
.rpt      { background:var(--surf); border:1px solid var(--bdr); border-radius:var(--r);
            padding:14px 18px; margin:8px 0; font-size:13px; line-height:1.7; color:var(--txt); }
.rpt-bull { border-left: 4px solid var(--green); }
.rpt-bear { border-left: 4px solid var(--red); }
.rpt-neu  { border-left: 4px solid var(--muted); }

/* ── level box ── */
.lvl-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:8px; margin:12px 0; }
.lvl { background:var(--surf2); border:1px solid var(--bdr); border-radius:8px;
       padding:10px; text-align:center; }
.lvl-label { font-size:10px; color:var(--muted); text-transform:uppercase; letter-spacing:.5px; }
.lvl-val   { font-size:18px; font-weight:700; margin-top:4px; color:var(--txt); }

/* ── header strip ── */
.hdr { display:flex; align-items:center; gap:20px; padding:8px 0 14px;
       border-bottom:1px solid var(--bdr); margin-bottom:14px; flex-wrap:wrap; }
.hdr-title { font-size:18px; font-weight:700; color:var(--txt); }
.hdr-idx   { font-size:12px; color:var(--muted); }
.hdr-val   { font-size:14px; font-weight:600; color:var(--txt); }

/* ── summary badges (sidebar) ── */
.sbadge { display:inline-flex; align-items:center; gap:4px;
          border-radius:6px; padding:4px 10px; font-size:12px; font-weight:600; margin:2px; }
.sb-entry { background:rgba(63,185,80,.15); color:var(--green); }
.sb-exit  { background:rgba(248,81,73,.15); color:var(--red); }
.sb-watch { background:rgba(139,148,158,.1); color:var(--muted); }

/* ── hide streamlit chrome, collapse header space ── */
#MainMenu, footer { visibility: hidden; }
header[data-testid="stHeader"] { height: 0 !important; min-height: 0 !important; overflow: hidden; }
div[data-testid="stToolbar"] { display: none; }
div[data-testid="stDecoration"] { display: none; }

/* stSidebarCollapsedControl is unreliable — handled by JS instead */

/* ── verdict color scale ── */
.v-strong-bull { color: var(--green); font-weight: 700; }
.v-bull        { color: var(--green); font-weight: 600; opacity: 0.8; }
.v-neu         { color: var(--muted); font-weight: 500; }
.v-bear        { color: var(--red);   font-weight: 600; opacity: 0.8; }
.v-strong-bear { color: var(--red);   font-weight: 700; }

/* ── watchlist panel ── */
.wl-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(180px,1fr)); gap:10px; margin:10px 0 20px; }
.wl-card { background:var(--surf2); border:1px solid var(--bdr); border-radius:10px; padding:12px 14px; }
.wl-card-name { font-size:13px; font-weight:700; color:var(--txt); }
.wl-card-id   { font-size:10px; color:var(--muted); margin-top:1px; }
.wl-card-price{ font-size:20px; font-weight:700; margin-top:6px; color:var(--txt); }
.wl-card-pct  { font-size:12px; margin-top:2px; }
.wl-card-sig  { font-size:11px; font-weight:600; margin-top:6px; }

/* ── watchlist faux table ─────────────────────────────────────────────────── */
/* :has(.wlt-start) scopes all rules below to the table container only         */

/* name column: strip button chrome → plain bold text                          */
[data-testid="stVerticalBlock"]:has(.wlt-start)
  [data-testid="stColumn"]:first-child .stButton > button {
  background:    transparent !important;
  border:        none !important;
  border-bottom: 1px solid var(--bdr) !important;
  border-radius: 0 !important;
  color:         var(--txt) !important;
  font-weight:   700 !important;
  font-size:     13px !important;
  text-align:    left !important;
  padding:       0 4px !important;
  margin:        0 !important;
  height:        46px !important;
  width:         100% !important;
}
[data-testid="stVerticalBlock"]:has(.wlt-start)
  [data-testid="stColumn"]:first-child .stButton > button:hover {
  color:      var(--blue) !important;
  background: rgba(88,166,255,0.04) !important;
}

/* delete column: minimal ✕ icon                                               */
[data-testid="stVerticalBlock"]:has(.wlt-start)
  [data-testid="stColumn"]:last-child .stButton > button[kind="secondary"] {
  background:    transparent !important;
  border:        none !important;
  border-bottom: 1px solid var(--bdr) !important;
  border-radius: 0 !important;
  color:         var(--muted) !important;
  font-size:     12px !important;
  padding:       0 2px !important;
  margin:        0 !important;
  height:        46px !important;
  width:         100% !important;
}
[data-testid="stVerticalBlock"]:has(.wlt-start)
  [data-testid="stColumn"]:last-child .stButton > button[kind="secondary"]:hover {
  color:      var(--red) !important;
  background: transparent !important;
}

/* reduce row gap between st.columns groups → table-row feel                  */
[data-testid="stVerticalBlock"]:has(.wlt-start)
  > div > [data-testid="stHorizontalBlock"] {
  margin-bottom: -6px !important;
  gap:           4px !important;
}

/* ── watchlist v2: scrollable table with sticky name column ─────────────── */
[data-testid="stVerticalBlock"]:has(.wlt2-start) {
  overflow-x: auto !important;
  -webkit-overflow-scrolling: touch;
  border: 1px solid var(--bdr);
  border-radius: 10px;
  margin: 4px 0 16px;
}
[data-testid="stVerticalBlock"]:has(.wlt2-start)
  > div > [data-testid="stHorizontalBlock"] {
  min-width: 520px;
  flex-wrap: nowrap !important;
  gap: 0 !important;
  margin-bottom: 0 !important;
}
[data-testid="stVerticalBlock"]:has(.wlt2-start)
  > div > [data-testid="stHorizontalBlock"]
  > [data-testid="stColumn"]:first-child {
  position: sticky;
  left: 0;
  z-index: 4;
  background: var(--surf);
  box-shadow: 2px 0 6px rgba(0,0,0,.06);
}
/* name button */
[data-testid="stVerticalBlock"]:has(.wlt2-start)
  [data-testid="stColumn"]:first-child .stButton > button {
  background: transparent !important;
  border: none !important;
  border-bottom: 1px solid var(--bdr) !important;
  border-radius: 0 !important;
  color: var(--txt) !important;
  font-weight: 700 !important;
  font-size: 13px !important;
  text-align: left !important;
  padding: 0 10px !important;
  height: 46px !important;
  width: 100% !important;
  margin: 0 !important;
}
[data-testid="stVerticalBlock"]:has(.wlt2-start)
  [data-testid="stColumn"]:first-child .stButton > button:hover {
  color: var(--blue) !important;
  background: rgba(13,110,253,.04) !important;
}
/* delete button (only rendered in edit mode, always last col) */
[data-testid="stVerticalBlock"]:has(.wlt2-edit)
  [data-testid="stColumn"]:last-child .stButton > button {
  background: transparent !important;
  border: none !important;
  border-bottom: 1px solid var(--bdr) !important;
  border-radius: 0 !important;
  color: var(--muted) !important;
  font-size: 14px !important;
  padding: 0 !important;
  height: 46px !important;
  width: 100% !important;
  margin: 0 !important;
}
[data-testid="stVerticalBlock"]:has(.wlt2-edit)
  [data-testid="stColumn"]:last-child .stButton > button:hover {
  color: var(--red) !important;
  background: rgba(220,53,69,.05) !important;
}
/* ── card view ── */
.wl-card2 {
  background: var(--surf2); border: 1px solid var(--bdr);
  border-radius: 10px; padding: 14px 16px; margin-bottom: 4px;
}
.wl-card2-sel  { border-color: var(--blue) !important; background: var(--surf) !important; }
.wl-card2-name { font-size: 14px; font-weight: 700; color: var(--txt); }
.wl-card2-id   { font-size: 11px; color: var(--muted); margin-top: 2px; }
.wl-card2-price{ font-size: 22px; font-weight: 700; margin-top: 8px; color: var(--txt); }
.wl-card2-pct  { font-size: 13px; margin-top: 3px; }
.wl-card2-sig  { font-size: 12px; font-weight: 600; margin-top: 8px; }

/* ── button tweaks ── */
.stButton > button {
  background: var(--surf2) !important;
  border: 1px solid var(--bdr) !important;
  color: var(--muted) !important;
  border-radius: 6px !important;
  font-size: 12px !important;
  padding: 4px 8px !important;
  margin-top: 2px !important;
}
.stButton > button:hover {
  border-color: var(--blue) !important;
  color: var(--txt) !important;
}

/* ═══════════════════════════════════════════════════════════════════════════
   MOBILE  ≤ 768px
═══════════════════════════════════════════════════════════════════════════ */
@media (max-width: 768px) {

  /* ── reduce page padding ── */
  .block-container { padding: 0.6rem 0.7rem 1rem !important; }

  /* ── sidebar: native overlay width, not fixed ── */
  section[data-testid="stSidebar"] { width: min(85vw, 300px) !important; }

  /* ── header: stack vertically, hide timestamp ── */
  .hdr {
    flex-direction: column !important;
    align-items: flex-start !important;
    gap: 3px !important;
    padding: 4px 0 8px !important;
  }
  .hdr-title { font-size: 14px !important; line-height: 1.3; }
  .hdr-idx   { font-size: 12px !important; }
  .hdr-val   { font-size: 13px !important; }
  .hdr > div:last-child { display: none !important; }

  /* ── tabs: horizontally scrollable, no wrap ── */
  .stTabs [data-baseweb="tab-list"] {
    overflow-x: auto !important;
    flex-wrap: nowrap !important;
    -webkit-overflow-scrolling: touch;
    scrollbar-width: none !important;
    padding: 3px !important;
  }
  .stTabs [data-baseweb="tab-list"]::-webkit-scrollbar { display: none; }
  .stTabs [data-baseweb="tab"] {
    white-space: nowrap !important;
    flex-shrink: 0 !important;
    padding: 7px 12px !important;
    font-size: 12px !important;
  }

  /* ── touch targets: 44px min height ── */
  .stButton > button {
    min-height: 44px !important;
    font-size: 14px !important;
    padding: 10px 12px !important;
  }

  /* ── KPI grid: 2 columns ── */
  .kgrid { grid-template-columns: repeat(2, 1fr) !important; }

  /* ── level box: 2 columns ── */
  .lvl-grid { grid-template-columns: repeat(2, 1fr) !important; }

  /* ── watchlist grid: 2 columns ── */
  .wl-grid { grid-template-columns: repeat(2, 1fr) !important; }

  /* ── font sizes: raise minimum ── */
  .klabel    { font-size: 11px !important; }
  .kval      { font-size: 18px !important; }
  .sec-title { font-size: 11px !important; }
  .scard-name, .wl-card-id { font-size: 12px !important; }
  .rpt       { font-size: 13px !important; padding: 10px 12px !important; }

  /* ── signal banner ── */
  .sig-banner { font-size: 15px !important; padding: 10px 14px !important; }

  /* ── remove horizontal margin on report cards ── */
  .rpt, .kbox, .scard { margin-left: 0 !important; margin-right: 0 !important; }
}

/* ═══════════════════════════════════════════════════════════════════════════
   SMALL PHONES  ≤ 480px
═══════════════════════════════════════════════════════════════════════════ */
@media (max-width: 480px) {

  /* ── watchlist: single column ── */
  .wl-grid { grid-template-columns: 1fr !important; }

  /* ── level box: also single column ── */
  .lvl-grid { grid-template-columns: repeat(2, 1fr) !important; }

  /* ── tighter block padding ── */
  .block-container { padding: 0.4rem 0.5rem 1rem !important; }
}
</style>
""", unsafe_allow_html=True)

# Apply theme to DOM on every render
_theme = st.session_state.get("theme", "light")
_components.html(
    f'<script>window.parent.document.documentElement.setAttribute("data-theme","{_theme}");</script>',
    height=0,
)

# Persistent sidebar expand button — slim tab on desktop, FAB on mobile
_components.html("""
<script>
(function() {
  var doc = window.parent.document;

  function ensureStyles() {
    if (doc.getElementById('sb-btn-styles')) return;
    var s = doc.createElement('style');
    s.id = 'sb-btn-styles';
    s.textContent = [
      '#sb-expand-btn {',
      '  position:fixed; left:0; top:50%; transform:translateY(-50%);',
      '  z-index:99999; width:22px; height:48px; display:none;',
      '  align-items:center; justify-content:center;',
      '  background:var(--surf,#fff); border:1px solid var(--bdr,#dee2e6);',
      '  border-left:none; border-radius:0 8px 8px 0;',
      '  font-size:20px; color:var(--blue,#0d6efd); cursor:pointer;',
      '  box-shadow:3px 0 8px rgba(0,0,0,.12); padding:0; line-height:1;',
      '}',
      '@media (max-width:768px) {',
      '  #sb-expand-btn {',
      '    left:12px !important; bottom:24px !important;',
      '    top:auto !important; transform:none !important;',
      '    width:48px !important; height:48px !important;',
      '    border-radius:50% !important;',
      '    border:1.5px solid var(--bdr,#dee2e6) !important;',
      '    font-size:24px !important;',
      '    box-shadow:0 4px 14px rgba(0,0,0,.2) !important;',
      '  }',
      '}'
    ].join('');
    doc.head.appendChild(s);
  }

  function ensureBtn() {
    ensureStyles();
    if (doc.getElementById('sb-expand-btn')) return;
    var btn = doc.createElement('button');
    btn.id = 'sb-expand-btn';
    btn.title = 'Expand sidebar';
    btn.innerHTML = '&#8250;';
    btn.onmouseenter = function() { btn.style.background = 'var(--surf2,#f1f3f5)'; };
    btn.onmouseleave = function() { btn.style.background = ''; };
    btn.onclick = function() {
      var toggle =
        doc.querySelector('[data-testid="stSidebarCollapsedControl"] button') ||
        doc.querySelector('[data-testid="stSidebarCollapseButton"] button') ||
        doc.querySelector('button[aria-label*="sidebar"]') ||
        doc.querySelector('button[aria-label*="Sidebar"]');
      if (toggle) toggle.click();
    };
    doc.body.appendChild(btn);
  }

  function update() {
    ensureBtn();
    var btn = doc.getElementById('sb-expand-btn');
    var sb  = doc.querySelector('[data-testid="stSidebar"]');
    if (!btn || !sb) return;
    var collapsed = sb.getBoundingClientRect().right < 20;
    btn.style.display = collapsed ? 'flex' : 'none';
  }

  setInterval(update, 250);
  update();
})();
</script>
""", height=0)


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    if not render_login_page():
        return

    stocks = load_db()
    if not stocks:
        stocks = [
            {"stock_id": "2330.TW", "stock_name": "台積電",     "holding_status": False},
            {"stock_id": "2303.TW", "stock_name": "聯電",       "holding_status": False},
            {"stock_id": "2881.TW", "stock_name": "富邦金",     "holding_status": True},
            {"stock_id": "2412.TW", "stock_name": "中華電",     "holding_status": False},
            {"stock_id": "4943.TW", "stock_name": "康控-KY",    "holding_status": True},
            {"stock_id": "3711.TW", "stock_name": "日月光投控", "holding_status": False},
        ]
        save_db(stocks)

    groups = load_groups()

    if "selected_stock" not in st.session_state:
        st.session_state.selected_stock = stocks[0]["stock_id"] if stocks else ""

    with st.sidebar:
        username = st.session_state.get("username", "")
        st.markdown(
            f'<div style="font-size:12px;color:var(--muted);padding:6px 0 2px;">👤 {username}</div>',
            unsafe_allow_html=True,
        )
        _tc1, _tc2 = st.columns(2)
        with _tc1:
            if st.button("Light", use_container_width=True,
                         type="primary" if _theme == "light" else "secondary"):
                st.session_state.theme = "light"
                st.rerun()
        with _tc2:
            if st.button("Dark", use_container_width=True,
                         type="primary" if _theme == "dark" else "secondary"):
                st.session_state.theme = "dark"
                st.rerun()
        if st.button("登出", use_container_width=True):
            st.session_state.clear()
            st.rerun()
        st.markdown('<hr style="border-color:var(--bdr);margin:8px 0;">', unsafe_allow_html=True)

    render_sidebar(stocks)

    # Header
    idx_val, idx_delta = fetch_index()
    d_cls = "pos" if idx_delta.startswith("+") else "neg" if idx_delta.startswith("-") else "neu"
    now_str = _dt.now().strftime("%Y-%m-%d %H:%M")

    st.markdown(
        f'<div class="hdr">'
        f'<div class="hdr-title">雙 Agent 股票量化 · K 線型態智能監控儀表板</div>'
        f'<div class="hdr-idx">加權 (TAIEX)</div>'
        f'<div class="hdr-val">{idx_val}&nbsp;<span class="{d_cls}">{idx_delta}</span></div>'
        f'<div class="hdr-idx" style="margin-left:auto;font-size:11px;">更新 {now_str}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Main tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "即時市場熱力圖",
        "追蹤名單分析",
        "觀察清單",
        groups[0]["name"],
        groups[1]["name"],
    ])
    with tab1:
        render_heatmap_tab()
    with tab2:
        render_analysis_tab(stocks)
    with tab3:
        render_watchlist_table(display_stocks=stocks, tab_key="wl", title="全部觀察股票")
    with tab4:
        render_group_tab(stocks, 0, groups)
    with tab5:
        render_group_tab(stocks, 1, groups)

    # ── Two-phase sidebar navigation: click main tab → click sub-tab ──────────
    nav = st.session_state.get("_nav_step", 0)
    if nav == 1:
        # Phase 1: switch to 追蹤名單分析; next rerender will run phase 2
        st.session_state._nav_step = 2
        _components.html("""<script>
setTimeout(function(){
  var tabs=window.parent.document.querySelectorAll('[data-baseweb="tab"]');
  for(var i=0;i<tabs.length;i++){
    if(tabs[i].textContent.trim()==='追蹤名單分析'){tabs[i].click();break;}
  }
},120);
</script>""", height=1)
    elif nav == 2:
        # Phase 2: switch to 量化與籌碼特徵 sub-tab
        st.session_state._nav_step = 0
        _components.html("""<script>
setTimeout(function(){
  var tabs=window.parent.document.querySelectorAll('[data-baseweb="tab"]');
  for(var i=0;i<tabs.length;i++){
    if(tabs[i].textContent.trim()==='量化與籌碼特徵'){tabs[i].click();break;}
  }
},120);
</script>""", height=1)


main()
