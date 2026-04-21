"""
Main evaluation runner for HireMe.AI.

Orchestrates parser, generation, RAG ranking, and A/B test evaluations,
then writes a consolidated JSON report to ``evaluation/results/``.

Usage
-----
    python -m evaluation.run_all                  # full suite
    python -m evaluation.run_all --quick          # parser + RAG only (no LLM generation costs)
    python -m evaluation.run_all --parser-only
    python -m evaluation.run_all --generator-only
    python -m evaluation.run_all --rag-only
    python -m evaluation.run_all --ab-only
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
PROJECT_DIR = REPO_ROOT / "HireMe.AI-V1"
EVAL_DIR = Path(__file__).resolve().parent
RESULTS_DIR = EVAL_DIR / "results"

for p in (PROJECT_DIR, str(EVAL_DIR)):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _write_report(report: dict[str, Any], label: str) -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"eval_report_{label}_{_timestamp()}.json"
    out_path = RESULTS_DIR / filename
    out_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    return out_path


# ---------------------------------------------------------------------------
# Individual suite runners (imported lazily to keep startup fast)
# ---------------------------------------------------------------------------

def _run_parser() -> dict[str, Any]:
    print("\n=== Resume Parser Evaluation ===")
    from eval_parser import run_parser_eval_suite
    results = run_parser_eval_suite()
    successful = [r for r in results if r.get("status") == "success"]
    summary = {
        "total": len(results),
        "successful": len(successful),
        "avg_accuracy": (
            round(sum(r["parser_accuracy"]["score"] for r in successful) / len(successful), 4)
            if successful else 0.0
        ),
    }
    print(f"  Parser accuracy: {summary['avg_accuracy']:.1%}")
    return {"summary": summary, "details": results}


def _run_generator(quick: bool = False) -> dict[str, Any]:
    print("\n=== Document Generation Evaluation ===")
    from eval_generator import run_generation_eval_suite, summarize_generation_results

    if quick:
        results = run_generation_eval_suite(
            candidate_ids=["candidate_1"],
            job_ids=["job_data_analyst"],
        )
    else:
        results = run_generation_eval_suite(skip_edge_cases=False)

    summary = summarize_generation_results(results)
    print(f"  Resume faithfulness avg: {summary.get('resume_averages', {}).get('faithfulness', 0):.1%}")
    print(f"  Resume relevance avg:    {summary.get('resume_averages', {}).get('relevance', 0):.1%}")
    # Strip raw outputs to keep report file size manageable
    for r in results:
        r.pop("outputs", None)
    return {"summary": summary, "details": results}


def _run_rag() -> dict[str, Any]:
    print("\n=== RAG Ranking Evaluation ===")
    from eval_rag import run_rag_eval_suite, summarize_rag_results
    results = run_rag_eval_suite(use_faiss=False)
    summary = summarize_rag_results(results)
    print(f"  Avg NDCG@3:      {summary.get('avg_ndcg_at_3', 0):.4f}")
    print(f"  Avg MRR:         {summary.get('avg_mrr', 0):.4f}")
    print(f"  Avg Precision@3: {summary.get('avg_precision_at_3', 0):.4f}")
    return {"summary": summary, "details": results}


def _run_ab() -> dict[str, Any]:
    print("\n=== A/B Testing ===")
    from ab_testing import run_default_ab_test, summarize_ab_results
    results = run_default_ab_test()
    summary = summarize_ab_results(results)
    print(f"  Win rates: {summary.get('win_rates', {})}")
    # Strip raw outputs
    for r in results:
        r.pop("outputs_a", None)
        r.pop("outputs_b", None)
    return {"summary": summary, "details": results}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Run HireMe.AI evaluation suite.")
    parser.add_argument("--quick", action="store_true", help="Run a minimal subset (parser + RAG, 1 gen pair).")
    parser.add_argument("--parser-only", action="store_true")
    parser.add_argument("--generator-only", action="store_true")
    parser.add_argument("--rag-only", action="store_true")
    parser.add_argument("--ab-only", action="store_true")
    args = parser.parse_args()

    from dotenv import load_dotenv
    load_dotenv(REPO_ROOT / ".env", override=True)

    run_all = not any([args.parser_only, args.generator_only, args.rag_only, args.ab_only])
    report: dict[str, Any] = {"run_timestamp": _timestamp()}

    overall_start = time.perf_counter()

    if run_all or args.parser_only:
        report["parser"] = _run_parser()

    if run_all or args.generator_only:
        report["generator"] = _run_generator(quick=args.quick)

    if run_all or args.rag_only:
        report["rag"] = _run_rag()

    if (run_all and not args.quick) or args.ab_only:
        report["ab_testing"] = _run_ab()

    report["total_time_seconds"] = round(time.perf_counter() - overall_start, 2)

    # Determine label
    if args.parser_only:
        label = "parser"
    elif args.generator_only:
        label = "generator"
    elif args.rag_only:
        label = "rag"
    elif args.ab_only:
        label = "ab"
    elif args.quick:
        label = "quick"
    else:
        label = "full"

    out_path = _write_report(report, label)

    print(f"\n{'='*50}")
    print(f"Evaluation complete in {report['total_time_seconds']}s")
    print(f"Report saved to: {out_path}")

    # Print compact summary
    print(f"\n--- Summary ---")
    if "parser" in report:
        print(f"Parser accuracy:       {report['parser']['summary'].get('avg_accuracy', 0):.1%}")
    if "generator" in report:
        gen = report["generator"]["summary"]
        ra = gen.get("resume_averages", {})
        print(f"Resume faithfulness:   {ra.get('faithfulness', 0):.1%}")
        print(f"Resume relevance:      {ra.get('relevance', 0):.1%}")
        print(f"Resume coherence:      {ra.get('coherence', 0):.1%}")
        print(f"Resume completeness:   {ra.get('completeness', 0):.1%}")
        print(f"Resume kw overlap:     {ra.get('keyword_overlap', 0):.1%}")
        print(f"Resume template adh:   {ra.get('template_adherence', 0):.1%}")
    if "rag" in report:
        rag = report["rag"]["summary"]
        print(f"RAG NDCG@3:            {rag.get('avg_ndcg_at_3', 0):.4f}")
        print(f"RAG MRR:               {rag.get('avg_mrr', 0):.4f}")
        print(f"RAG Precision@3:       {rag.get('avg_precision_at_3', 0):.4f}")
    if "ab_testing" in report:
        ab = report["ab_testing"]["summary"]
        print(f"A/B win rates:         {ab.get('win_rates', {})}")


if __name__ == "__main__":
    main()
