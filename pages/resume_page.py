import io
import os
import sys
import inspect


dir_name = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if dir_name not in sys.path:
    sys.path.append(dir_name)

from PIL import Image
import streamlit as st
from pathlib import Path
from functools import cache, lru_cache
# from streamlit_tags import st_tags

from pages.base_page import Page
from data.resume_data import resume_dict
from controller.resume_controller import PdfPage, ResumePage as Resume, InternationalDocxGenerator
from streamlit.runtime.scriptrunner import get_script_run_ctx

import streamlit as st
import base64

def embed_font_base64(font_path, font_name):
    with open(font_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode()
    css = f"""
    <style>
    @font-face {{
        font-family: '{font_name}';
        src: url(data:font/otf;base64,{encoded}) format('opentype');
    }}
    * {{
        font-family: '{font_name}', sans-serif;
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

# Normalize skills for comparison
def normalize(skills):
    return {s.strip().lower() for s in skills}

# Ensure selected_skills exists in session state
if "selected_skills" not in st.session_state:
    st.session_state.selected_skills = set()

resume_page = Resume.from_json(resume_dict)
png_page = PdfPage(
    resume_page,
    pallette={
        "primary_color": "#f8f3eb",
        "secondary_color": "#88a9c3",
        "background_color": "#2b4257",
        "black_color": "#FFFFFF",
        "white_color": "#091235",
    },
)

# doc_page = DocGenerator(resume_page=resume_page).generate(output_path="resume.docx")
# doc_page
@cache
def get_png_page_download(png_page: PdfPage):
    pagebuff = io.BytesIO()
    png_page.create_resume_png(pagebuff)
    pagebuff.seek(0)
    return pagebuff.getvalue()


# @cache
def get_docx_page_download(page: Resume):
    docx_gen = InternationalDocxGenerator(page)
    pagebuff = io.BytesIO()
    docx_gen.generate(pagebuff)
    # png_page.create_resume_png(pagebuff)
    pagebuff.seek(0)
    return pagebuff.getvalue()


# PDFbyte = get_png_page_download(png_page)
PDFbyte=b''
PDFbyte=get_docx_page_download(resume_page)


class ResumeStPage(Page):

    @classmethod
    @lru_cache(maxsize=None)
    def render_experience_item_expander(cls, exp, index):
        pass

    @classmethod
    def page(cls):
        current_dir = Path(__file__).parent
        css_file = current_dir / "styles" / "main.css"
        profile_pic = current_dir.parent / "static/me.jpg"

        # embed_font_base64("fonts/WarowniaNrw.otf", "Warownia")     

        with open(css_file) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
        profile_pic = Image.open(profile_pic)

        col1, col2 = st.columns(2)
        with col1:
            st.image(profile_pic, width=330)

        with col2:
            st.title(resume_page.name)
            st.write(resume_page.expected_position)
            st.download_button(
                label="📄 Download 1-page CV (png)",
                data=PDFbyte,
                # file_name="Resume.png",
                file_name="Resume.docx",
                mime="application/octet-stream",
            )
            st.write("📫", resume_page.email)

        cols = st.columns(len(resume_page.contacts))
        for i, contact in enumerate(resume_page.contacts):
            cols[i].write(contact.to_markdown())

        st.write("---")
        st.subheader("Experience")

        # months = resume_page.total_experience_months
        months = resume_page.total_experience_months_wide
        st.success(f"Total experience: {months // 12} years {months % 12} months")

        for i, exp in enumerate(resume_page.ordered_experience):
            key = f"skills-selection-{i}"
            current_skills = exp.skills
            current_skills_norm = normalize(current_skills)

            # Determine which of these skills are selected
            selected_in_this_exp = {
                s for s in current_skills if s.strip().lower() in st.session_state.selected_skills
            }

            # Expander logic
            default_expanded = i <= 2
            has_selected_overlap = bool(current_skills_norm & st.session_state.selected_skills)
            expanded = default_expanded or has_selected_overlap

            with st.expander(
                f"{exp.company_name} | {exp.position_name} | "
                f"{str(exp.total_time_delta.years)+' yr' if exp.total_time_delta.years else ''} {exp.total_time_delta.months} mo",
                expanded=expanded,
            ):
                st.header(exp.company_name)
                if exp.company_contacts:
                    contact_html = (
                        f'<a href="{exp.company_contacts_link}">🔗 {exp.company_contacts}</a>'
                        if exp.company_contacts_link
                        else f"{exp.company_contacts}"
                    )
                    st.markdown(contact_html, unsafe_allow_html=True)

                if exp.position_name:
                    st.subheader(exp.position_name)

                st.write(
                    f"{exp.work_start_date_object.strftime('%b %Y')} - "
                    f"{exp.work_end_date_object.strftime('%b %Y') if not exp.is_still_working else 'Present'}"
                )

                for pt in exp.action_points:
                    st.markdown(f"- {pt}")

                st.markdown("#### Responsibilities")
                for res in exp.responsibilities:
                    st.markdown(f"- {res}")

                st.markdown(exp.description)

                if exp.video_links:
                    vid_cols = st.columns(len(exp.video_links))
                    for idx, link in enumerate(exp.video_links):
                        with vid_cols[idx]:
                            st.video(str(link))

                # Pills: show default selections
                selected_pills = st.pills(
                    "Skills",
                    current_skills,
                    selection_mode="multi",
                    key=key,
                    default=selected_in_this_exp,
                )

                # Normalize current selections
                norm_selected = normalize(selected_pills)

                # Update global selected_skills state
                changed = False
                for skill in current_skills_norm:
                    if skill in st.session_state.selected_skills and skill not in norm_selected:
                        st.session_state.selected_skills.remove(skill)
                        changed = True
                        # search_keywords = list(st.session_state.selected_skills) 
                    elif skill not in st.session_state.selected_skills and skill in norm_selected:
                        st.session_state.selected_skills.add(skill)
                        changed = True
                        # search_keywords = list(st.session_state.selected_skills) 
                    
                if changed:
                    pass
                    # st.rerun()

def get_caller_module():
    frame = inspect.currentframe()
    try:
        # Поднимаемся на 2 уровня вверх:
        # 1-й уровень — это вызов этой функции,
        # 2-й уровень — это место, где импортировали текущий модуль
        caller_frame = frame.f_back.f_back
        caller_module = inspect.getmodule(caller_frame)
        return caller_module.__name__ if caller_module else None
    finally:
        del frame  # Важно для избежания утечек памяти


if __name__ != "__main__":
    caller = get_caller_module()
    print(f"Импортировано из модуля: {caller}")
    if caller == 'streamlit.navigation.page':
        ResumeStPage.page()
else:
    print("imported as main")
