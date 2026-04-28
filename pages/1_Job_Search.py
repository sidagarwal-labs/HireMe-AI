from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

import streamlit as st
import requests

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

        /* ── Job result card ──────────────────────────────────── */
        .job-card {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 10px;
            padding: 1rem 1.25rem;
            margin-bottom: 0.6rem;
            transition: box-shadow 0.15s;
        }
        .job-card:hover { box-shadow: 0 4px 12px rgba(15, 23, 42, 0.08); }
        .job-rank {
            font-family: "Inter", sans-serif;
            font-size: 0.75rem;
            font-weight: 600;
            color: #94a3b8;
            text-transform: uppercase;
            letter-spacing: 0.06em;
        }
        .job-title {
            font-family: "Space Grotesk", sans-serif;
            font-size: 1rem;
            font-weight: 600;
            color: #0f172a;
            margin: 2px 0;
        }
        .job-meta {
            font-family: "Inter", sans-serif;
            font-size: 0.82rem;
            color: #64748b;
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

        /* ── Sidebar ──────────────────────────────────────────── */
        section[data-testid="stSidebar"] {
            background: #ffffff;
            border-right: 1px solid #e2e8f0;
        }

        /* ── Divider ──────────────────────────────────────────── */
        hr { border-color: #e2e8f0; }
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


_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
_JSON_LD_TYPES = {"jobposting", "job_posting"}


def _normalize_text(value: str) -> str:
    text = html.unescape(_TAG_RE.sub(" ", value or ""))
    return _WS_RE.sub(" ", text).strip()


def _walk_jsonld_descriptions(node: object) -> list[str]:
    matches: list[str] = []
    if isinstance(node, dict):
        node_type = str(node.get("@type", "")).replace(" ", "").lower()
        if node_type in _JSON_LD_TYPES and isinstance(node.get("description"), str):
            matches.append(node["description"])
        for value in node.values():
            matches.extend(_walk_jsonld_descriptions(value))
    elif isinstance(node, list):
        for item in node:
            matches.extend(_walk_jsonld_descriptions(item))
    return matches


def _extract_html_candidates(page_html: str) -> list[str]:
    candidates: list[str] = []

    for match in re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        page_html,
        flags=re.IGNORECASE | re.DOTALL,
    ):
        try:
            data = json.loads(match)
        except json.JSONDecodeError:
            continue
        candidates.extend(_walk_jsonld_descriptions(data))

    for match in re.findall(
        r'<meta[^>]+(?:name|property)=["\'](?:description|og:description|twitter:description)["\'][^>]+content=["\'](.*?)["\'][^>]*>',
        page_html,
        flags=re.IGNORECASE | re.DOTALL,
    ):
        candidates.append(match)

    return [_normalize_text(c) for c in candidates if _normalize_text(c)]


def _looks_more_complete(candidate: str, fallback: str) -> bool:
    if not candidate:
        return False
    if len(candidate) < max(700, len(fallback) + 150):
        return False
    return candidate != fallback


def _fetch_full_job_description(url: str, fallback: str) -> str:
    if not url:
        return fallback
    try:
        response = requests.get(
            url,
            timeout=10,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                )
            },
        )
        response.raise_for_status()
    except requests.RequestException:
        return fallback

    candidates = _extract_html_candidates(response.text)
    if not candidates:
        return fallback

    best = max(candidates, key=len)
    return best if _looks_more_complete(best, fallback) else fallback


def main() -> None:
    st.set_page_config(page_title="HireMe.AI — Job Search", layout="wide")
    _init_session_state()
    _inject_styles()

    st.markdown(
        """
        <div class="app-header">
            <span class="app-name">HireMe<span style="color:#4f46e5">.AI</span></span>
            <span class="app-tagline">Find and rank open roles, then send them to the resume builder.</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if IMPORT_ERROR is not None:
        st.error(f"Job search dependencies are not ready: {IMPORT_ERROR}")
        st.code("pip install python-jobspy rank-bm25 faiss-cpu")
        st.stop()

    search_col, status_col = st.columns([1.5, 0.8], gap="large")

    with search_col:
        st.markdown('<div class="app-card">', unsafe_allow_html=True)
        st.markdown('<p class="section-label">Search Query</p>', unsafe_allow_html=True)
        query = st.text_area(
            "Query",
            key="job_search_query",
            height=100,
            label_visibility="collapsed",
        )
        top_n = st.slider(
            "Results to show",
            min_value=5,
            max_value=30,
            key="job_search_top_n",
        )
        search_clicked = st.button("Search Jobs", type="primary")
        st.markdown("</div>", unsafe_allow_html=True)

        if search_clicked:
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

    with status_col:
        def _status_row(label: str, value: str, highlight: bool = False) -> str:
            color = "#4f46e5" if highlight else "#0f172a"
            return f"""
            <div style="display:flex;justify-content:space-between;align-items:center;
                        padding:9px 0;border-bottom:1px solid #f8fafc;">
                <span style="font-family:Inter,sans-serif;font-size:0.82rem;color:#64748b;">{label}</span>
                <span style="font-family:Inter,sans-serif;font-size:0.82rem;font-weight:600;color:{color};">{value}</span>
            </div>"""

        has_results = bool(st.session_state.job_search_results)
        jd_filled = bool(st.session_state.get("job_description", "").strip())
        raw_count = st.session_state.get("job_search_raw_count", 0)

        rows = (
            _status_row("Last query", "Set" if st.session_state.job_search_query.strip() else "—")
            + _status_row("Results fetched", str(raw_count) if raw_count else "—", highlight=has_results)
            + _status_row("Builder JD", "✓ Filled" if jd_filled else "Empty", highlight=jd_filled)
        )
        st.markdown(
            f'<div class="app-card"><p class="section-label">Search Status</p>{rows}</div>',
            unsafe_allow_html=True,
        )

    ranked = st.session_state.get("job_search_ranked", [])
    if ranked:
        raw_count = st.session_state.get("job_search_raw_count", 0)
        st.markdown(
            f'<p style="font-family:Inter,sans-serif;font-size:0.85rem;color:#64748b;margin:1rem 0 0.5rem;">'
            f'Showing top <strong style="color:#0f172a;">{len(ranked)}</strong> of '
            f'<strong style="color:#0f172a;">{raw_count}</strong> results</p>',
            unsafe_allow_html=True,
        )

        for i, job in enumerate(ranked, 1):
            source_badge = (
                f'<span style="font-size:0.72rem;font-weight:600;color:#94a3b8;'
                f'text-transform:uppercase;letter-spacing:0.05em;">{job.source}</span>'
                if job.source else ""
            )
            meta_parts = [p for p in [job.location, job.salary] if p]
            meta_str = " · ".join(meta_parts) if meta_parts else ""

            with st.expander(f"{i}. {job.title} — {job.company}", expanded=(i <= 3)):
                st.markdown(
                    f"""
                    <div style="margin-bottom:0.75rem;">
                        {source_badge}
                        {f'<p style="font-family:Inter,sans-serif;font-size:0.83rem;color:#64748b;margin:4px 0 0;">{meta_str}</p>' if meta_str else ""}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                desc = job.description
                if len(desc) > 600:
                    desc = desc[:600] + "…"
                st.markdown(
                    f'<p style="font-family:Inter,sans-serif;font-size:0.875rem;color:#374151;'
                    f'line-height:1.6;">{desc}</p>',
                    unsafe_allow_html=True,
                )

                btn_col, link_col = st.columns([2, 1])
                with btn_col:
                    if st.button("Use in Resume Builder", key=f"use_job_{i}"):
                        with st.spinner("Loading full job description..."):
                            full_description = _fetch_full_job_description(job.url, job.description)
                        st.session_state.job_title = job.title
                        st.session_state.company_name = job.company
                        st.session_state.job_description = full_description
                        st.session_state.job_title_input = job.title
                        st.session_state.company_name_input = job.company
                        st.session_state.job_description_input = full_description
                        st.session_state.job_builder_prefill_pending = True
                        st.success("Sent to resume builder.")
                with link_col:
                    if job.url:
                        st.link_button("View posting →", job.url)

    if st.session_state.job_search_results:
        with st.expander("Agent summary", expanded=False):
            st.markdown(
                f'<p style="font-family:Inter,sans-serif;font-size:0.875rem;color:#374151;">'
                f'{st.session_state.job_search_results}</p>',
                unsafe_allow_html=True,
            )


if __name__ == "__main__":
    main()
