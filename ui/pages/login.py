import streamlit as st

from services import auth_service


def _render_login_form() -> None:
    with st.form("login_form"):
        username = st.text_input("Username")
        c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
        password = c1.text_input("Password", type="password")
        submitted = c2.form_submit_button("Log in", icon=":material/login:", use_container_width=True)

    if submitted:
        user = auth_service.verify_user(username, password)
        if user:
            st.session_state["user"] = user
            auth_service.remember_login(user)
            st.success(f"Welcome back, {user['username']}!")
            st.rerun()
        else:
            st.error("Wrong username or password.")


def _render_signup_form() -> None:
    with st.form("signup_form"):
        username = st.text_input("Choose a username", key="signup_username")
        c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
        password = c1.text_input("Choose a password", type="password", key="signup_password")
        submitted = c2.form_submit_button("Create account", icon=":material/person_add:",
                                           use_container_width=True)

    if submitted:
        ok, message = auth_service.register_user(username, password)
        (st.success if ok else st.error)(message)


def render() -> None:
    st.markdown("## :material/login: Login")

    user = st.session_state.get("user")
    if user:
        st.success(f"You're logged in as **{user['username']}**.", icon=":material/check_circle:")
        st.caption("You'll stay logged in even if you reload the page, for 30 days.")
        st.caption("Head to the Music tab to build playlists.")
        if st.button("Log out", icon=":material/logout:"):
            del st.session_state["user"]
            auth_service.forget_login()
            st.rerun()
        return

    tab1, tab2 = st.tabs([":material/login: Log in", ":material/person_add: Sign up"])
    with tab1:
        _render_login_form()
    with tab2:
        _render_signup_form()