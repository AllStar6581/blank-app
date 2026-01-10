import io
import os
import sys
import inspect
import locale


dir_name = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if dir_name not in sys.path:
    sys.path.append(dir_name)

from PIL import Image
import streamlit as st
from pathlib import Path
from functools import cache, lru_cache
import phonenumbers

from pages.base_page import Page
from data.resume_data import resume_dict
from data.resume_data_ru import resume_dict as resume_dict_ru
from controller.resume_controller import ResumePage as Resume, SkillCategorized
from controller.resume_docx_generator import InternationalDocxGenerator
from controller.resume_pdf_generator import HHRuPDFGenerator
from streamlit.runtime.scriptrunner import get_script_run_ctx
from locales.localization import get_text

import streamlit as st
import base64
from controller.data_structures import CaseInsensitiveSet


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
# TODO: move to model
def normalize(skills):
    normalized_skill_set = set()
    for skill in skills:
        if isinstance(skill, str):
            normalized_skill_set.add(skill.strip().lower())
        elif isinstance(skill, SkillCategorized):
            normalized_skill_set.add(skill.name.strip().lower())
        else:
            raise Exception("Unexpected object in skillset")
    return normalized_skill_set
    # return {s.strip().lower() for s in skills}


# Ensure selected_skills exists in session state
if "selected_skills" not in st.session_state:
    st.session_state.selected_skills = set()


if "language" not in st.session_state or st.session_state.language == "ENGLISH":
    resume_page = Resume.from_json(resume_dict)
else:
    resume_page = Resume.from_json(resume_dict_ru)
# def resume_page_default() -> Resume:
#     global resume_page
#     resume_page = Resume.from_json(resume_dict)
#     return resume_page


# def resume_page_ru() -> Resume:
#     global resume_page
#     resume_page = Resume.from_json(resume_dict_ru)
#     return resume_page


# resume_page = resume_page_default()


# def switch_lang_eng():
#     if 'language' not in st.session_state or st.session_state.language != "ENGLISH":
#         st.session_state['language'] = 'ENGLISH'


# def switch_lang_ru():
#     if 'language' not in st.session_state or st.session_state.language != "RUSSIAN":
#         st.session_state['language'] = 'RUSSIAN'


def switch_lang_rus_eng():
    if "language" not in st.session_state or st.session_state.language != "ENGLISH":
        st.session_state["language"] = "ENGLISH"
        locale.setlocale(locale.LC_ALL, "en_US.UTF-8")
    else:
        st.session_state["language"] = "RUSSIAN"
        locale.setlocale(locale.LC_ALL, "ru_RU.UTF-8")


# png_page = PdfPage(
#     resume_page,
#     # pallette={
#     #     "primary_color": "#f8f3eb",
#     #     "secondary_color": "#88a9c3",
#     #     "background_color": "#2b4257",
#     #     "black_color": "#FFFFFF",
#     #     "white_color": "#091235",
#     # },
# )


# doc_page = DocGenerator(resume_page=resume_page).generate(output_path="resume.docx")
# doc_page
# @cache
def get_png_page_download(png_page):
    pagebuff = io.BytesIO()
    png_page.create_resume_png(pagebuff)
    pagebuff.seek(0)
    return pagebuff.getvalue()


# @cache
# @st.cache_data
def get_docx_page_download(page: Resume):
    if "language" not in st.session_state or st.session_state.language != "ENGLISH":
        generator_class = HHRuPDFGenerator
    else:
        generator_class = InternationalDocxGenerator
    docx_gen = generator_class(page)
    pagebuff = io.BytesIO()
    docx_gen.generate(pagebuff)
    # png_page.create_resume_png(pagebuff)
    pagebuff.seek(0)
    return pagebuff.getvalue()


# PDFbyte = get_png_page_download(png_page)
PDFbyte = b""
PDFbyte = get_docx_page_download(resume_page)


class ResumeStPage(Page):
    @classmethod
    @lru_cache(maxsize=None)
    def render_experience_item_expander(cls, exp, index):
        pass

    @classmethod
    def page(cls):
        locale_code = (
            st.session_state.get("language")[:3]
            if st.session_state.get("language")
            else "ENG"
        )
        L_ = get_text(locale_code)
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
            col_lang_1, col_lang_2 = st.columns(2)
            with col_lang_1:
                st.button(
                    label="русский/english", key="lang_ru", on_click=switch_lang_rus_eng
                )

        with col2:
            st.title(resume_page.name)
            st.write(resume_page.expected_position)
            st.download_button(
                label=L_("📄 Download CV as .docx file (word)"),
                data=PDFbyte,
                # file_name="Resume.png",
                file_name=L_("Kriminetskii_Lead_Backend_2026_CV.docx"),
                mime="application/octet-stream",
            )
            st.write("📫", resume_page.email)
            if resume_page.tel:
                tel_e164 = phonenumbers.format_number(
                    phonenumbers.parse(resume_page.tel, None),
                    phonenumbers.PhoneNumberFormat.INTERNATIONAL,
                )
                tel_html = f'☎️ <a href="tel:{resume_page.tel}">{tel_e164}</a>'
                st.markdown(tel_html, unsafe_allow_html=True)

        cols = st.columns(len(resume_page.contacts))
        for i, contact in enumerate(resume_page.contacts):
            cols[i].write(contact.to_markdown())

        st.write("---")
        st.subheader(L_("Experience"))

        # months = resume_page.total_experience_months
        months = resume_page.total_experience_months_wide
        st.success(
            f"{L_('Total experience')}: {months // 12} {L_('years')} {months % 12} {L_('months')}"
        )

        for i, exp in enumerate(resume_page.ordered_experience):
            key = f"skills-selection-{i}"
            # current_skills = exp.skills
            current_skills = list()
            for skill in exp.skills:
                if isinstance(skill, str):
                    current_skills.append(skill)
                elif isinstance(skill, SkillCategorized):
                    current_skills.append(skill.name)
                else:
                    raise Exception("Unexpected object in skillset")

            current_skills_norm = CaseInsensitiveSet(normalize(current_skills))

            # Determine which of these skills are selected
            # TODO: move to model
            selected_in_this_exp = CaseInsensitiveSet()
            for skill in st.session_state.selected_skills:
                if isinstance(skill, str):
                    selected_in_this_exp.add(skill.strip().lower())
                elif isinstance(skill, SkillCategorized):
                    selected_in_this_exp.add(skill.name.strip().lower())
                else:
                    raise Exception("Unexpected object in skillset")

            # selected_in_this_exp = {
            #     s for s in current_skills if s.strip().lower() in st.session_state.selected_skills
            # }

            # Expander logic
            default_expanded = i <= 2
            has_selected_overlap = bool(
                current_skills_norm & st.session_state.selected_skills
            )
            expanded = default_expanded or has_selected_overlap

            txt_years_name = L_("yr")
            txt_months_name = L_("mo")
            txt_years = (
                str(exp.total_time_delta.years) + f" {txt_years_name}"
                if exp.total_time_delta.years
                else ""
            )
            with st.expander(
                f"{exp.company_name} | {exp.position_name} | "
                f"{txt_years} {exp.total_time_delta.months} {txt_months_name}",
                expanded=expanded,
            ):
                st.header(exp.company_name)
                if exp.company_contacts:
                    contact_html = (
                        f'🔗 <a href="{exp.company_contacts_link}">{exp.company_contacts}</a>'
                        if exp.company_contacts_link
                        else f"{exp.company_contacts}"
                    )
                    st.markdown(contact_html, unsafe_allow_html=True)

                if exp.position_name:
                    st.subheader(exp.position_name)

                st.write(
                    f"{exp.work_start_date_object.strftime('%b %Y')} - "
                    f"{exp.work_end_date_object.strftime('%b %Y') if not exp.is_still_working else L_('Present')}"
                )

                for pt in exp.action_points:
                    st.markdown(f"- {pt}")

                st.markdown(L_("#### Responsibilities"))
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
                    L_("Skills"),
                    current_skills,
                    selection_mode="multi",
                    key=key,
                    # default=selected_in_this_exp,
                    default=CaseInsensitiveSet(current_skills).intersection(
                        selected_in_this_exp
                    ),
                )

                # Normalize current selections
                norm_selected = normalize(selected_pills)

                # Update global selected_skills state
                changed = False
                for skill in current_skills_norm:
                    if (
                        skill in st.session_state.selected_skills
                        and skill not in norm_selected
                    ):
                        st.session_state.selected_skills.remove(skill)
                        changed = True
                        # search_keywords = list(st.session_state.selected_skills)
                    elif (
                        skill not in st.session_state.selected_skills
                        and skill in norm_selected
                    ):
                        st.session_state.selected_skills.add(skill)
                        changed = True
                        # search_keywords = list(st.session_state.selected_skills)

                if changed:
                    pass
                    # st.rerun()

        st.markdown(L_("#### Education"))

        for i, edu in enumerate(resume_page.edu):
            with st.container(height=None, border=True):
                col_logo, col_text, _, _ = st.columns(4, gap="small")
                with col_logo:
                    st.image(edu.icon, width=150, clamp=True, caption=f"{edu.website}")
                with col_text:
                    st.write(edu.degree)
                    st.write(f"{edu.year_start} - {edu.year_end}")
                    st.write(edu.university)
                    st.write(edu.programme)


def get_caller_module():
    frame = inspect.currentframe()
    try:
        caller_frame = frame.f_back.f_back
        caller_module = inspect.getmodule(caller_frame)
        return caller_module.__name__ if caller_module else None
    finally:
        del frame


if __name__ != "__main__":
    caller = get_caller_module()
    if caller == "streamlit.navigation.page":
        ResumeStPage.page()
else:
    print("imported as main")
