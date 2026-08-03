import pandas as pd
import streamlit as st

from config import TIMEZONE
from services import notes_service
from ui.styles import render_card


def render() -> None:
    st.markdown("## :material/self_improvement: Relax")
    text = st.text_area("Tâm sự vào đây (Ẩn danh 100%)", "")

    def _submit():
        notes_service.add_note("{" + text + "}")
        st.rerun()

    st.button("Submit", key="submit_note", icon=":material/send:", on_click=_submit)

    notes = notes_service.get_notes()
    if not notes.empty:
        notes["time"] = pd.to_datetime(notes["time"])
        notes["time"] = notes.apply(lambda row: row["time"].astimezone(TIMEZONE), axis=1)
        notes = notes.sort_values(by="time", ascending=False)
        for _, row in notes.iterrows():
            render_card(
                title=None,
                meta=row["time"].strftime("%m/%d/%Y, %H:%M:%S"),
                body=row["content"],
            )
