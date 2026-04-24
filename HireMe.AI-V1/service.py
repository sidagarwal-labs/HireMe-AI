from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from agents import make_cover_letter_writer_llm, make_resume_writer_llm
from doc_parser import parse_resume_file
from models import CandidateProfile, JobPosting
from prompts import build_cover_letter_prompt, build_resume_prompt
from tools import format_cover_letter_markdown, format_resume_markdown
from tools_llm import invoke_with_tools


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def generate_documents(
    candidate_data: dict[str, Any],
    job_data: dict[str, Any],
    *,
    resume_template_path: str | Path,
    cover_template_path: str | Path,
    use_tool_calling: bool = False,
    temperature: float = 0.3,
) -> dict[str, str]:
    """
    Main pipeline:
    1. Validate candidate + job input
    2. Build prompts from templates
    3. Generate resume and cover letter
    4. Return markdown outputs
    """
    profile = CandidateProfile(**candidate_data)
    job = JobPosting(**job_data)

    resume_template = _read_text(Path(resume_template_path))
    cover_template = _read_text(Path(cover_template_path))

    resume_prompt = build_resume_prompt(profile, job, resume_template)
    cover_prompt = build_cover_letter_prompt(profile, job, cover_template)

    resume_llm = make_resume_writer_llm(temperature=temperature)
    cover_llm = make_cover_letter_writer_llm(temperature=temperature)

    if use_tool_calling:
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            resume_future = executor.submit(invoke_with_tools, resume_llm, resume_prompt)
            cover_future = executor.submit(invoke_with_tools, cover_llm, cover_prompt)
            resume_md = resume_future.result()
            cover_md = cover_future.result()
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            resume_future = executor.submit(lambda: resume_llm.invoke(resume_prompt).content)
            cover_future = executor.submit(lambda: cover_llm.invoke(cover_prompt).content)
            resume_md = resume_future.result()
            cover_md = cover_future.result()

    return {
        "resume_md": format_resume_markdown(resume_md),
        "cover_letter_md": format_cover_letter_markdown(cover_md),
    }


def run_pipeline(
    *,
    repo_root: str | Path,
    candidate_json_path: str | Path | None = None,
    candidate_document_path: str | Path | None = None,
    job_description: str,
    job_title: str = "",
    company_name: str = "",
    output_dir: str | Path | None = None,
    use_tool_calling: bool = False,
) -> dict[str, str]:
    """
    File-based pipeline helper for scripts/notebooks.
    """
    repo_root = Path(repo_root)
    project_dir = repo_root / "HireMe.AI-V1"
    templates_dir = project_dir / "Templates"

    load_dotenv(repo_root / ".env", override=True)
    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY is missing. Set it in your environment or .env file.")

    if candidate_document_path is not None:
        candidate_data = parse_resume_file(Path(candidate_document_path))
    elif candidate_json_path is not None:
        candidate_data = _read_json(Path(candidate_json_path))
    else:
        raise ValueError("Provide either candidate_json_path or candidate_document_path.")

    job_data = {
        "job_title": job_title,
        "company_name": company_name,
        "job_description": job_description,
    }

    outputs = generate_documents(
        candidate_data,
        job_data,
        resume_template_path=templates_dir / "resume_template.md",
        cover_template_path=templates_dir / "cover_letter_template.md",
        use_tool_calling=use_tool_calling,
    )

    if output_dir is not None:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        (out / "resume_output.md").write_text(outputs["resume_md"], encoding="utf-8")
        (out / "cover_letter_output.md").write_text(outputs["cover_letter_md"], encoding="utf-8")

    return outputs


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate resume and cover letter markdown outputs.")
    parser.add_argument("--repo-root", default=".", help="Path to repo root.")
    parser.add_argument(
        "--candidate-json",
        default="HireMe.AI-V1/candidate_profile.json",
        help="Path to candidate profile JSON.",
    )
    parser.add_argument(
        "--candidate-document",
        default=None,
        help="Path to a resume document (.txt, .md, .docx, .pdf, .png, .jpg, .jpeg, .webp).",
    )
    parser.add_argument("--job-description", required=True, help="Full job description text.")
    parser.add_argument("--job-title", default="", help="Target job title.")
    parser.add_argument("--company-name", default="", help="Target company name.")
    parser.add_argument("--output-dir", default="notebooks/outputs", help="Directory for markdown outputs.")
    parser.add_argument(
        "--use-tool-calling",
        action="store_true",
        help="Let the LLM call tools from tools_llm.py during generation.",
    )
    return parser


def main() -> None:
    args = _build_arg_parser().parse_args()
    outputs = run_pipeline(
        repo_root=args.repo_root,
        candidate_json_path=None if args.candidate_document else args.candidate_json,
        candidate_document_path=args.candidate_document,
        job_description=args.job_description,
        job_title=args.job_title,
        company_name=args.company_name,
        output_dir=args.output_dir,
        use_tool_calling=args.use_tool_calling,
    )
    print("Resume preview:\n")
    print(outputs["resume_md"][:1000])
    print("\nCover letter preview:\n")
    print(outputs["cover_letter_md"][:1000])


if __name__ == "__main__":
    main()
