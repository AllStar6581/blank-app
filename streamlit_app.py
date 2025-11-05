import streamlit as st

POSITION="sidebar"

st.set_page_config(layout="wide", page_icon="👨‍💻", page_title="Kriminetskii SWE")
resume_page = st.Page("pages/resume_page.py", title="Resume", icon=":material/badge:")
pg = st.navigation([resume_page],position=POSITION, expanded=True)
pg.run()
