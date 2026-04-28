from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from typing import Any

import streamlit as st

REPO_ROOT = Path(__file__).resolve().parent


@st.cache_data(show_spinner=False)
def _to_docx_bytes(markdown_text: str) -> bytes:
    import pypandoc
    try:
        pypandoc.get_pandoc_version()
    except OSError:
        # pandoc binary not on PATH — download it once (Streamlit Cloud
        # installs it via packages.txt; this fallback covers other hosts)
        pypandoc.download_pandoc()
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        pypandoc.convert_text(markdown_text, "docx", format="md", outputfile=tmp_path)
        return Path(tmp_path).read_bytes()
    finally:
        try:
            Path(tmp_path).unlink()
        except OSError:
            pass
PROJECT_DIR = REPO_ROOT / "HireMe.AI-V1"
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from streamlit_env import load_runtime_secrets
from doc_parser import parse_resume_file
from service import generate_documents


def _inject_styles() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Space+Grotesk:wght@600;700&display=swap');

        /* ── Base ─────────────────────────────────────────────── */
        .stApp { background: #f8fafc; }

        /* ── Typography ───────────────────────────────────────── */
        h1, h2, h3, h4 {
            font-family: "Space Grotesk", sans-serif;
            letter-spacing: -0.02em;
            color: #0f172a;
        }
        p, li, label, .stMarkdown, .stCaption {
            font-family: "Inter", sans-serif;
        }

        /* ── App header ───────────────────────────────────────── */
        .app-header {
            display: flex;
            align-items: baseline;
            gap: 0.75rem;
            background: linear-gradient(135deg, rgba(79, 70, 229, 0.06) 0%, rgba(248, 250, 252, 0) 60%);
            border: 1px solid rgba(79, 70, 229, 0.14);
            border-radius: 14px;
            padding: 1.1rem 1.4rem;
            margin-bottom: 1.25rem;
        }
        .app-name {
            font-family: "Space Grotesk", sans-serif;
            font-size: 2rem;
            font-weight: 700;
            color: #0f172a;
            letter-spacing: -0.03em;
            line-height: 1;
        }
        .app-tagline {
            font-family: "Inter", sans-serif;
            font-size: 0.875rem;
            color: #94a3b8;
        }

        /* ── Cards ────────────────────────────────────────────── */
        .app-card {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-top: 2px solid #4f46e5;
            border-radius: 12px;
            box-shadow: 0 1px 4px rgba(15, 23, 42, 0.05);
            padding: 1.5rem;
            margin-bottom: 0.5rem;
        }
        .section-label {
            font-family: "Inter", sans-serif;
            font-size: 0.68rem;
            font-weight: 600;
            letter-spacing: 0.09em;
            text-transform: uppercase;
            color: #6366f1;
            margin-bottom: 0.6rem;
            margin-top: 0;
        }

        /* ── Buttons ──────────────────────────────────────────── */
        .stButton > button, .stDownloadButton > button {
            background: #4f46e5;
            color: #ffffff;
            border: none;
            border-radius: 8px;
            padding: 0.55rem 1.1rem;
            font-family: "Inter", sans-serif;
            font-weight: 600;
            font-size: 0.875rem;
            box-shadow: none;
            transition: background 0.15s;
        }
        .stButton > button:hover, .stDownloadButton > button:hover {
            background: #4338ca;
            border: none;
        }

        /* ── Inputs ───────────────────────────────────────────── */
        .stTextInput input, .stTextArea textarea {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            font-family: "Inter", sans-serif;
            color: #0f172a;
            font-size: 0.9rem;
        }
        .stTextInput input:focus, .stTextArea textarea:focus {
            border-color: #4f46e5;
            box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.08);
        }

        /* ── File uploader ────────────────────────────────────── */
        div[data-testid="stFileUploader"] {
            background: #f8fafc;
            border: 1.5px dashed #cbd5e1;
            border-radius: 10px;
            padding: 0.75rem;
        }

        /* ── Sidebar ──────────────────────────────────────────── */
        section[data-testid="stSidebar"] {
            background: #ffffff;
            border-right: 1px solid #e2e8f0;
        }
        section[data-testid="stSidebar"] .stMarkdown p {
            font-family: "Inter", sans-serif;
            font-size: 0.85rem;
            color: #475569;
        }

        /* ── Tabs ─────────────────────────────────────────────── */
        .stTabs [data-baseweb="tab"] {
            font-family: "Inter", sans-serif;
            font-size: 0.875rem;
            font-weight: 500;
            color: #64748b;
        }
        .stTabs [data-baseweb="tab-highlight"] { background-color: #4f46e5; }
        .stTabs [aria-selected="true"] { color: #0f172a; }

        /* ── Divider ──────────────────────────────────────────── */
        hr { border-color: #e2e8f0; }

        /* ── Radio ────────────────────────────────────────────── */
        .stRadio > div { gap: 0.5rem; }
        .stRadio label { font-family: "Inter", sans-serif; font-size: 0.9rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _init_session_state() -> None:
    defaults: dict[str, Any] = {
        "intake_mode": "Upload Resume",
        "resume_bytes": None,
        "resume_name": "",
        "job_title": "",
        "company_name": "",
        "job_description": "",
        "job_title_input": "",
        "company_name_input": "",
        "job_description_input": "",
        "job_builder_prefill_pending": False,
        "candidate_data": None,
        "resume_md": "",
        "cover_letter_md": "",
        "job_search_query": "find me data analyst jobs in New York",
        "job_search_results": "",
        "job_search_ranked": [],
        "job_search_raw_count": 0,
        "job_search_top_n": 10,
        "creativity_level": 0.3,
        "manual_name": "",
        "manual_email": "",
        "manual_phone": "",
        "manual_website": "",
        "manual_summary": "",
        "manual_technical_skills": "",
        "manual_tools_skills": "",
        "manual_soft_skills": "",
        "manual_certifications": "",
        "manual_awards": "",
        "manual_work_entries": [{"title": "", "company": "", "start": "", "end": "", "bullets": ""}],
        "manual_education_entries": [{"degree": "", "school": "", "start": "", "end": "", "details": ""}],
        "manual_project_entries": [{"name": "", "bullets": ""}],
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _sync_job_inputs_to_state() -> None:
    st.session_state.job_title = st.session_state.job_title_input
    st.session_state.company_name = st.session_state.company_name_input
    st.session_state.job_description = st.session_state.job_description_input


def _split_lines(value: str) -> list[str]:
    return [line.strip(" -\t") for line in value.splitlines() if line.strip(" -\t")]


# ── Entry list helpers ────────────────────────────────────────────

_WORK_FIELDS = ["title", "company", "start", "end", "bullets"]
_EDU_FIELDS = ["degree", "school", "start", "end", "details"]
_PROJ_FIELDS = ["name", "bullets"]

_EMPTY_WORK = lambda: {"title": "", "company": "", "start": "", "end": "", "bullets": ""}
_EMPTY_EDU = lambda: {"degree": "", "school": "", "start": "", "end": "", "details": ""}
_EMPTY_PROJ = lambda: {"name": "", "bullets": ""}


def _sync_widgets_to_entries() -> None:
    for i, entry in enumerate(st.session_state.manual_work_entries):
        for field in _WORK_FIELDS:
            entry[field] = st.session_state.get(f"wexp_{i}_{field}", entry.get(field, ""))
    for i, entry in enumerate(st.session_state.manual_education_entries):
        for field in _EDU_FIELDS:
            entry[field] = st.session_state.get(f"edu_{i}_{field}", entry.get(field, ""))
    for i, entry in enumerate(st.session_state.manual_project_entries):
        for field in _PROJ_FIELDS:
            entry[field] = st.session_state.get(f"proj_{i}_{field}", entry.get(field, ""))


def _restore_widget_keys() -> None:
    for i, entry in enumerate(st.session_state.manual_work_entries):
        for field in _WORK_FIELDS:
            key = f"wexp_{i}_{field}"
            if key not in st.session_state:
                st.session_state[key] = entry.get(field, "")
    for i, entry in enumerate(st.session_state.manual_education_entries):
        for field in _EDU_FIELDS:
            key = f"edu_{i}_{field}"
            if key not in st.session_state:
                st.session_state[key] = entry.get(field, "")
    for i, entry in enumerate(st.session_state.manual_project_entries):
        for field in _PROJ_FIELDS:
            key = f"proj_{i}_{field}"
            if key not in st.session_state:
                st.session_state[key] = entry.get(field, "")


def _clear_indexed_widget_keys(prefix: str, fields: list[str], count: int) -> None:
    for i in range(count):
        for field in fields:
            st.session_state.pop(f"{prefix}_{i}_{field}", None)


def _render_work_entries() -> None:
    entries = st.session_state.manual_work_entries
    n = len(entries)
    for i in range(n):
        if n > 1:
            st.markdown(f"**Experience {i + 1}**")
        meta_col, dates_col = st.columns(2)
        with meta_col:
            st.text_input("Role title", key=f"wexp_{i}_title")
            st.text_input("Company", key=f"wexp_{i}_company")
        with dates_col:
            st.text_input("Start date", key=f"wexp_{i}_start")
            st.text_input("End date", key=f"wexp_{i}_end")
        st.text_area("Work bullets", key=f"wexp_{i}_bullets", height=110)
        if n > 1:
            if st.button("Remove this experience", key=f"remove_work_{i}"):
                _sync_widgets_to_entries()
                _clear_indexed_widget_keys("wexp", _WORK_FIELDS, n)
                st.session_state.manual_work_entries.pop(i)
                st.rerun()
        if i < n - 1:
            st.divider()

    if st.button("+ Add Work Experience"):
        _sync_widgets_to_entries()
        st.session_state.manual_work_entries.append(_EMPTY_WORK())
        st.rerun()


def _render_education_entries() -> None:
    entries = st.session_state.manual_education_entries
    n = len(entries)
    for i in range(n):
        if n > 1:
            st.markdown(f"**Education {i + 1}**")
        meta_col, dates_col = st.columns(2)
        with meta_col:
            st.text_input("Degree", key=f"edu_{i}_degree")
            st.text_input("School", key=f"edu_{i}_school")
        with dates_col:
            st.text_input("Education start", key=f"edu_{i}_start")
            st.text_input("Education end", key=f"edu_{i}_end")
        st.text_area("Education details", key=f"edu_{i}_details", height=90)
        if n > 1:
            if st.button("Remove this education", key=f"remove_edu_{i}"):
                _sync_widgets_to_entries()
                _clear_indexed_widget_keys("edu", _EDU_FIELDS, n)
                st.session_state.manual_education_entries.pop(i)
                st.rerun()
        if i < n - 1:
            st.divider()

    if st.button("+ Add Education"):
        _sync_widgets_to_entries()
        st.session_state.manual_education_entries.append(_EMPTY_EDU())
        st.rerun()


def _render_project_entries() -> None:
    entries = st.session_state.manual_project_entries
    n = len(entries)
    for i in range(n):
        if n > 1:
            st.markdown(f"**Project {i + 1}**")
        st.text_input("Project name", key=f"proj_{i}_name")
        st.text_area("Project bullets", key=f"proj_{i}_bullets", height=90)
        if n > 1:
            if st.button("Remove this project", key=f"remove_proj_{i}"):
                _sync_widgets_to_entries()
                _clear_indexed_widget_keys("proj", _PROJ_FIELDS, n)
                st.session_state.manual_project_entries.pop(i)
                st.rerun()
        if i < n - 1:
            st.divider()

    if st.button("+ Add Project"):
        _sync_widgets_to_entries()
        st.session_state.manual_project_entries.append(_EMPTY_PROJ())
        st.rerun()


def _build_manual_candidate_profile() -> dict[str, Any]:
    _sync_widgets_to_entries()

    work_experience = []
    for entry in st.session_state.manual_work_entries:
        title = entry.get("title", "").strip()
        company = entry.get("company", "").strip()
        if title or company:
            work_experience.append(
                {
                    "job_title": title,
                    "company": company,
                    "start_date": entry.get("start", "").strip(),
                    "end_date": entry.get("end", "").strip(),
                    "bullets": _split_lines(entry.get("bullets", "")),
                }
            )

    education = []
    for entry in st.session_state.manual_education_entries:
        degree = entry.get("degree", "").strip()
        school = entry.get("school", "").strip()
        if degree or school:
            education.append(
                {
                    "degree": degree,
                    "school": school,
                    "start_date": entry.get("start", "").strip(),
                    "end_date": entry.get("end", "").strip(),
                    "details": _split_lines(entry.get("details", "")),
                }
            )

    projects = []
    for entry in st.session_state.manual_project_entries:
        name = entry.get("name", "").strip()
        if name:
            projects.append(
                {
                    "project_name": name,
                    "bullets": _split_lines(entry.get("bullets", "")),
                }
            )

    certifications = [
        {"name": item} for item in _split_lines(st.session_state.manual_certifications)
    ]

    awards = []
    for item in _split_lines(st.session_state.manual_awards):
        parts = [part.strip() for part in item.split("|", 2)]
        title = parts[0] if parts else ""
        year = parts[1] if len(parts) > 1 else ""
        description = parts[2] if len(parts) > 2 else ""
        awards.append({"title": title, "year": year, "description": description})

    return {
        "name": st.session_state.manual_name.strip(),
        "contact": {
            "email": st.session_state.manual_email.strip(),
            "phone": st.session_state.manual_phone.strip(),
            "website": st.session_state.manual_website.strip(),
        },
        "summary": st.session_state.manual_summary.strip(),
        "work_experience": work_experience,
        "education": education,
        "skills": {
            "technical": _split_lines(st.session_state.manual_technical_skills),
            "tools": _split_lines(st.session_state.manual_tools_skills),
            "soft_skills": _split_lines(st.session_state.manual_soft_skills),
        },
        "projects": projects,
        "certifications": certifications,
        "awards_and_achievements": awards,
        "cover_letter_preferences": {
            "recipient_name": "Hiring Manager",
            "opening_style": "professional",
            "tone": "confident",
            "length": "medium",
        },
    }


def _render_sidebar_steps() -> None:
    candidate_ready = st.session_state.candidate_data is not None
    job_ready = bool(st.session_state.get("job_description", "").strip())
    outputs_ready = bool(st.session_state.get("resume_md") or st.session_state.get("cover_letter_md"))

    steps = [
        ("Add your profile", candidate_ready),
        ("Add target job", job_ready),
        ("Generate documents", outputs_ready),
    ]

    rows = ""
    for i, (label, done) in enumerate(steps, 1):
        if done:
            circle_bg = "#4f46e5"
            circle_fg = "#ffffff"
            circle_border = "none"
        else:
            circle_bg = "#ffffff"
            circle_fg = "#6366f1"
            circle_border = "2px solid #e0e7ff"
        icon = "✓" if done else str(i)
        label_color = "#0f172a" if done else "#94a3b8"
        label_weight = "500" if done else "400"
        rows += f"""
        <div style="display:flex;align-items:center;gap:10px;padding:6px 0;">
            <div style="width:22px;height:22px;border-radius:50%;background:{circle_bg};
                        color:{circle_fg};border:{circle_border};
                        display:flex;align-items:center;justify-content:center;
                        font-size:11px;font-weight:700;flex-shrink:0;font-family:Inter,sans-serif;">
                {icon}
            </div>
            <span style="font-family:Inter,sans-serif;font-size:13px;
                         color:{label_color};font-weight:{label_weight};">{label}</span>
        </div>"""

    st.markdown(f'<div style="padding:2px 0">{rows}</div>', unsafe_allow_html=True)


def _render_status_card() -> None:
    source = "Upload" if st.session_state.intake_mode == "Upload Resume" else "Manual"
    loaded = "Yes" if st.session_state.resume_name else "No"
    job_title = st.session_state.job_title or "—"
    profile_ready = st.session_state.candidate_data is not None
    outputs_ready = bool(st.session_state.resume_md or st.session_state.cover_letter_md)

    def _row(label: str, value: str, highlight: bool = False) -> str:
        color = "#4f46e5" if highlight else "#0f172a"
        return f"""
        <div style="display:flex;justify-content:space-between;align-items:center;
                    padding:9px 0;border-bottom:1px solid #f8fafc;">
            <span style="font-family:Inter,sans-serif;font-size:0.82rem;color:#64748b;">{label}</span>
            <span style="font-family:Inter,sans-serif;font-size:0.82rem;font-weight:600;color:{color};">{value}</span>
        </div>"""

    rows = (
        _row("Profile source", source)
        + _row("Resume loaded", loaded)
        + _row("Job title", job_title)
        + _row("Profile", "✓ Ready" if profile_ready else "Waiting", highlight=profile_ready)
        + _row("Documents", "✓ Ready" if outputs_ready else "Not generated", highlight=outputs_ready)
    )

    st.markdown(
        f"""
        <div class="app-card">
            <p class="section-label">Session Status</p>
            {rows}
        </div>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    load_runtime_secrets(REPO_ROOT)
    _init_session_state()

    if st.session_state.job_builder_prefill_pending:
        st.session_state.job_title_input = st.session_state.job_title
        st.session_state.company_name_input = st.session_state.company_name
        st.session_state.job_description_input = st.session_state.job_description
        st.session_state.job_builder_prefill_pending = False

    st.set_page_config(page_title="HireMe.AI", layout="wide")
    _inject_styles()

    st.markdown(
        """
        <div class="app-header">
            <span class="app-name">HireMe<span style="color:#4f46e5">.AI</span></span>
            <span class="app-tagline">Resume &amp; cover letter, tailored to your target role.</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not os.getenv("OPENAI_API_KEY"):
        st.error(
            "OPENAI_API_KEY is missing. Add it to `.env` locally or to Streamlit app secrets before running."
        )
        st.stop()

    with st.sidebar:
        st.markdown(
            '<div style="padding:0.75rem 0 1rem;">'
            '<span style="font-family:\'Space Grotesk\',sans-serif;font-size:1.2rem;'
            'font-weight:700;color:#0f172a;letter-spacing:-0.02em;">'
            'HireMe<span style="color:#4f46e5">.AI</span>'
            '</span></div>',
            unsafe_allow_html=True,
        )
        st.markdown('<p class="section-label">Workflow</p>', unsafe_allow_html=True)
        _render_sidebar_steps()
        st.divider()
        st.markdown('<p class="section-label">Supported Formats</p>', unsafe_allow_html=True)
        st.caption(".txt · .md · .docx · .pdf · .png · .jpg · .webp")

    intake_col, status_col = st.columns([1.5, 0.9], gap="large")

    with intake_col:
        st.markdown('<div class="app-card">', unsafe_allow_html=True)
        st.radio(
            "Profile input method",
            ["Upload Resume", "Fill In Profile"],
            key="intake_mode",
            horizontal=True,
        )

        parse_clicked = False
        manual_profile_clicked = False

        if st.session_state.intake_mode == "Upload Resume":
            uploaded_resume = st.file_uploader(
                "Upload a resume",
                type=["txt", "md", "docx", "pdf", "png", "jpg", "jpeg", "webp"],
            )
            if uploaded_resume is not None:
                new_bytes = uploaded_resume.getvalue()
                new_name = uploaded_resume.name
                if (
                    st.session_state.resume_bytes != new_bytes
                    or st.session_state.resume_name != new_name
                ):
                    st.session_state.resume_bytes = new_bytes
                    st.session_state.resume_name = new_name
                    st.session_state.candidate_data = None
                    st.session_state.resume_md = ""
                    st.session_state.cover_letter_md = ""
            elif st.session_state.resume_name:
                st.caption(f"Using saved upload: {st.session_state.resume_name}")

            parse_clicked = st.button("Parse Resume")
        else:
            _sync_widgets_to_entries()
            _restore_widget_keys()

            contact_col, links_col = st.columns(2)
            with contact_col:
                st.text_input("Full name", key="manual_name")
                st.text_input("Email", key="manual_email")
                st.text_input("Phone", key="manual_phone")
            with links_col:
                st.text_input("Website / LinkedIn", key="manual_website")
                st.text_area("Professional summary", key="manual_summary", height=108)

            skills_col, tools_col, soft_col = st.columns(3)
            with skills_col:
                st.text_area("Technical skills", key="manual_technical_skills", height=120)
            with tools_col:
                st.text_area("Tools", key="manual_tools_skills", height=120)
            with soft_col:
                st.text_area("Soft skills", key="manual_soft_skills", height=120)

            st.markdown("#### Work Experience")
            _render_work_entries()

            st.markdown("#### Education")
            _render_education_entries()

            st.markdown("#### Projects And Extras")
            project_col, extras_col = st.columns(2)
            with project_col:
                _render_project_entries()
            with extras_col:
                st.text_area("Certifications", key="manual_certifications", height=90)
                st.text_area("Awards", key="manual_awards", height=90)
                st.caption("Format: `Title | Year | Description`, one per line.")

            manual_profile_clicked = st.button("Save Manual Profile")

        st.divider()
        st.markdown('<p class="section-label">Target Job</p>', unsafe_allow_html=True)
        st.text_input("Job title", key="job_title_input", on_change=_sync_job_inputs_to_state)
        st.text_input("Company name", key="company_name_input", on_change=_sync_job_inputs_to_state)
        st.text_area(
            "Job description",
            height=220,
            key="job_description_input",
            on_change=_sync_job_inputs_to_state,
        )

        st.divider()
        st.markdown('<p class="section-label">Writing Style</p>', unsafe_allow_html=True)
        c_left, c_slider, c_right = st.columns([1, 4, 1])
        with c_left:
            st.caption("Precise")
        with c_slider:
            st.slider(
                "Creativity",
                min_value=0.0,
                max_value=1.0,
                step=0.1,
                key="creativity_level",
                label_visibility="collapsed",
                help="Low = consistent, close to your exact words. High = more varied phrasing.",
            )
        with c_right:
            st.caption("Creative")

        generate_clicked = st.button("Generate Documents")
        st.markdown("</div>", unsafe_allow_html=True)

    with status_col:
        _render_status_card()

    if manual_profile_clicked:
        _sync_job_inputs_to_state()
        if not st.session_state.manual_name.strip():
            st.error("Please enter your name before saving the manual profile.")
            st.stop()

        st.session_state.candidate_data = _build_manual_candidate_profile()
        st.session_state.resume_md = ""
        st.session_state.cover_letter_md = ""
        st.success("Manual profile saved. You can now generate documents.")

    if parse_clicked:
        _sync_job_inputs_to_state()
        if st.session_state.resume_bytes is None or not st.session_state.resume_name:
            st.error("Please upload a resume file.")
            st.stop()

        progress_bar = st.progress(0, text="Preparing resume for parsing...")
        suffix = Path(st.session_state.resume_name).suffix.lower()
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
            tmp_file.write(st.session_state.resume_bytes)
            temp_resume_path = Path(tmp_file.name)

        try:
            progress_bar.progress(25, text="Resume uploaded. Extracting content...")
            with st.spinner("Parsing resume..."):
                progress_bar.progress(60, text="Sending resume to parser...")
                st.session_state.candidate_data = parse_resume_file(temp_resume_path)
                st.session_state.resume_md = ""
                st.session_state.cover_letter_md = ""
            progress_bar.progress(100, text="Resume parsing complete.")
            st.rerun()
        except Exception as exc:
            st.error(str(exc))
        finally:
            try:
                temp_resume_path.unlink()
            except OSError:
                pass
            progress_bar.empty()

    if generate_clicked:
        _sync_job_inputs_to_state()
        if st.session_state.candidate_data is None:
            st.error("Please parse a resume or save the manual profile first.")
            st.stop()
        if not st.session_state.job_description.strip():
            st.error("Please paste a job description.")
            st.stop()

        progress_bar = st.progress(0, text="Preparing document generation...")
        try:
            progress_bar.progress(20, text="Building prompts from your profile and job description...")
            with st.spinner("Generating documents..."):
                progress_bar.progress(55, text="Generating resume and cover letter...")
                outputs = generate_documents(
                    candidate_data=st.session_state.candidate_data,
                    job_data={
                        "job_title": st.session_state.job_title,
                        "company_name": st.session_state.company_name,
                        "job_description": st.session_state.job_description,
                    },
                    resume_template_path=PROJECT_DIR / "Templates" / "resume_template.md",
                    cover_template_path=PROJECT_DIR / "Templates" / "cover_letter_template.md",
                    temperature=st.session_state.creativity_level,
                )

            progress_bar.progress(90, text="Formatting generated documents...")
            st.session_state.resume_md = outputs["resume_md"]
            st.session_state.cover_letter_md = outputs["cover_letter_md"]
            progress_bar.progress(100, text="Document generation complete.")
            st.rerun()
        except Exception as exc:
            st.error(str(exc))
        finally:
            progress_bar.empty()

    if st.session_state.candidate_data is not None:
        st.markdown("")
        parsed_tab, resume_tab, cover_tab = st.tabs(["Parsed Profile", "Resume", "Cover Letter"])

        with parsed_tab:
            st.markdown('<div class="app-card">', unsafe_allow_html=True)
            st.json(st.session_state.candidate_data)
            st.markdown("</div>", unsafe_allow_html=True)

        with resume_tab:
            st.markdown('<div class="app-card">', unsafe_allow_html=True)
            if st.session_state.resume_md:
                st.markdown(st.session_state.resume_md)
                dl_col1, dl_col2 = st.columns(2)
                with dl_col1:
                    st.download_button(
                        "Download Resume (.md)",
                        st.session_state.resume_md,
                        file_name="resume_output.md",
                        use_container_width=True,
                    )
                with dl_col2:
                    try:
                        resume_docx = _to_docx_bytes(st.session_state.resume_md)
                        st.download_button(
                            "Download Resume (.docx)",
                            resume_docx,
                            file_name="resume_output.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            use_container_width=True,
                        )
                    except Exception:
                        st.caption("Word export unavailable — pandoc could not be initialized.")
            else:
                st.info("Generate documents to see the tailored resume.")
            st.markdown("</div>", unsafe_allow_html=True)

        with cover_tab:
            st.markdown('<div class="app-card">', unsafe_allow_html=True)
            if st.session_state.cover_letter_md:
                st.markdown(st.session_state.cover_letter_md)
                dl_col1, dl_col2 = st.columns(2)
                with dl_col1:
                    st.download_button(
                        "Download Cover Letter (.md)",
                        st.session_state.cover_letter_md,
                        file_name="cover_letter_output.md",
                        use_container_width=True,
                    )
                with dl_col2:
                    try:
                        cover_docx = _to_docx_bytes(st.session_state.cover_letter_md)
                        st.download_button(
                            "Download Cover Letter (.docx)",
                            cover_docx,
                            file_name="cover_letter_output.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            use_container_width=True,
                        )
                    except Exception:
                        st.caption("Word export unavailable — pandoc could not be initialized.")
            else:
                st.info("Generate documents to see the tailored cover letter.")
            st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
