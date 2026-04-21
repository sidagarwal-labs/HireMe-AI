from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

REPO_ROOT = Path(__file__).resolve().parents[1]
SEARCH_TOOL_DIR = REPO_ROOT / "Random-Testing" / "Search-Tool"
PROJECT_DIR = REPO_ROOT / "HireMe.AI-V1"

for p in (SEARCH_TOOL_DIR, PROJECT_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from streamlit_env import load_runtime_secrets

load_runtime_secrets(REPO_ROOT)

IMPORT_ERROR: Exception | None = None
search_jobs = None
rank_jobs = None

try:
    from job_search_agent import search_jobs
    from rag import rank_jobs
except Exception as exc:
    IMPORT_ERROR = exc


def _inject_styles() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=Source+Serif+4:wght@400;600&display=swap');

        .stApp {
            background:
                radial-gradient(circle at top right, rgba(255, 228, 201, 0.9), transparent 30%),
                linear-gradient(180deg, #f7f3eb 0%, #f2efe7 100%);
        }

        h1, h2, h3 {
            font-family: "Space Grotesk", sans-serif;
            letter-spacing: -0.03em;
        }

        p, li, label, .stMarkdown, .stTextArea {
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
            font-size: 2.4rem;
            line-height: 0.98;
            margin-bottom: 0.5rem;
        }

        .hero-kicker {
            font-family: "Space Grotesk", sans-serif;
            font-size: 0.88rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: #9d5c34;
            margin-bottom: 0.35rem;
        }

        .stButton > button {
            background: linear-gradient(135deg, #203a4d 0%, #355e74 100%);
            color: #fffaf0;
            border: 0;
            border-radius: 999px;
            padding: 0.7rem 1.2rem;
            font-family: "Space Grotesk", sans-serif;
            font-weight: 700;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _init_session_state() -> None:
    defaults = {
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
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def main() -> None:
    st.set_page_config(page_title="HireMe.AI Job Search", layout="wide")
    _init_session_state()
    _inject_styles()
    st.markdown(
        """
        <div class="hero-card">
            <div class="hero-kicker">Discovery Layer</div>
            <div class="hero-title">Job Search</div>
            <p>Use the existing search agent to find roles, then move the results back into the document generator.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if IMPORT_ERROR is not None:
        st.error(f"Job search dependencies are not ready: {IMPORT_ERROR}")
        st.code("pip install python-jobspy rank-bm25 faiss-cpu")
        st.stop()

    input_col, info_col = st.columns([1.5, 0.8], gap="large")

    with input_col:
        st.markdown('<div class="panel-card">', unsafe_allow_html=True)
        query = st.text_area(
            "Search query",
            key="job_search_query",
            height=120,
        )
        top_n = st.slider(
            "Number of results to show",
            min_value=5,
            max_value=30,
            key="job_search_top_n",
        )

        if st.button("Search Jobs", type="primary"):
            if not query.strip():
                st.error("Please enter a search query.")
                st.stop()

            try:
                with st.spinner("Searching jobs..."):
                    summary, raw_jobs = search_jobs(query)
                st.session_state.job_search_results = summary
                st.session_state.job_search_raw_count = len(raw_jobs)

                if raw_jobs:
                    with st.spinner(f"Ranking {len(raw_jobs)} results..."):
                        st.session_state.job_search_ranked = rank_jobs(query, raw_jobs, top_n=top_n)
                else:
                    st.session_state.job_search_ranked = []
            except Exception as exc:
                st.error(str(exc))
        st.markdown("</div>", unsafe_allow_html=True)

    with info_col:
        st.markdown('<div class="panel-card">', unsafe_allow_html=True)
        st.markdown("### Current Session")
        st.metric("Last Query", "Ready" if st.session_state.job_search_query.strip() else "Empty")
        st.metric("Results", "Ready" if st.session_state.job_search_results else "Not fetched")
        st.metric("Main App JD", "Filled" if st.session_state.get("job_description", "").strip() else "Empty")
        st.markdown("</div>", unsafe_allow_html=True)

    ranked = st.session_state.get("job_search_ranked", [])
    if ranked:
        st.markdown('<div class="panel-card">', unsafe_allow_html=True)
        raw_count = st.session_state.get("job_search_raw_count", 0)
        st.subheader(f"Top {len(ranked)} of {raw_count} Results")

        for i, job in enumerate(ranked, 1):
            label = f"**{i}. {job.title}** — {job.company}"
            if job.source:
                label += f"  _{job.source}_"

            with st.expander(label, expanded=(i <= 3)):
                cols = st.columns([3, 1])
                with cols[0]:
                    if job.location:
                        st.markdown(f"Location: {job.location}")
                    if job.salary:
                        st.markdown(f"Salary: {job.salary}")
                with cols[1]:
                    if job.url:
                        st.link_button("View Job", job.url)

                desc = job.description
                if len(desc) > 600:
                    desc = desc[:600] + "..."
                st.markdown(desc)
                if st.button("Use In Resume Builder", key=f"use_job_{i}"):
                    st.session_state.job_title = job.title
                    st.session_state.company_name = job.company
                    st.session_state.job_description = job.description
                    st.session_state.job_title_input = job.title
                    st.session_state.company_name_input = job.company
                    st.session_state.job_description_input = job.description
                    st.session_state.job_builder_prefill_pending = True
                    st.success("Sent this job to the resume builder.")

        st.markdown("</div>", unsafe_allow_html=True)

    if st.session_state.job_search_results:
        with st.expander("Agent Summary", expanded=False):
            st.write(st.session_state.job_search_results)


if __name__ == "__main__":
    main()
