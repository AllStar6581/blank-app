import streamlit as st
import os
os.environ["LANG"] = "C.UTF-8"
os.environ["LC_ALL"] = "C.UTF-8"

POSITION = "sidebar"

if "language" not in st.session_state:
    st.session_state["language"] = "ENGLISH"

st.set_page_config(layout="wide", page_icon="👨‍💻", page_title="Kriminetskii SWE")
resume_page = st.Page("pages/resume_page.py", title="Resume", icon=":material/badge:")
pg = st.navigation([resume_page], position=POSITION, expanded=True)
pg.run()
