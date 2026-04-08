"""Streamlit resume page — renders the interactive CV with skill filtering and DOCX download."""

import io
import locale
import re
import threading
from pathlib import Path
import os
import sys

dir_name = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if dir_name not in sys.path:
    sys.path.append(dir_name)

import phonenumbers
import streamlit as st
from PIL import Image

from controller.cache import (
    fetch_image_cached,
    get_cached,
    get_image_from_cache,
    make_cache_key,
    set_cached,
)
from controller.data_structures import CaseInsensitiveSet
from controller.resume_controller import (
    ResumePage as Resume,
)
from controller.resume_controller import (
    _extract_skill_name,
)
from controller.resume_docx_generator import InternationalDocxGenerator
from controller.resume_pdf_generator import HHRuPDFGenerator
from data.resume_data import resume_dict
from data.resume_data_ru import resume_dict as resume_dict_ru
from locales.localization import get_text

# ---------------------------------------------------------------------------
# Experimental flag — set to False to revert categorized skill display
# ---------------------------------------------------------------------------

_EXPERIMENTAL_CATEGORIZED_SKILLS = True
_EXPERIMENTAL_YT_FACADE = True  # False → revert to st.video for YouTube
_EXPERIMENTAL_VIDEO_CAROUSEL = True  # False → current st.columns layout
# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _group_skills_by_category(skills) -> dict[str, list[str]]:
    """Group an experience's skills by category for display."""
    from controller.resume_controller import SkillCategorized

    groups: dict[str, list[str]] = {}
    for skill in skills:
        if isinstance(skill, SkillCategorized) and skill.category:
            cat = skill.category
            name = skill.name
        else:
            cat = "Other"
            name = _extract_skill_name(skill)
        groups.setdefault(cat, []).append(name)
    return groups


def _normalize_skills(skills) -> set[str]:
    """Return a lowercase set of skill names for comparison."""
    return {_extract_skill_name(s).strip().lower() for s in skills}


def _skill_names_list(skills) -> list[str]:
    """Extract display names from a mixed list of str / SkillCategorized."""
    return [_extract_skill_name(s) for s in skills]


_YT_VIDEO_RE = re.compile(
    r"https?://(?:www\.)?(?:youtube\.com/(?:watch\?v=|embed/)|youtu\.be/)([a-zA-Z0-9_-]+)"
)

# Generic video platforms: (regex, embed-URL builder).
# YouTube is handled separately (facade with thumbnail).
_VIDEO_PLATFORMS: list[tuple[re.Pattern, callable]] = [
    (
        re.compile(r"https?://(?:m\.)?(?:vkvideo\.ru|vk\.com)/video(-?\d+)_(\d+)"),
        lambda m: f"https://vkvideo.ru/video_ext.php?oid={m.group(1)}&id={m.group(2)}&hd=2",
    ),
    (
        re.compile(r"https?://(?:www\.)?vimeo\.com/(\d+)"),
        lambda m: f"https://player.vimeo.com/video/{m.group(1)}",
    ),
    (
        re.compile(r"https?://rutube\.ru/video/([a-zA-Z0-9]+)"),
        lambda m: f"https://rutube.ru/play/embed/{m.group(1)}",
    ),
]


def _get_embed_url(link: str) -> str | None:
    """Return an iframe-ready embed URL for known platforms (excl. YouTube)."""
    for pattern, builder in _VIDEO_PLATFORMS:
        match = pattern.search(link)
        if match:
            return builder(match)
    return None


def _yt_facade_html(vid_id: str) -> str:
    """Return click-to-play YouTube facade HTML.

    Shows a full-size thumbnail with a YouTube-style play button.
    Only loads the real player iframe when the user clicks.
    """
    return f"""<!DOCTYPE html>
<html><head><style>
html, body {{ margin:0; padding:0; width:100%; height:100%; overflow:hidden; }}
.yt-facade {{
    width:100%; height:100%; cursor:pointer;
    background:#000 url('https://i.ytimg.com/vi/{vid_id}/hqdefault.jpg') center/cover no-repeat;
    display:flex; align-items:center; justify-content:center;
}}
.yt-play {{
    width:68px; height:48px; background:rgba(255,0,0,0.8);
    border-radius:14px; display:flex; align-items:center; justify-content:center;
    transition:background 0.2s;
}}
.yt-facade:hover .yt-play {{ background:#f00; }}
.yt-play::after {{
    content:''; border-style:solid;
    border-width:11px 0 11px 19px;
    border-color:transparent transparent transparent #fff;
    margin-left:4px;
}}
</style></head><body>
<div class="yt-facade" id="yt"><div class="yt-play"></div></div>
<script>
document.getElementById('yt').addEventListener('click', function() {{
    this.outerHTML = '<iframe src="https://www.youtube.com/embed/{vid_id}?autoplay=1"'
        + ' style="width:100%;height:100%" frameborder="0"'
        + ' allow="autoplay;encrypted-media" allowfullscreen></iframe>';
}});
</script>
</body></html>"""


def _video_embed_html(link: str, idx: int = 0) -> str | None:
    """Return embed HTML for a single video inside the carousel.

    YouTube gets a click-to-play facade (thumbnail + play button).
    Every other platform (VK, Vimeo, Rutube …) gets a direct iframe —
    those players already ship their own preview / play button.
    """
    # YouTube → facade with static thumbnail
    yt_match = _YT_VIDEO_RE.search(link)
    if yt_match:
        vid_id = yt_match.group(1)
        if _EXPERIMENTAL_YT_FACADE:
            thumb = f"https://i.ytimg.com/vi/{vid_id}/hqdefault.jpg"
            embed_url = f"https://www.youtube.com/embed/{vid_id}?autoplay=1"
            return (
                f'<div class="yt-facade" id="yt-{idx}"'
                f" style=\"background-image:url('{thumb}')\""
                f' data-src="{embed_url}">'
                f'<div class="play-btn yt"></div>'
                f'</div>'
            )
        return (
            f'<iframe src="https://www.youtube.com/embed/{vid_id}"'
            f' width="100%" height="100%" frameborder="0"'
            f' allow="autoplay;encrypted-media" allowfullscreen></iframe>'
        )

    # Generic platform → direct iframe
    embed_url = _get_embed_url(link)
    if embed_url:
        return (
            f'<iframe src="{embed_url}" width="100%" height="100%"'
            f' frameborder="0" loading="lazy"'
            f' allow="autoplay; encrypted-media; fullscreen;'
            f' picture-in-picture; screen-wake-lock;" allowfullscreen></iframe>'
        )

    return None


def _video_carousel_html(links: list[str]) -> str:
    """Wrap multiple video embeds in a CSS scroll-snap horizontal carousel."""
    items_html = ""
    dot_html = ""
    count = 0
    for link in links:
        embed = _video_embed_html(link, idx=count)
        if embed is None:
            continue
        active = " active" if count == 0 else ""
        items_html += f'<div class="carousel-item" id="slide-{count}">{embed}</div>'
        dot_html += f'<span class="dot{active}" data-idx="{count}"></span>'
        count += 1

    return f"""<!DOCTYPE html>
<html><head><style>
*{{ margin:0; padding:0; box-sizing:border-box; }}
html, body {{ width:100%; height:100%; overflow:hidden; font-family:sans-serif; }}

/* ── carousel layout ── */
.carousel-wrapper {{
    position:relative; width:100%; height:calc(100% - 36px);
    border-radius:12px; overflow:hidden;
    background:#111;
}}
.carousel {{
    display:flex; overflow-x:auto; scroll-snap-type:x mandatory;
    width:100%; height:100%; scroll-behavior:smooth;
    -ms-overflow-style:none; scrollbar-width:none;
}}
.carousel::-webkit-scrollbar {{ display:none; }}
.carousel-item {{
    flex:0 0 100%; scroll-snap-align:start;
    width:100%; height:100%; position:relative;
}}

/* ── prev / next arrows ── */
.nav-btn {{
    position:absolute; top:50%; transform:translateY(-50%);
    width:44px; height:44px; border-radius:50%;
    background:rgba(0,0,0,.55); color:#fff; border:2px solid rgba(255,255,255,.35);
    font-size:22px; cursor:pointer; z-index:10;
    display:flex; align-items:center; justify-content:center;
    transition:background .2s, border-color .2s, opacity .25s;
    opacity:.85; backdrop-filter:blur(4px);
}}
.nav-btn:hover {{ background:rgba(0,0,0,.8); border-color:rgba(255,255,255,.6); opacity:1; }}
.nav-btn.prev {{ left:10px; }}
.nav-btn.next {{ right:10px; }}
.nav-btn.hidden {{ opacity:0; pointer-events:none; }}

/* ── dots + counter ── */
.controls {{
    display:flex; justify-content:center; align-items:center;
    height:36px; gap:8px;
}}
.dot {{
    width:10px; height:10px; border-radius:50%;
    background:#bbb; cursor:pointer; transition:background .25s, transform .25s;
    border:none;
}}
.dot.active {{ background:#e04060; transform:scale(1.25); }}
.counter {{
    font-size:13px; color:#888; margin-left:8px; user-select:none;
}}

/* ── YouTube facade ── */
.yt-facade {{
    width:100%; height:100%; cursor:pointer;
    background:#000 center/cover no-repeat;
    display:flex; align-items:center; justify-content:center;
}}
.play-btn {{
    width:68px; height:48px; border-radius:14px;
    background:rgba(255,0,0,.8); border:none;
    display:flex; align-items:center; justify-content:center;
    transition:background .2s;
}}
.play-btn::after {{
    content:''; border-style:solid;
    border-width:12px 0 12px 20px;
    border-color:transparent transparent transparent #fff;
    margin-left:4px;
}}
.yt-facade:hover .play-btn {{ background:#f00; }}
</style></head><body>
<div class="carousel-wrapper">
    <button class="nav-btn prev hidden" id="prevBtn">&#10094;</button>
    <div class="carousel" id="carousel">{items_html}</div>
    <button class="nav-btn next{' hidden' if count <= 1 else ''}" id="nextBtn">&#10095;</button>
</div>
<div class="controls" id="controls">
    {dot_html}
    <span class="counter" id="counter">1 / {count}</span>
</div>
<script>
(function() {{
    var carousel = document.getElementById('carousel');
    var dots     = document.querySelectorAll('.dot');
    var prevBtn  = document.getElementById('prevBtn');
    var nextBtn  = document.getElementById('nextBtn');
    var counter  = document.getElementById('counter');
    var currentIdx = 0;
    var total = carousel.children.length;

    function updateUI() {{
        prevBtn.classList.toggle('hidden', currentIdx <= 0);
        nextBtn.classList.toggle('hidden', currentIdx >= total - 1);
        counter.textContent = (currentIdx + 1) + ' / ' + total;
        dots.forEach(function(d, i) {{
            d.classList.toggle('active', i === currentIdx);
        }});
    }}

    function goTo(idx) {{
        idx = Math.max(0, Math.min(idx, total - 1));
        carousel.children[idx].scrollIntoView({{behavior:'smooth', block:'nearest', inline:'start'}});
    }}

    prevBtn.addEventListener('click', function() {{ goTo(currentIdx - 1); }});
    nextBtn.addEventListener('click', function() {{ goTo(currentIdx + 1); }});
    dots.forEach(function(d) {{
        d.addEventListener('click', function() {{ goTo(parseInt(this.dataset.idx)); }});
    }});

    /* track which slide is visible */
    var observer = new IntersectionObserver(function(entries) {{
        entries.forEach(function(e) {{
            if (e.isIntersecting) {{
                currentIdx = Array.prototype.indexOf.call(carousel.children, e.target);
                updateUI();
            }}
        }});
    }}, {{ root: carousel, threshold: 0.6 }});
    Array.from(carousel.children).forEach(function(c) {{ observer.observe(c); }});

    /* click-to-play: replace YouTube facade with iframe */
    document.querySelectorAll('.yt-facade').forEach(function(el) {{
        el.addEventListener('click', function() {{
            this.outerHTML = '<iframe src="' + this.dataset.src + '" '
                + 'style="width:100%;height:100%" frameborder="0" '
                + 'allow="autoplay; encrypted-media" allowfullscreen></iframe>';
        }});
    }});

    updateUI();
}})();
</script>
</body></html>"""


def _render_video(link: str) -> None:
    """Render a single video: YouTube via facade, others via direct iframe."""
    if _EXPERIMENTAL_YT_FACADE:
        yt_match = _YT_VIDEO_RE.search(link)
        if yt_match:
            st.components.v1.html(_yt_facade_html(yt_match.group(1)), height=560)
            return

    embed_url = _get_embed_url(link)
    if embed_url:
        st.components.v1.html(
            f'<iframe src="{embed_url}" width="100%" height="560"'
            f' frameborder="0" loading="lazy"'
            f' allow="autoplay; encrypted-media; fullscreen;'
            f' picture-in-picture; screen-wake-lock;" allowfullscreen></iframe>',
            height=560,
        )
        return

    st.video(link)


# ---------------------------------------------------------------------------
# Cached data loaders (the key performance fix)
# ---------------------------------------------------------------------------


_resume_cache: dict[str, Resume] = {}
_resume_warming: set[str] = set()


def _load_resume(language: str) -> Resume:
    """Parse resume data once per language and cache in module-level dict.

    Using a dict instead of @st.cache_data so background threads can warm it.
    """
    if language in _resume_cache:
        return _resume_cache[language]
    data = resume_dict_ru if language == "RUSSIAN" else resume_dict
    result = Resume.from_json(data)
    _resume_cache[language] = result
    return result


def _prewarm_resume(language: str) -> None:
    """Parse and cache the other language's resume in a background thread."""
    if language in _resume_cache or language in _resume_warming:
        return
    _resume_warming.add(language)

    def _warm():
        try:
            _load_resume(language)
        finally:
            _resume_warming.discard(language)

    threading.Thread(target=_warm, daemon=True).start()


_pending_downloads: set[str] = set()
_prewarm_pending: set[str] = set()


def _download_cache_key(language: str, compact: bool) -> str:
    """Build the L2 cache key for a download variant."""
    data = resume_dict_ru if language == "RUSSIAN" else resume_dict
    key = make_cache_key(language, data)
    if compact:
        key += ":compact"
    return key


def _prewarm_download(language: str, compact: bool) -> None:
    """Generate and store a download variant in L2 cache (background thread)."""
    cache_key = _download_cache_key(language, compact)
    if cache_key in _prewarm_pending:
        return
    if get_cached(cache_key) is not None:
        return
    _prewarm_pending.add(cache_key)

    def _generate():
        try:
            data = resume_dict_ru if language == "RUSSIAN" else resume_dict
            resume = Resume.from_json(data)
            gen_cls = HHRuPDFGenerator if language == "RUSSIAN" else InternationalDocxGenerator
            buf = io.BytesIO()
            gen_cls(resume, compact=compact).generate(buf)
            buf.seek(0)
            set_cached(cache_key, buf.getvalue())
        finally:
            _prewarm_pending.discard(cache_key)

    threading.Thread(target=_generate, daemon=True).start()


def _ensure_image_downloaded(url: str) -> None:
    """Kick off a background download for a URL not yet in cache."""
    if url in _pending_downloads:
        return
    _pending_downloads.add(url)

    def _download():
        try:
            fetch_image_cached(url)
        finally:
            _pending_downloads.discard(url)

    threading.Thread(target=_download, daemon=True).start()


@st.cache_data
def _generate_download_bytes(language: str, compact: bool = True) -> bytes:
    """Generate the downloadable document bytes, cached per (language, compact).

    Checks L2 (Redis / local file) before generating; stores result in L2
    after generation so it survives process restarts.
    """
    data = resume_dict_ru if language == "RUSSIAN" else resume_dict
    cache_key = make_cache_key(language, data)
    if compact:
        cache_key += ":compact"

    cached = get_cached(cache_key)
    if cached is not None:
        return cached

    resume = _load_resume(language)
    generator_cls = HHRuPDFGenerator if language == "RUSSIAN" else InternationalDocxGenerator
    buf = io.BytesIO()
    generator_cls(resume, compact=compact).generate(buf)
    buf.seek(0)
    result = buf.getvalue()

    set_cached(cache_key, result)
    return result


# ---------------------------------------------------------------------------
# Session state init
# ---------------------------------------------------------------------------

if "selected_skills" not in st.session_state:
    st.session_state.selected_skills = CaseInsensitiveSet()

if "language" not in st.session_state:
    st.session_state["language"] = "ENGLISH"


def _switch_language():
    """Toggle between English and Russian."""
    if st.session_state.language == "ENGLISH":
        st.session_state["language"] = "RUSSIAN"
        try:
            locale.setlocale(locale.LC_ALL, "ru_RU.UTF-8")
        except locale.Error:
            pass
    else:
        st.session_state["language"] = "ENGLISH"
        try:
            locale.setlocale(locale.LC_ALL, "en_US.UTF-8")
        except locale.Error:
            pass

    # Clear cross-language skill selections so that widget keys
    # created with the old language are discarded.
    st.session_state.selected_skills = CaseInsensitiveSet()


# ---------------------------------------------------------------------------
# Experience fragment — isolated so skill-pill clicks only re-render this
# ---------------------------------------------------------------------------


def _on_pill_toggle(i, language, all_exp):
    """Callback: sync a flat pill click to global state (non-categorized path)."""
    key = f"skills-{language}-{i}"
    selected = st.session_state.get(key, [])
    selected_lower = {s.lower() for s in selected}

    exp_skills = _skill_names_list(all_exp[i].skills)
    exp_lower = {s.lower() for s in exp_skills}

    for s in selected_lower & exp_lower:
        st.session_state.selected_skills.add(s)
    for s in exp_lower - selected_lower:
        st.session_state.selected_skills.discard(s)

    global_lower = {s.lower() for s in st.session_state.selected_skills}
    for j, other_exp in enumerate(all_exp):
        if j == i:
            continue
        other_key = f"skills-{language}-{j}"
        other_skills = _skill_names_list(other_exp.skills)
        st.session_state[other_key] = [s for s in other_skills if s.lower() in global_lower]


def _on_categorized_pill_toggle(i, cat_idx, language, all_exp, all_grouped):
    """Callback: sync a categorized pill click to global state.

    Collects selected skills from ALL category pills of experience *i*,
    updates global state, then propagates to every other experience's
    category pills.
    """
    grouped_i = all_grouped[i]
    cats_i = list(grouped_i.values())

    # Collect all selected skills across every category of experience i
    all_selected_lower: set[str] = set()
    for c in range(len(cats_i)):
        key = f"skills-{language}-{i}-{c}"
        for s in st.session_state.get(key, []):
            all_selected_lower.add(s.lower())

    # Full skill set of experience i
    exp_lower = {_extract_skill_name(s).lower() for s in all_exp[i].skills}

    # Update global state
    for s in all_selected_lower & exp_lower:
        st.session_state.selected_skills.add(s)
    for s in exp_lower - all_selected_lower:
        st.session_state.selected_skills.discard(s)

    # Propagate to all OTHER experiences' category pills
    global_lower = {s.lower() for s in st.session_state.selected_skills}
    for j, _other_exp in enumerate(all_exp):
        if j == i:
            continue
        grouped_j = all_grouped[j]
        for c, cat_skills in enumerate(grouped_j.values()):
            other_key = f"skills-{language}-{j}-{c}"
            st.session_state[other_key] = [s for s in cat_skills if s.lower() in global_lower]


@st.fragment
def _render_experience(resume_page, language, L_):
    """Render the experience section with interactive skill pills."""
    all_exp = resume_page.ordered_experience

    # Pre-compute category groups for the categorized callback
    if _EXPERIMENTAL_CATEGORIZED_SKILLS:
        all_grouped = [_group_skills_by_category(exp.skills) for exp in all_exp]

    st.subheader(L_("Experience"))
    months = resume_page.total_experience_months_wide
    st.success(
        f"{L_('Total experience')}: {months // 12} {L_('years')} {months % 12} {L_('months')}"
    )

    for i, exp in enumerate(all_exp):
        current_skills = _skill_names_list(exp.skills)
        current_skills_norm = CaseInsensitiveSet(_normalize_skills(current_skills))

        default_expanded = i <= 2
        has_selected_overlap = bool(current_skills_norm & st.session_state.selected_skills)
        expanded = default_expanded or has_selected_overlap

        txt_yr = L_("yr")
        txt_mo = L_("mo")
        years_label = f"{exp.total_time_delta.years} {txt_yr}" if exp.total_time_delta.years else ""

        with st.expander(
            f"{exp.company_name} | {exp.position_name} | "
            f"{years_label} {exp.total_time_delta.months} {txt_mo}",
            expanded=expanded,
        ):
            st.header(exp.company_name)
            if exp.company_contacts:
                if exp.company_contacts_link:
                    st.markdown(
                        f'🔗 <a href="{exp.company_contacts_link}">{exp.company_contacts}</a>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.write(exp.company_contacts)

            if exp.position_name:
                st.subheader(exp.position_name)

            end_date_str = (
                L_("Present")
                if exp.is_still_working
                else exp.work_end_date_object.strftime("%b %Y")
            )
            st.write(f"{exp.work_start_date_object.strftime('%b %Y')} - {end_date_str}")

            if exp.description:
                st.markdown(exp.description)

            if exp.responsibilities:
                st.markdown(L_("#### Responsibilities"))
                for res in exp.responsibilities:
                    st.markdown(f"- {res}")

            if exp.action_points:
                st.markdown(L_("#### Results"))
                for pt in exp.action_points or []:
                    st.markdown(f"- {pt}")

            if exp.video_links:
                if _EXPERIMENTAL_VIDEO_CAROUSEL and len(exp.video_links) > 1:
                    st.components.v1.html(
                        _video_carousel_html([str(lnk) for lnk in exp.video_links]),
                        height=600,
                    )
                else:
                    vid_cols = st.columns(len(exp.video_links))
                    for idx, link in enumerate(exp.video_links):
                        with vid_cols[idx]:
                            _render_video(str(link))

            # --- Skills: categorized pills (experimental) or flat pills ---
            if _EXPERIMENTAL_CATEGORIZED_SKILLS:
                grouped = all_grouped[i]
                for c, (cat_name, cat_skills) in enumerate(grouped.items()):
                    st.pills(
                        cat_name,
                        cat_skills,
                        selection_mode="multi",
                        key=f"skills-{language}-{i}-{c}",
                        on_change=_on_categorized_pill_toggle,
                        args=(i, c, language, all_exp, all_grouped),
                    )
            else:
                st.pills(
                    L_("Skills"),
                    current_skills,
                    selection_mode="multi",
                    key=f"skills-{language}-{i}",
                    on_change=_on_pill_toggle,
                    args=(i, language, all_exp),
                )


# ---------------------------------------------------------------------------
# Page renderer
# ---------------------------------------------------------------------------


@st.fragment
def _render_download(language, L_):
    """Fragment for compact toggle + download — isolated so toggling is instant."""
    st.toggle(L_("Compact CV (1-2 pages)"), value=True, key="compact_cv")
    compact = st.session_state.get("compact_cv", True)
    download_bytes = _generate_download_bytes(language, compact)
    st.download_button(
        label=L_("📄 Download CV as .docx file (word)"),
        data=download_bytes,
        file_name=L_("Kriminetskii_Lead_Backend_2026_CV.docx"),
        mime="application/octet-stream",
    )
    # Pre-warm the OTHER compact variant so the next toggle is instant
    _prewarm_download(language, not compact)


def _render_page():
    """Main page rendering logic."""
    language = st.session_state.get("language", "ENGLISH")
    locale_code = language[:3]
    L_ = get_text(locale_code)

    resume_page = _load_resume(language)

    current_dir = Path(__file__).parent
    css_file = current_dir / "styles" / "main.css"
    profile_pic_path = current_dir.parent / "static" / "me.jpg"

    with open(css_file) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

    profile_pic = Image.open(profile_pic_path)

    # --- Header ---
    col1, col2 = st.columns(2)
    with col1:
        st.image(profile_pic, width=330)
        lang_col, _ = st.columns(2)
        with lang_col:
            st.button("русский/english", key="lang_ru", on_click=_switch_language)

    with col2:
        st.title(resume_page.name)
        st.write(resume_page.expected_position)
        _render_download(language, L_)
        st.write("📫", resume_page.email)
        if resume_page.tel:
            tel_e164 = phonenumbers.format_number(
                phonenumbers.parse(resume_page.tel, None),
                phonenumbers.PhoneNumberFormat.INTERNATIONAL,
            )
            st.markdown(
                f'☎️ <a href="tel:{resume_page.tel}">{tel_e164}</a>',
                unsafe_allow_html=True,
            )

    # --- Contacts row ---
    cols = st.columns(len(resume_page.contacts))
    for i, contact in enumerate(resume_page.contacts):
        cols[i].write(contact.to_markdown())

    st.write("---")

    # --- Experience (own fragment for fast skill-toggle reruns) ---
    _render_experience(resume_page, language, L_)

    # --- Technical Skills (disabled — kept for future use) ---
    # categorized = resume_page.all_skills_categorized
    # if categorized:
    #     st.markdown(L_("#### Technical Skills"))
    #     for category, skills in categorized.items():
    #         st.markdown(f"**{category}:** {', '.join(skills)}")

    # --- Education ---
    st.markdown(L_("#### Education"))
    for edu in resume_page.edu:
        with st.container(height=None, border=True):
            col_logo, col_text, _, _ = st.columns(4, gap="small")
            with col_logo:
                if edu.icon:
                    img_bytes = get_image_from_cache(edu.icon)
                    if img_bytes:
                        st.image(img_bytes, width=150, clamp=True, caption=f"{edu.website}")
                    else:
                        _ensure_image_downloaded(edu.icon)
            with col_text:
                st.write(edu.degree)
                st.write(f"{edu.year_start} - {edu.year_end}")
                st.write(edu.university)
                st.write(edu.programme)

    # Pre-warm the OTHER language's resume + downloads in background
    other_lang = "RUSSIAN" if language == "ENGLISH" else "ENGLISH"
    _prewarm_resume(other_lang)
    _prewarm_download(other_lang, True)
    _prewarm_download(other_lang, False)


# ---------------------------------------------------------------------------
# Entry point — called by Streamlit's navigation system
# ---------------------------------------------------------------------------

_render_page()
