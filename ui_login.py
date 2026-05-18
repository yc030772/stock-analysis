from __future__ import annotations

from datetime import datetime, timedelta

import streamlit as st

from cookie_auth import COOKIE_NAME, COOKIE_DAYS, make_token
from user_db import register, verify


def render_login_page(cookie_manager) -> bool:
    """Render login/register UI. Returns True if already authenticated."""
    if st.session_state.get("username"):
        return True

    _, center, _ = st.columns([1, 2, 1])
    with center:
        st.markdown(
            '<div style="font-size:26px;font-weight:700;color:#c9d1d9;'
            'text-align:center;margin:32px 0 24px;">📊 股票量化監控儀表板</div>',
            unsafe_allow_html=True,
        )

        tab_login, tab_reg = st.tabs(["登入", "註冊新帳號"])

        with tab_login:
            with st.form("login_form"):
                username = st.text_input("帳號", placeholder="輸入帳號")
                password = st.text_input("密碼", type="password", placeholder="輸入密碼")
                submitted = st.form_submit_button("登入", use_container_width=True, type="primary")
            if submitted:
                if verify(username, password):
                    uname = username.strip().lower()
                    st.session_state["username"] = uname
                    # Persist login in browser cookie for 30 days
                    expires = datetime.now() + timedelta(days=COOKIE_DAYS)
                    cookie_manager.set(COOKIE_NAME, make_token(uname), expires_at=expires)
                    st.rerun()
                else:
                    st.error("帳號或密碼錯誤。")

        with tab_reg:
            with st.form("register_form"):
                new_user  = st.text_input("帳號", placeholder="至少 3 個字元", key="reg_user")
                new_pass  = st.text_input("密碼", type="password", placeholder="至少 6 個字元", key="reg_pass")
                new_pass2 = st.text_input("確認密碼", type="password", placeholder="再次輸入密碼", key="reg_pass2")
                submitted2 = st.form_submit_button("建立帳號", use_container_width=True, type="primary")
            if submitted2:
                if new_pass != new_pass2:
                    st.error("兩次輸入的密碼不一致。")
                else:
                    ok, msg = register(new_user, new_pass)
                    if ok:
                        st.success(msg + "  請切換到「登入」頁面。")
                    else:
                        st.error(msg)

    return False
