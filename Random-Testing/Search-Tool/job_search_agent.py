import ast
import json
import os
import re
import sys

from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", ".env"), override=True)

from langchain.agents import create_agent
from adzuna_tool import adzuna_jobs
from muse_tool import muse_jobs
from jobspy_tool import jobspy_jobs

SYSTEM_PROMPT = (
    "You are a helpful job search assistant with three tools. "
    "- Adzuna: Best for keyword searches, salary filtering, and employment type (full-time, contract, etc.) "
    "- The Muse: Best for browsing by job category, experience level, or specific company. "
    "- JobSpy: Best for broad searches across LinkedIn, Indeed, Glassdoor, ZipRecruiter, and Google Jobs simultaneously. Use this when the user wants wide coverage, remote jobs, or when other tools return few results. "
    "You can use any combination of tools to broaden the scope and find more jobs, a single tool to narrow down results, or none."
    )

def build_agent():
    return create_agent(
        model="openai:gpt-5-nano",
        tools=[adzuna_jobs, muse_jobs, jobspy_jobs],
        system_prompt=SYSTEM_PROMPT,
    )


def _extract_tool_results(messages) -> list[dict]:
    """Extract raw job data from ToolMessage objects in the agent history."""
    raw_jobs: list[dict] = []
    for msg in messages:
        if not (hasattr(msg, "type") and msg.type == "tool"):
            continue

        content = msg.content
        try:
            if isinstance(content, dict):
                data = content
            elif isinstance(content, str):
                try:
                    data = json.loads(content)
                except json.JSONDecodeError:
                    try:
                        data = ast.literal_eval(content)
                    except (ValueError, SyntaxError):
                        # Tool output may contain non-literal Python objects
                        # (e.g. Timestamp). Try sanitising before eval.
                        cleaned = _sanitize_python_repr(content)
                        data = ast.literal_eval(cleaned)
            else:
                continue

            if data.get("success") and "data" in data:
                source = getattr(msg, "name", "unknown")
                for job in data["data"]:
                    if isinstance(job, dict):
                        job["_source"] = source
                        raw_jobs.append(job)
        except Exception:
            continue
    return raw_jobs


# Patterns like  Timestamp('...')  or  datetime.date(2026, 3, 24)
_FUNC_CALL_RE = re.compile(
    r"(?:[\w.]+)\((['\"].*?['\"])\)"   # Func('string-arg')
    r"|(?:[\w.]+)\(([\d, ]+)\)"        # Func(2026, 3, 24)
)


def _sanitize_python_repr(text: str) -> str:
    """Replace common non-literal function calls with their string arg."""
    def _repl(m: re.Match) -> str:
        if m.group(1) is not None:      # Timestamp('2026-03-24')  →  '2026-03-24'
            return m.group(1)
        return f"'{m.group(2).strip()}'"  # datetime.date(2026,3,24) → '2026,3,24'
    return _FUNC_CALL_RE.sub(_repl, text)


def search_jobs(query: str) -> tuple[str, list[dict]]:
    """
    Search for jobs and return ``(agent_summary, raw_job_dicts)``.

    * **agent_summary** – the LLM's natural-language response.
    * **raw_job_dicts** – structured results from each tool, tagged with
      ``_source`` for downstream normalization / ranking.
    """
    agent = build_agent()
    result = agent.invoke({"messages": [{"role": "user", "content": query}]})
    messages = result["messages"]

    summary = messages[-1].content
    raw_jobs = _extract_tool_results(messages)

    return summary, raw_jobs


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "find me data analyst jobs in New York"
    print(f"Query: {query}\n")
    summary, raw_jobs = search_jobs(query)
    print(summary)
    print(f"\n--- {len(raw_jobs)} raw jobs extracted ---")
