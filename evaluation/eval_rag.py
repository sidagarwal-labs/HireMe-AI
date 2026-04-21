"""
Evaluate the RAG-based job ranking pipeline.

Tests the BM25 + FAISS reciprocal rank fusion pipeline with synthetic job
listings and known-relevant queries, reporting NDCG, MRR, and
precision-at-k metrics.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
PROJECT_DIR = REPO_ROOT / "HireMe.AI-V1"
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from rag import rank_jobs, normalize_jobs

EVAL_DIR = Path(__file__).resolve().parent
TEST_DATA = EVAL_DIR / "test_data"


# ---------------------------------------------------------------------------
# Synthetic job data for ranking evaluation
# ---------------------------------------------------------------------------

RANKING_TEST_CASES: list[dict[str, Any]] = [
    {
        "id": "rank_data_analyst",
        "query": "data analyst SQL Tableau dashboards",
        "jobs": [
            {
                "title": "Senior Data Analyst",
                "company": "DataCo",
                "location": "New York, NY",
                "description": "Build dashboards using Tableau and SQL. Analyze business KPIs and present insights to stakeholders. 3+ years experience required.",
                "job_url": "https://example.com/1",
                "site": "test",
                "_source": "jobspy_search",
                "relevance": 3,  # highly relevant
            },
            {
                "title": "Data Analyst Intern",
                "company": "StartupX",
                "location": "Remote",
                "description": "Entry-level data analyst position. Use SQL and Excel to support the analytics team. Learn Tableau on the job.",
                "job_url": "https://example.com/2",
                "site": "test",
                "_source": "jobspy_search",
                "relevance": 2,  # relevant
            },
            {
                "title": "Machine Learning Engineer",
                "company": "AI Labs",
                "location": "San Francisco, CA",
                "description": "Design and train deep learning models using PyTorch. Deploy ML pipelines on Kubernetes. PhD preferred.",
                "job_url": "https://example.com/3",
                "site": "test",
                "_source": "jobspy_search",
                "relevance": 0,  # not relevant
            },
            {
                "title": "Marketing Coordinator",
                "company": "BrandCo",
                "location": "Chicago, IL",
                "description": "Coordinate marketing campaigns. Manage social media accounts and track engagement metrics.",
                "job_url": "https://example.com/4",
                "site": "test",
                "_source": "jobspy_search",
                "relevance": 0,  # not relevant
            },
            {
                "title": "Business Intelligence Analyst",
                "company": "FinTech Inc",
                "location": "Charlotte, NC",
                "description": "Create interactive Tableau dashboards for financial reporting. Write complex SQL queries against Snowflake. Automate data pipelines.",
                "job_url": "https://example.com/5",
                "site": "test",
                "_source": "jobspy_search",
                "relevance": 3,  # highly relevant
            },
        ],
    },
    {
        "id": "rank_software_engineer",
        "query": "software engineer Python microservices AWS",
        "jobs": [
            {
                "title": "Backend Software Engineer",
                "company": "CloudScale",
                "location": "Seattle, WA",
                "description": "Build microservices in Python using FastAPI. Deploy to AWS ECS. Experience with Docker and CI/CD required.",
                "job_url": "https://example.com/6",
                "site": "test",
                "_source": "jobspy_search",
                "relevance": 3,
            },
            {
                "title": "Frontend Developer",
                "company": "WebCraft",
                "location": "Austin, TX",
                "description": "Build React applications with TypeScript. Create responsive, accessible UIs. No backend experience needed.",
                "job_url": "https://example.com/7",
                "site": "test",
                "_source": "jobspy_search",
                "relevance": 0,
            },
            {
                "title": "DevOps Engineer",
                "company": "InfraTeam",
                "location": "Remote",
                "description": "Manage AWS infrastructure using Terraform. Build CI/CD pipelines. Some Python scripting for automation.",
                "job_url": "https://example.com/8",
                "site": "test",
                "_source": "jobspy_search",
                "relevance": 1,
            },
            {
                "title": "Python Developer",
                "company": "DataPipe",
                "location": "New York, NY",
                "description": "Develop data processing microservices in Python. Use AWS Lambda, SQS, and DynamoDB. Agile team environment.",
                "job_url": "https://example.com/9",
                "site": "test",
                "_source": "jobspy_search",
                "relevance": 3,
            },
        ],
    },
]


# ---------------------------------------------------------------------------
# Ranking metrics
# ---------------------------------------------------------------------------

def _dcg(relevances: list[float], k: int | None = None) -> float:
    """Discounted Cumulative Gain."""
    if k is not None:
        relevances = relevances[:k]
    return sum(rel / np.log2(i + 2) for i, rel in enumerate(relevances))


def ndcg_at_k(relevances: list[float], k: int) -> float:
    """Normalized Discounted Cumulative Gain at k."""
    ideal = sorted(relevances, reverse=True)
    ideal_dcg = _dcg(ideal, k)
    if ideal_dcg == 0:
        return 0.0
    return _dcg(relevances, k) / ideal_dcg


def mrr(relevances: list[float], threshold: float = 1.0) -> float:
    """Mean Reciprocal Rank — rank of first relevant result."""
    for i, rel in enumerate(relevances):
        if rel >= threshold:
            return 1.0 / (i + 1)
    return 0.0


def precision_at_k(relevances: list[float], k: int, threshold: float = 1.0) -> float:
    """Precision at k — fraction of top-k results that are relevant."""
    top_k = relevances[:k]
    if not top_k:
        return 0.0
    return sum(1 for r in top_k if r >= threshold) / k


# ---------------------------------------------------------------------------
# Evaluation runner
# ---------------------------------------------------------------------------

def evaluate_ranking(
    test_case: dict[str, Any],
    use_faiss: bool = False,
) -> dict[str, Any]:
    """
    Evaluate ranking quality for a single test case.

    Runs the RAG pipeline (BM25-only by default to avoid FAISS/API costs)
    and computes NDCG@3, MRR, and P@3 against known relevance labels.
    """
    import os
    if not use_faiss:
        os.environ["HIREME_USE_FAISS"] = "0"

    query = test_case["query"]
    raw_jobs = test_case["jobs"]

    # Build relevance lookup keyed on job URL
    relevance_map = {j["job_url"]: j.get("relevance", 0) for j in raw_jobs}

    ranked = rank_jobs(query, raw_jobs, top_n=len(raw_jobs))
    ranked_relevances = [relevance_map.get(j.url, 0) for j in ranked]

    k = min(3, len(ranked))

    return {
        "test_case_id": test_case["id"],
        "query": query,
        "num_jobs": len(raw_jobs),
        "ranked_order": [
            {"title": j.title, "company": j.company, "relevance": relevance_map.get(j.url, 0)}
            for j in ranked
        ],
        "ndcg_at_3": round(ndcg_at_k(ranked_relevances, k), 4),
        "mrr": round(mrr(ranked_relevances), 4),
        "precision_at_3": round(precision_at_k(ranked_relevances, k), 4),
    }


def run_rag_eval_suite(use_faiss: bool = False) -> list[dict[str, Any]]:
    """Run ranking evaluation across all test cases."""
    results: list[dict[str, Any]] = []
    for tc in RANKING_TEST_CASES:
        print(f"  Evaluating ranking: {tc['id']}")
        try:
            result = evaluate_ranking(tc, use_faiss=use_faiss)
            result["status"] = "success"
        except Exception as exc:
            result = {
                "test_case_id": tc["id"],
                "status": "error",
                "error": str(exc),
            }
        results.append(result)
    return results


def summarize_rag_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate ranking evaluation results."""
    successful = [r for r in results if r.get("status") == "success"]
    if not successful:
        return {"total": len(results), "successful": 0}

    return {
        "total": len(results),
        "successful": len(successful),
        "avg_ndcg_at_3": round(np.mean([r["ndcg_at_3"] for r in successful]), 4),
        "avg_mrr": round(np.mean([r["mrr"] for r in successful]), 4),
        "avg_precision_at_3": round(np.mean([r["precision_at_3"] for r in successful]), 4),
    }


if __name__ == "__main__":
    results = run_rag_eval_suite()
    summary = summarize_rag_results(results)
    print(json.dumps(summary, indent=2))
    print("\nDetails:")
    print(json.dumps(results, indent=2, default=str))
