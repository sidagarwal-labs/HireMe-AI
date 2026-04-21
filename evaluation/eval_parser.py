"""
Evaluate the resume parser.

Parses sample resume files, compares the extracted structured profile against
golden-reference candidate data, and reports field-level accuracy.
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

from doc_parser import parse_resume_file
from metrics import parser_accuracy_score


EVAL_DIR = Path(__file__).resolve().parent
TEST_DATA = EVAL_DIR / "test_data"


def _load_golden_candidates() -> list[dict[str, Any]]:
    return json.loads((TEST_DATA / "candidates.json").read_text(encoding="utf-8"))


def evaluate_parser(
    resume_path: str | Path | None = None,
    golden_index: int = 0,
) -> dict[str, Any]:
    """
    Parse a resume file and compare against the golden candidate at *golden_index*.

    Parameters
    ----------
    resume_path : path, optional
        Resume file to parse.  Defaults to ``test_data/parser_inputs/sample_resume.txt``.
    golden_index : int
        Index into ``candidates.json`` to use as the ground-truth profile.

    Returns
    -------
    dict with ``parser_accuracy``, ``parsed_profile``, ``timing_seconds``.
    """
    if resume_path is None:
        resume_path = TEST_DATA / "parser_inputs" / "sample_resume.txt"
    resume_path = Path(resume_path)

    golden_candidates = _load_golden_candidates()
    golden = golden_candidates[golden_index]
    # Remove our evaluation-only "id" field before comparing
    golden = {k: v for k, v in golden.items() if k != "id"}

    start = time.perf_counter()
    parsed = parse_resume_file(resume_path)
    elapsed = time.perf_counter() - start

    accuracy = parser_accuracy_score(parsed, golden)

    return {
        "resume_file": str(resume_path),
        "golden_candidate": golden.get("name", f"index-{golden_index}"),
        "parser_accuracy": accuracy,
        "parsed_profile": parsed,
        "timing_seconds": round(elapsed, 2),
    }


def run_parser_eval_suite() -> list[dict[str, Any]]:
    """Run parser evaluation for every file in ``test_data/parser_inputs/``."""
    inputs_dir = TEST_DATA / "parser_inputs"
    results: list[dict[str, Any]] = []

    for path in sorted(inputs_dir.iterdir()):
        if path.suffix.lower() in {".txt", ".md", ".docx", ".pdf", ".png", ".jpg", ".jpeg", ".webp"}:
            print(f"  Evaluating parser on: {path.name}")
            try:
                result = evaluate_parser(resume_path=path, golden_index=0)
                result["status"] = "success"
            except Exception as exc:
                result = {
                    "resume_file": str(path),
                    "status": "error",
                    "error": str(exc),
                }
            results.append(result)

    return results


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(REPO_ROOT / ".env", override=True)

    results = run_parser_eval_suite()
    print(json.dumps(results, indent=2, default=str))
