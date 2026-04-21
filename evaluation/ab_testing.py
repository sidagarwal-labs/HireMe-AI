"""
A/B testing framework for HireMe.AI.

Compares two pipeline variants (different models, prompts, or parameters)
side-by-side using the same evaluation metrics, and produces a comparative
report including LLM-as-judge pairwise preference scoring.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[1]
PROJECT_DIR = REPO_ROOT / "HireMe.AI-V1"
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from langchain_openai import ChatOpenAI

from models import CandidateProfile, JobPosting
from prompts import build_resume_prompt, build_cover_letter_prompt
from metrics import (
    faithfulness_score,
    relevance_score,
    coherence_score,
    completeness_score,
    keyword_overlap_score,
)

EVAL_DIR = Path(__file__).resolve().parent
TEST_DATA = EVAL_DIR / "test_data"
TEMPLATES_DIR = PROJECT_DIR / "Templates"


# ---------------------------------------------------------------------------
# Pipeline variant definition
# ---------------------------------------------------------------------------

class PipelineVariant:
    """Describes one variant of the generation pipeline for A/B testing."""

    def __init__(
        self,
        name: str,
        model: str = "gpt-4.1-nano",
        temperature: float = 0.2,
        prompt_builder: Callable | None = None,
    ):
        self.name = name
        self.model = model
        self.temperature = temperature
        self.prompt_builder = prompt_builder  # optional override

    def __repr__(self) -> str:
        return f"PipelineVariant(name={self.name!r}, model={self.model!r}, temp={self.temperature})"


# ---------------------------------------------------------------------------
# Generation helper
# ---------------------------------------------------------------------------

def _generate_with_variant(
    variant: PipelineVariant,
    candidate_data: dict[str, Any],
    job_data: dict[str, Any],
) -> dict[str, str]:
    """Run generation using a specific pipeline variant."""
    profile = CandidateProfile(**candidate_data)
    job = JobPosting(**job_data)

    resume_template = (TEMPLATES_DIR / "resume_template.md").read_text(encoding="utf-8")
    cover_template = (TEMPLATES_DIR / "cover_letter_template.md").read_text(encoding="utf-8")

    if variant.prompt_builder:
        resume_prompt = variant.prompt_builder(profile, job, resume_template, "resume")
        cover_prompt = variant.prompt_builder(profile, job, cover_template, "cover_letter")
    else:
        resume_prompt = build_resume_prompt(profile, job, resume_template)
        cover_prompt = build_cover_letter_prompt(profile, job, cover_template)

    llm = ChatOpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        model=variant.model,
        temperature=variant.temperature,
    )

    resume_md = llm.invoke(resume_prompt).content.strip()
    cover_md = llm.invoke(cover_prompt).content.strip()

    return {"resume_md": resume_md, "cover_letter_md": cover_md}


# ---------------------------------------------------------------------------
# Pairwise LLM-as-judge comparison
# ---------------------------------------------------------------------------

def _pairwise_preference(
    output_a: str,
    output_b: str,
    label_a: str,
    label_b: str,
    criteria: str,
) -> dict[str, Any]:
    """Ask an LLM judge which output is better for a given criterion."""
    llm = ChatOpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        model=os.getenv("EVAL_MODEL", "gpt-4.1-nano"),
        temperature=0.0,
    )

    prompt = f"""You are a fair evaluation judge. Compare two generated documents
and decide which is better based on the criterion: {criteria}.

=== DOCUMENT A ({label_a}) ===
{output_a[:3000]}

=== DOCUMENT B ({label_b}) ===
{output_b[:3000]}

Respond in this exact format:
Winner: A or B or Tie
Confidence: High/Medium/Low
Reasoning: <1-2 sentence explanation>
"""
    response = llm.invoke(prompt).content
    winner = "tie"
    if "winner: a" in response.lower():
        winner = label_a
    elif "winner: b" in response.lower():
        winner = label_b

    return {"winner": winner, "raw_response": response}


# ---------------------------------------------------------------------------
# A/B test runner
# ---------------------------------------------------------------------------

def run_ab_test(
    variant_a: PipelineVariant,
    variant_b: PipelineVariant,
    candidate: dict[str, Any],
    job: dict[str, Any],
) -> dict[str, Any]:
    """
    Run an A/B test between two pipeline variants on a single (candidate, job) pair.

    Returns comparative metrics and pairwise preference judgments.
    """
    candidate_data = {k: v for k, v in candidate.items() if k != "id"}
    job_data = {
        "job_title": job.get("job_title", ""),
        "company_name": job.get("company_name", ""),
        "job_description": job.get("job_description", ""),
    }
    jd = job.get("job_description", "")

    # Generate with both variants
    start_a = time.perf_counter()
    outputs_a = _generate_with_variant(variant_a, candidate_data, job_data)
    time_a = time.perf_counter() - start_a

    start_b = time.perf_counter()
    outputs_b = _generate_with_variant(variant_b, candidate_data, job_data)
    time_b = time.perf_counter() - start_b

    # Score both outputs
    def _score(text: str, doc_type: str) -> dict[str, Any]:
        return {
            "faithfulness": faithfulness_score(text, candidate_data),
            "relevance": relevance_score(text, jd),
            "coherence": coherence_score(text),
            "completeness": completeness_score(text, candidate_data),
            "keyword_overlap": keyword_overlap_score(text, jd),
        }

    metrics_a = {
        "resume": _score(outputs_a["resume_md"], "resume"),
        "cover_letter": _score(outputs_a["cover_letter_md"], "cover_letter"),
    }
    metrics_b = {
        "resume": _score(outputs_b["resume_md"], "resume"),
        "cover_letter": _score(outputs_b["cover_letter_md"], "cover_letter"),
    }

    # Pairwise preferences
    preferences = {}
    for criteria in ["overall quality", "job relevance", "faithfulness to candidate data"]:
        preferences[criteria] = _pairwise_preference(
            outputs_a["resume_md"],
            outputs_b["resume_md"],
            variant_a.name,
            variant_b.name,
            criteria,
        )

    return {
        "variant_a": variant_a.name,
        "variant_b": variant_b.name,
        "candidate": candidate.get("id", candidate.get("name")),
        "job": job.get("id", job.get("job_title")),
        "metrics_a": metrics_a,
        "metrics_b": metrics_b,
        "timing": {
            "variant_a_seconds": round(time_a, 2),
            "variant_b_seconds": round(time_b, 2),
        },
        "preferences": preferences,
        "outputs_a": outputs_a,
        "outputs_b": outputs_b,
    }


def summarize_ab_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate wins/ties across multiple A/B test runs."""
    if not results:
        return {"total_tests": 0}

    variant_a_name = results[0]["variant_a"]
    variant_b_name = results[0]["variant_b"]
    wins: dict[str, int] = {variant_a_name: 0, variant_b_name: 0, "tie": 0}

    for r in results:
        for criteria, pref in r.get("preferences", {}).items():
            winner = pref.get("winner", "tie")
            if winner == variant_a_name:
                wins[variant_a_name] += 1
            elif winner == variant_b_name:
                wins[variant_b_name] += 1
            else:
                wins["tie"] += 1

    total_comparisons = sum(wins.values())
    return {
        "total_tests": len(results),
        "total_comparisons": total_comparisons,
        "wins": wins,
        "win_rates": {
            k: round(v / total_comparisons, 4) if total_comparisons else 0.0
            for k, v in wins.items()
        },
    }


# ---------------------------------------------------------------------------
# Convenience: default A/B test with two model variants
# ---------------------------------------------------------------------------

def run_default_ab_test() -> list[dict[str, Any]]:
    """Run an A/B test comparing two model sizes on the first candidate×job pair."""
    candidates = json.loads((TEST_DATA / "candidates.json").read_text(encoding="utf-8"))
    jobs = json.loads((TEST_DATA / "jobs.json").read_text(encoding="utf-8"))

    # Use the first non-edge candidate and job
    candidate = next(c for c in candidates if "edge" not in c.get("id", ""))
    job = next(j for j in jobs if "edge" not in j.get("id", ""))

    variant_a = PipelineVariant(name="gpt-4.1-nano", model="gpt-4.1-nano", temperature=0.2)
    variant_b = PipelineVariant(name="gpt-4.1-mini", model="gpt-4.1-mini", temperature=0.2)

    print(f"  A/B test: {variant_a.name} vs {variant_b.name}")
    print(f"  Candidate: {candidate.get('id')}  |  Job: {job.get('id')}")

    result = run_ab_test(variant_a, variant_b, candidate, job)
    return [result]


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(REPO_ROOT / ".env", override=True)

    results = run_default_ab_test()
    summary = summarize_ab_results(results)
    print(json.dumps(summary, indent=2, default=str))
