"""
Simple RAG ranking pipeline for job search results.

Ranks jobs using BM25 (lexical) + FAISS (semantic) with Reciprocal Rank Fusion.
Designed for low latency: truncated text, batched embeddings, in-memory indices.
"""

from __future__ import annotations

import os
import platform
import re
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from rank_bm25 import BM25Okapi


@dataclass
class NormalizedJob:
    """Common schema for jobs from any source."""

    title: str
    company: str
    location: str
    description: str
    url: str
    source: str
    salary: str = ""
    raw: dict = field(default_factory=dict, repr=False)


# ── Helpers ────────────────────────────────────────────────────

_TAG_RE = re.compile(r"<[^>]+>")
_WORD_RE = re.compile(r"\w+")
_MAX_DESC = 500  # chars of description used for indexing


def _strip_html(text: str) -> str:
    return _TAG_RE.sub(" ", text).strip()


def _s(val: Any, default: str = "") -> str:
    """Safely coerce a value to a stripped string."""
    return str(val).strip() if val is not None else default


def _salary(min_val: Any, max_val: Any) -> str:
    parts = []
    for v in (min_val, max_val):
        if v is not None:
            try:
                parts.append(f"${float(v):,.0f}")
            except (ValueError, TypeError):
                pass
    return " – ".join(parts)


# ── Normalizers (one per source API) ───────────────────────────

def _normalize_adzuna(job: dict) -> NormalizedJob:
    return NormalizedJob(
        title=_s(job.get("title")),
        company=_s((job.get("company") or {}).get("display_name")),
        location=_s((job.get("location") or {}).get("display_name")),
        description=_s(job.get("description")),
        url=_s(job.get("redirect_url")),
        source="adzuna",
        salary=_salary(job.get("salary_min"), job.get("salary_max")),
        raw=job,
    )


def _normalize_muse(job: dict) -> NormalizedJob:
    locations = job.get("locations") or []
    loc = ", ".join(_s(l.get("name")) for l in locations if l.get("name"))
    return NormalizedJob(
        title=_s(job.get("name")),
        company=_s((job.get("company") or {}).get("name")),
        location=loc,
        description=_strip_html(_s(job.get("contents"))),
        url=_s((job.get("refs") or {}).get("landing_page")),
        source="muse",
        raw=job,
    )


def _normalize_jobspy(job: dict) -> NormalizedJob:
    return NormalizedJob(
        title=_s(job.get("title")),
        company=_s(job.get("company") or job.get("company_name")),
        location=_s(job.get("location")),
        description=_s(job.get("description")),
        url=_s(job.get("job_url")),
        source=_s(job.get("site", "jobspy")),
        salary=_salary(job.get("min_amount"), job.get("max_amount")),
        raw=job,
    )


_NORMALIZERS = {
    "adzuna_search": _normalize_adzuna,
    "muse_search": _normalize_muse,
    "jobspy_search": _normalize_jobspy,
}


def normalize_jobs(raw_jobs: list[dict]) -> list[NormalizedJob]:
    """Normalize raw job dicts (tagged with ``_source``) into a common schema.

    Jobs missing a title or description are dropped — they carry no useful
    signal for ranking.
    """
    out: list[NormalizedJob] = []
    for job in raw_jobs:
        normalizer = _NORMALIZERS.get(job.get("_source", ""), _normalize_jobspy)
        try:
            nj = normalizer(job)
            if not nj.title or not nj.description:
                continue
            out.append(nj)
        except Exception:
            continue
    return out


# ── Tokenizer / text builder ──────────────────────────────────

def _tokenize(text: str) -> list[str]:
    return _WORD_RE.findall(text.lower())


def _job_text(job: NormalizedJob) -> str:
    desc = job.description[:_MAX_DESC] if job.description else ""
    return f"{job.title} {job.company} {job.location} {desc}"


def _should_use_faiss() -> bool:
    """Gate FAISS behind an env var on macOS to avoid libomp runtime conflicts."""
    env_value = os.getenv("HIREME_USE_FAISS")
    if env_value is not None:
        return env_value.strip().lower() in {"1", "true", "yes", "on"}
    return platform.system() != "Darwin"


# ── BM25 (lexical) ────────────────────────────────────────────

def _bm25_rank(query: str, jobs: list[NormalizedJob]) -> list[int]:
    corpus = [_tokenize(_job_text(j)) for j in jobs]
    bm25 = BM25Okapi(corpus)
    scores = bm25.get_scores(_tokenize(query))
    return [int(i) for i in np.argsort(scores)[::-1]]


# ── FAISS (semantic) ──────────────────────────────────────────

def _faiss_rank(query: str, jobs: list[NormalizedJob]) -> list[int]:
    from langchain_openai import OpenAIEmbeddings
    import faiss

    embedder = OpenAIEmbeddings(model="text-embedding-3-small")
    texts = [_job_text(j) for j in jobs]

    # One batched API call for all job texts + query
    all_texts = texts + [query]
    all_vectors = np.array(embedder.embed_documents(all_texts), dtype=np.float32)

    job_vectors = all_vectors[:-1]
    query_vector = all_vectors[-1:].copy()

    faiss.normalize_L2(job_vectors)
    faiss.normalize_L2(query_vector)

    index = faiss.IndexFlatIP(job_vectors.shape[1])
    index.add(job_vectors)
    _, indices = index.search(query_vector, len(jobs))

    return [int(i) for i in indices[0]]


# ── Reciprocal Rank Fusion ────────────────────────────────────

def reciprocal_rank_fusion(rankings: list[list[int]], k: int = 60) -> list[int]:
    """Combine multiple rankings via RRF. Higher *k* smooths rank differences."""
    scores: dict[int, float] = {}
    for ranking in rankings:
        for rank, idx in enumerate(ranking):
            scores[idx] = scores.get(idx, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores, key=lambda i: scores[i], reverse=True)


# ── Public API ────────────────────────────────────────────────

def rank_jobs(
    query: str,
    raw_jobs: list[dict],
    top_n: int = 10,
) -> list[NormalizedJob]:
    """
    Normalize, index, and rank job results using BM25 + FAISS rank fusion.

    Parameters
    ----------
    query : str
        The user's original search query.
    raw_jobs : list[dict]
        Raw job dicts from the search tools, each tagged with ``_source``.
    top_n : int
        Number of top results to return.

    Returns
    -------
    list[NormalizedJob]
        Jobs ranked by fused relevance score.
    """
    jobs = normalize_jobs(raw_jobs)
    if len(jobs) <= 2:
        return jobs

    bm25_ranking = _bm25_rank(query, jobs)
    if _should_use_faiss():
        faiss_ranking = _faiss_rank(query, jobs)
        fused = reciprocal_rank_fusion([bm25_ranking, faiss_ranking])
    else:
        fused = bm25_ranking

    return [jobs[i] for i in fused[:top_n]]
