import streamlit as st

POSITION = "sidebar"

if "language" not in st.session_state:
    st.session_state["language"] = "ENGLISH"

st.set_page_config(layout="wide", page_icon="👨‍💻", page_title="Kriminetskii SWE")
resume_page = st.Page("pages/resume_page.py", title="Resume", icon=":material/badge:")
pg = st.navigation([resume_page], position=POSITION, expanded=True)
pg.run()
