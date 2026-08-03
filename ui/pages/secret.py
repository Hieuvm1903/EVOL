import pandas as pd
import streamlit as st

from config import SECRET_KEY, TIMEZONE
from services import blog_service
from ui.styles import render_card


def render() -> None:
    col1, col2 = st.columns([1, 3])
    with col1:
        key_input = st.text_input("Key???", "/Evolut??n")
    with col2:
        text = st.text_area("My thought", "")

    if st.button("Submit", key="submit_secret", icon=":material/send:"):
        if SECRET_KEY in key_input:
            blog_service.add_post(text.strip())
            st.success("Posted!!!")
            st.rerun()
        else:
            st.warning("Don't ya remember it, EVOL?")

    posts = blog_service.get_posts()
    if not posts.empty:
        posts["time"] = pd.to_datetime(posts["time"])
        posts["time"] = posts.apply(lambda row: row["time"].astimezone(TIMEZONE), axis=1)
        posts = posts.sort_values(by="time", ascending=False)
        for _, row in posts.iterrows():
            render_card(
                title=None,
                meta=row["time"].strftime("%m/%d/%Y, %H:%M:%S"),
                body=row["content"],
            )
