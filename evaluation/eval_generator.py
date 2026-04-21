"""
Evaluate resume and cover letter generation quality.

Runs the generation pipeline for each (candidate, job) pair and scores the
outputs on faithfulness, relevance, coherence, completeness, keyword overlap,
and template adherence.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
PROJECT_DIR = REPO_ROOT / "HireMe.AI-V1"
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from service import generate_documents
from metrics import (
    faithfulness_score,
    relevance_score,
    coherence_score,
    completeness_score,
    template_adherence_score,
    keyword_overlap_score,
)

EVAL_DIR = Path(__file__).resolve().parent
TEST_DATA = EVAL_DIR / "test_data"
TEMPLATES_DIR = PROJECT_DIR / "Templates"


def _load_json(name: str) -> list[dict[str, Any]]:
    return json.loads((TEST_DATA / name).read_text(encoding="utf-8"))


def evaluate_generation(
    candidate: dict[str, Any],
    job: dict[str, Any],
    *,
    use_tool_calling: bool = False,
) -> dict[str, Any]:
    """
    Generate documents for one (candidate, job) pair and score them.

    Returns
    -------
    dict with ``resume_metrics``, ``cover_letter_metrics``, ``outputs``, ``timing``.
    """
    candidate_data = {k: v for k, v in candidate.items() if k != "id"}
    job_data = {
        "job_title": job.get("job_title", ""),
        "company_name": job.get("company_name", ""),
        "job_description": job.get("job_description", ""),
    }

    resume_template = (TEMPLATES_DIR / "resume_template.md").read_text(encoding="utf-8")
    cover_template = (TEMPLATES_DIR / "cover_letter_template.md").read_text(encoding="utf-8")

    start = time.perf_counter()
    outputs = generate_documents(
        candidate_data=candidate_data,
        job_data=job_data,
        resume_template_path=TEMPLATES_DIR / "resume_template.md",
        cover_template_path=TEMPLATES_DIR / "cover_letter_template.md",
        use_tool_calling=use_tool_calling,
    )
    elapsed = time.perf_counter() - start

    resume_md = outputs["resume_md"]
    cover_md = outputs["cover_letter_md"]
    jd = job.get("job_description", "")

    resume_metrics = {
        "faithfulness": faithfulness_score(resume_md, candidate_data),
        "relevance": relevance_score(resume_md, jd),
        "coherence": coherence_score(resume_md),
        "completeness": completeness_score(resume_md, candidate_data),
        "keyword_overlap": keyword_overlap_score(resume_md, jd),
        "template_adherence": template_adherence_score(resume_md, resume_template),
    }

    cover_metrics = {
        "faithfulness": faithfulness_score(cover_md, candidate_data),
        "relevance": relevance_score(cover_md, jd),
        "coherence": coherence_score(cover_md),
        "keyword_overlap": keyword_overlap_score(cover_md, jd),
        "template_adherence": template_adherence_score(cover_md, cover_template),
    }

    return {
        "candidate": candidate.get("id", candidate.get("name", "unknown")),
        "job": job.get("id", job.get("job_title", "unknown")),
        "resume_metrics": resume_metrics,
        "cover_letter_metrics": cover_metrics,
        "outputs": outputs,
        "timing_seconds": round(elapsed, 2),
    }


def run_generation_eval_suite(
    candidate_ids: list[str] | None = None,
    job_ids: list[str] | None = None,
    skip_edge_cases: bool = False,
) -> list[dict[str, Any]]:
    """
    Evaluate generation across all (or selected) candidate × job combinations.

    Parameters
    ----------
    candidate_ids : list[str], optional
        Filter to specific candidate IDs. None = all.
    job_ids : list[str], optional
        Filter to specific job IDs. None = all.
    skip_edge_cases : bool
        If True, skip candidates/jobs whose ID contains "edge".
    """
    candidates = _load_json("candidates.json")
    jobs = _load_json("jobs.json")

    if candidate_ids:
        candidates = [c for c in candidates if c.get("id") in candidate_ids]
    if job_ids:
        jobs = [j for j in jobs if j.get("id") in job_ids]
    if skip_edge_cases:
        candidates = [c for c in candidates if "edge" not in c.get("id", "")]
        jobs = [j for j in jobs if "edge" not in j.get("id", "")]

    results: list[dict[str, Any]] = []

    for candidate in candidates:
        for job in jobs:
            pair_label = f"{candidate.get('id', '?')} × {job.get('id', '?')}"
            print(f"  Evaluating: {pair_label}")
            try:
                result = evaluate_generation(candidate, job)
                result["status"] = "success"
            except Exception as exc:
                result = {
                    "candidate": candidate.get("id"),
                    "job": job.get("id"),
                    "status": "error",
                    "error": str(exc),
                }
            results.append(result)

    return results


def summarize_generation_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate generation evaluation results into a summary report."""
    successful = [r for r in results if r.get("status") == "success"]
    if not successful:
        return {"total": len(results), "successful": 0, "averages": {}}

    def _avg_metric(doc_type: str, metric_name: str) -> float:
        scores = []
        for r in successful:
            m = r.get(f"{doc_type}_metrics", {}).get(metric_name, {})
            if "score" in m:
                max_s = m.get("max_score", 10.0)
                scores.append(m["score"] / max_s if max_s > 0 else 0.0)
        return round(sum(scores) / len(scores), 4) if scores else 0.0

    return {
        "total": len(results),
        "successful": len(successful),
        "failed": len(results) - len(successful),
        "resume_averages": {
            "faithfulness": _avg_metric("resume", "faithfulness"),
            "relevance": _avg_metric("resume", "relevance"),
            "coherence": _avg_metric("resume", "coherence"),
            "completeness": _avg_metric("resume", "completeness"),
            "keyword_overlap": _avg_metric("resume", "keyword_overlap"),
            "template_adherence": _avg_metric("resume", "template_adherence"),
        },
        "cover_letter_averages": {
            "faithfulness": _avg_metric("cover_letter", "faithfulness"),
            "relevance": _avg_metric("cover_letter", "relevance"),
            "coherence": _avg_metric("cover_letter", "coherence"),
            "keyword_overlap": _avg_metric("cover_letter", "keyword_overlap"),
            "template_adherence": _avg_metric("cover_letter", "template_adherence"),
        },
        "avg_timing_seconds": round(
            sum(r.get("timing_seconds", 0) for r in successful) / len(successful), 2
        ),
    }


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(REPO_ROOT / ".env", override=True)

    results = run_generation_eval_suite(
        candidate_ids=["candidate_1"],
        job_ids=["job_data_analyst"],
    )
    summary = summarize_generation_results(results)
    print(json.dumps(summary, indent=2, default=str))
