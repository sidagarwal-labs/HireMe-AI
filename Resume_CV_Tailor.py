from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from typing import Any

import streamlit as st

REPO_ROOT = Path(__file__).resolve().parent
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
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=Source+Serif+4:wght@400;600&display=swap');

        .stApp {
            background:
                radial-gradient(circle at top left, rgba(214, 233, 255, 0.9), transparent 30%),
                linear-gradient(180deg, #f7f3eb 0%, #f2efe7 100%);
        }

        h1, h2, h3 {
            font-family: "Space Grotesk", sans-serif;
            letter-spacing: -0.03em;
        }

        p, li, label, .stMarkdown, .stTextInput, .stTextArea {
            font-family: "Source Serif 4", serif;
        }

        .hero-card, .panel-card {
            background: rgba(255, 252, 246, 0.88);
            border: 1px solid rgba(53, 71, 92, 0.12);
            border-radius: 22px;
            box-shadow: 0 18px 50px rgba(53, 71, 92, 0.08);
            padding: 1.25rem 1.35rem;
        }

        .hero-title {
            font-size: 3rem;
            line-height: 0.95;
            margin-bottom: 0.5rem;
        }

        .hero-kicker {
            font-family: "Space Grotesk", sans-serif;
            font-size: 0.9rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: #9d5c34;
            margin-bottom: 0.35rem;
        }

        .muted-note {
            color: #5e6773;
            font-size: 0.96rem;
        }

        .stButton > button, .stDownloadButton > button {
            background: linear-gradient(135deg, #203a4d 0%, #355e74 100%);
            color: #fffaf0;
            border: 0;
            border-radius: 999px;
            padding: 0.7rem 1.2rem;
            font-family: "Space Grotesk", sans-serif;
            font-weight: 700;
        }

        .stTextInput input, .stTextArea textarea {
            background: rgba(255, 255, 255, 0.92);
            border-radius: 16px;
        }

        div[data-testid="stFileUploader"] {
            background: rgba(255, 252, 246, 0.88);
            border: 1px dashed rgba(53, 71, 92, 0.25);
            border-radius: 18px;
            padding: 0.8rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _init_session_state() -> None:
    defaults = {
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
        "manual_name": "",
        "manual_email": "",
        "manual_phone": "",
        "manual_website": "",
        "manual_summary": "",
        "manual_technical_skills": "",
        "manual_tools_skills": "",
        "manual_soft_skills": "",
        "manual_work_title": "",
        "manual_work_company": "",
        "manual_work_start": "",
        "manual_work_end": "",
        "manual_work_bullets": "",
        "manual_education_degree": "",
        "manual_education_school": "",
        "manual_education_start": "",
        "manual_education_end": "",
        "manual_education_details": "",
        "manual_project_name": "",
        "manual_project_bullets": "",
        "manual_certifications": "",
        "manual_awards": "",
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


def _build_manual_candidate_profile() -> dict[str, Any]:
    work_experience = []
    if st.session_state.manual_work_title.strip() or st.session_state.manual_work_company.strip():
        work_experience.append(
            {
                "job_title": st.session_state.manual_work_title.strip(),
                "company": st.session_state.manual_work_company.strip(),
                "start_date": st.session_state.manual_work_start.strip(),
                "end_date": st.session_state.manual_work_end.strip(),
                "bullets": _split_lines(st.session_state.manual_work_bullets),
            }
        )

    education = []
    if st.session_state.manual_education_degree.strip() or st.session_state.manual_education_school.strip():
        education.append(
            {
                "degree": st.session_state.manual_education_degree.strip(),
                "school": st.session_state.manual_education_school.strip(),
                "start_date": st.session_state.manual_education_start.strip(),
                "end_date": st.session_state.manual_education_end.strip(),
                "details": _split_lines(st.session_state.manual_education_details),
            }
        )

    projects = []
    if st.session_state.manual_project_name.strip():
        projects.append(
            {
                "project_name": st.session_state.manual_project_name.strip(),
                "bullets": _split_lines(st.session_state.manual_project_bullets),
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
        <div class="hero-card">
            <div class="hero-kicker">Career Documents, Tailored Fast</div>
            <div class="hero-title">HireMe.AI</div>
            <p class="muted-note">
                Upload a resume, drop in a target job description, and generate a tailored resume
                plus cover letter from one workflow.
            </p>
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
        st.markdown("### Workflow")
        st.markdown("1. Upload a resume or fill in your profile")
        st.markdown("2. Parse the resume or save the manual profile")
        st.markdown("3. Add the target job")
        st.markdown("4. Generate tailored documents")
        st.markdown("---")
        st.markdown("### Supported Files")
        st.caption(".txt, .md, .docx, .pdf, .png, .jpg, .jpeg, .webp")

    intake_col, status_col = st.columns([1.5, 0.9], gap="large")

    with intake_col:
        st.markdown('<div class="panel-card">', unsafe_allow_html=True)
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
            work_meta_col, work_dates_col = st.columns(2)
            with work_meta_col:
                st.text_input("Role title", key="manual_work_title")
                st.text_input("Company", key="manual_work_company")
            with work_dates_col:
                st.text_input("Start date", key="manual_work_start")
                st.text_input("End date", key="manual_work_end")
            st.text_area("Work bullets", key="manual_work_bullets", height=110)

            st.markdown("#### Education")
            edu_meta_col, edu_dates_col = st.columns(2)
            with edu_meta_col:
                st.text_input("Degree", key="manual_education_degree")
                st.text_input("School", key="manual_education_school")
            with edu_dates_col:
                st.text_input("Education start", key="manual_education_start")
                st.text_input("Education end", key="manual_education_end")
            st.text_area("Education details", key="manual_education_details", height=90)

            st.markdown("#### Projects And Extras")
            project_col, extras_col = st.columns(2)
            with project_col:
                st.text_input("Project name", key="manual_project_name")
                st.text_area("Project bullets", key="manual_project_bullets", height=90)
            with extras_col:
                st.text_area("Certifications", key="manual_certifications", height=90)
                st.text_area("Awards", key="manual_awards", height=90)
                st.caption("Awards format: `Title | Year | Description`, one per line.")

            manual_profile_clicked = st.button("Save Manual Profile")

        st.text_input("Job title", key="job_title_input", on_change=_sync_job_inputs_to_state)
        st.text_input("Company name", key="company_name_input", on_change=_sync_job_inputs_to_state)
        st.text_area(
            "Job description",
            height=250,
            key="job_description_input",
            on_change=_sync_job_inputs_to_state,
        )
        generate_clicked = st.button("Generate Documents")
        st.markdown("</div>", unsafe_allow_html=True)

    with status_col:
        st.markdown('<div class="panel-card">', unsafe_allow_html=True)
        st.markdown("### Session Status")
        st.metric(
            "Profile Source",
            "Upload" if st.session_state.intake_mode == "Upload Resume" else "Manual",
        )
        st.metric("Resume Loaded", "Yes" if st.session_state.resume_name else "No")
        st.metric("Job Title", st.session_state.job_title or "Not set")
        st.metric("Profile Ready", "Ready" if st.session_state.candidate_data else "Waiting")
        st.metric(
            "Outputs",
            "Ready" if st.session_state.resume_md or st.session_state.cover_letter_md else "Not generated",
        )
        st.markdown("</div>", unsafe_allow_html=True)

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
            st.markdown('<div class="panel-card">', unsafe_allow_html=True)
            st.json(st.session_state.candidate_data)
            st.markdown("</div>", unsafe_allow_html=True)

        with resume_tab:
            st.markdown('<div class="panel-card">', unsafe_allow_html=True)
            if st.session_state.resume_md:
                st.markdown(st.session_state.resume_md)
                st.download_button(
                    "Download Resume Markdown",
                    st.session_state.resume_md,
                    file_name="resume_output.md",
                )
            else:
                st.info("Generate documents to see the tailored resume.")
            st.markdown("</div>", unsafe_allow_html=True)

        with cover_tab:
            st.markdown('<div class="panel-card">', unsafe_allow_html=True)
            if st.session_state.cover_letter_md:
                st.markdown(st.session_state.cover_letter_md)
                st.download_button(
                    "Download Cover Letter Markdown",
                    st.session_state.cover_letter_md,
                    file_name="cover_letter_output.md",
                )
            else:
                st.info("Generate documents to see the tailored cover letter.")
            st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
