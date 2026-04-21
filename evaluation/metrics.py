"""
Evaluation metrics for HireMe.AI.

Provides both deterministic (keyword overlap, structural checks) and
LLM-as-judge metrics (faithfulness, relevance, coherence) for evaluating
resume parsing, document generation, and job ranking quality.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

from langchain_openai import ChatOpenAI


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_eval_llm() -> ChatOpenAI:
    """Return a lightweight LLM used for LLM-as-judge evaluations."""
    return ChatOpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        model=os.getenv("EVAL_MODEL", "gpt-4.1-nano"),
        temperature=0.0,
    )


def _extract_score(response_text: str) -> float:
    """Pull a numeric score (0-10) from an LLM judge response."""
    match = re.search(r"\b(\d+(?:\.\d+)?)\s*/\s*10\b", response_text)
    if match:
        return min(float(match.group(1)), 10.0)
    match = re.search(r"(?:score|rating)[:\s]*(\d+(?:\.\d+)?)", response_text, re.I)
    if match:
        return min(float(match.group(1)), 10.0)
    nums = re.findall(r"\b(\d+(?:\.\d+)?)\b", response_text)
    for n in nums:
        val = float(n)
        if 0 <= val <= 10:
            return val
    return 0.0


def _llm_judge(prompt: str) -> dict[str, Any]:
    """Run an LLM-as-judge evaluation and return score + reasoning."""
    llm = _get_eval_llm()
    response = llm.invoke(prompt)
    text = response.content
    score = _extract_score(text)
    return {"score": score, "max_score": 10.0, "reasoning": text}


# ---------------------------------------------------------------------------
# 1. FAITHFULNESS — does the output stick to facts in the source data?
# ---------------------------------------------------------------------------

def faithfulness_score(
    generated_text: str,
    source_data: dict[str, Any],
) -> dict[str, Any]:
    """
    Evaluate whether generated text only contains facts present in source_data.
    Uses LLM-as-judge to detect hallucinated employers, dates, metrics, etc.
    """
    prompt = f"""You are an evaluation judge. Score the FAITHFULNESS of the generated
document on a scale of 0-10.

FAITHFULNESS means the generated text contains ONLY facts explicitly present in
the source data. Deduct points for:
- Invented employers, job titles, or companies not in the source
- Fabricated metrics, percentages, or numbers not in the source
- Made-up certifications, degrees, or skills not in the source
- Claims about the candidate that cannot be verified from the source

SOURCE DATA:
{json.dumps(source_data, indent=2)}

GENERATED TEXT:
{generated_text}

Respond with:
Score: X/10
Reasoning: <detailed explanation of any hallucinations found or why the score is high>
"""
    return _llm_judge(prompt)


# ---------------------------------------------------------------------------
# 2. RELEVANCE — is the output tailored to the target job?
# ---------------------------------------------------------------------------

def relevance_score(
    generated_text: str,
    job_description: str,
) -> dict[str, Any]:
    """
    Evaluate how well the generated document is tailored to the job description.
    """
    prompt = f"""You are an evaluation judge. Score the JOB RELEVANCE of the generated
document on a scale of 0-10.

RELEVANCE means the document emphasizes skills, experiences, and qualifications
that match the target job description. High scores require:
- Key job requirements are addressed
- Relevant skills are prominently featured
- Work experience bullets are ordered/worded to match the role
- Irrelevant content is minimized

JOB DESCRIPTION:
{job_description}

GENERATED TEXT:
{generated_text}

Respond with:
Score: X/10
Reasoning: <explanation of how well the document targets this specific role>
"""
    return _llm_judge(prompt)


# ---------------------------------------------------------------------------
# 3. COHERENCE — is the output well-structured and readable?
# ---------------------------------------------------------------------------

def coherence_score(generated_text: str) -> dict[str, Any]:
    """
    Evaluate structural quality, readability, and logical flow.
    """
    prompt = f"""You are an evaluation judge. Score the COHERENCE of the generated
document on a scale of 0-10.

COHERENCE means the document is:
- Well-organized with clear sections
- Grammatically correct
- Free of repetition or contradictions
- Professional in tone
- Logically ordered (e.g., most recent experience first)

GENERATED TEXT:
{generated_text}

Respond with:
Score: X/10
Reasoning: <explanation of structural quality, readability issues, or strengths>
"""
    return _llm_judge(prompt)


# ---------------------------------------------------------------------------
# 4. COMPLETENESS — does the output cover all important candidate data?
# ---------------------------------------------------------------------------

def completeness_score(
    generated_text: str,
    source_data: dict[str, Any],
) -> dict[str, Any]:
    """
    Evaluate whether the output includes all significant candidate information.
    Checks that key sections (experience, education, skills) are represented.
    """
    results: dict[str, Any] = {"checks": {}, "score": 0.0, "max_score": 1.0}
    checks = results["checks"]

    name = source_data.get("name", "")
    checks["name_present"] = bool(name and name.lower() in generated_text.lower())

    work = source_data.get("work_experience", [])
    if work:
        companies = [w.get("company", "") for w in work if w.get("company")]
        found = sum(1 for c in companies if c.lower() in generated_text.lower())
        checks["work_experience_coverage"] = found / len(companies) if companies else 1.0
    else:
        checks["work_experience_coverage"] = 1.0

    edu = source_data.get("education", [])
    if edu:
        schools = [e.get("school", "") for e in edu if e.get("school")]
        found = sum(1 for s in schools if s.lower() in generated_text.lower())
        checks["education_coverage"] = found / len(schools) if schools else 1.0
    else:
        checks["education_coverage"] = 1.0

    skills = source_data.get("skills", {})
    all_skills = (
        skills.get("technical", [])
        + skills.get("tools", [])
        + skills.get("soft_skills", [])
    )
    if all_skills:
        found = sum(1 for s in all_skills if s.lower() in generated_text.lower())
        checks["skills_coverage"] = found / len(all_skills)
    else:
        checks["skills_coverage"] = 1.0

    section_headers = ["summary", "experience", "education", "skills"]
    found_headers = sum(
        1 for h in section_headers if re.search(rf"\b{h}\b", generated_text, re.I)
    )
    checks["section_headers_present"] = found_headers / len(section_headers)

    values = [v for v in checks.values() if isinstance(v, (int, float))]
    results["score"] = sum(values) / len(values) if values else 0.0

    return results


# ---------------------------------------------------------------------------
# 5. TEMPLATE ADHERENCE — does the output follow the expected template?
# ---------------------------------------------------------------------------

def template_adherence_score(
    generated_text: str,
    template_text: str,
) -> dict[str, Any]:
    """
    Check whether the generated output follows the structure of the template.
    Uses a combination of header matching and LLM judgment.
    """
    template_headers = re.findall(r"^#+\s+(.+)", template_text, re.MULTILINE)
    output_headers = re.findall(r"^#+\s+(.+)", generated_text, re.MULTILINE)

    if template_headers:
        matched = 0
        for th in template_headers:
            th_clean = re.sub(r"\[.*?\]", "", th).strip().lower()
            if not th_clean:
                matched += 1
                continue
            for oh in output_headers:
                if th_clean in oh.lower() or oh.lower() in th_clean:
                    matched += 1
                    break
        structural_ratio = matched / len(template_headers)
    else:
        structural_ratio = 1.0

    return {
        "structural_match": structural_ratio,
        "template_headers": template_headers,
        "output_headers": output_headers,
        "score": structural_ratio,
        "max_score": 1.0,
    }


# ---------------------------------------------------------------------------
# 6. KEYWORD OVERLAP — deterministic relevance proxy
# ---------------------------------------------------------------------------

def keyword_overlap_score(
    generated_text: str,
    job_description: str,
) -> dict[str, Any]:
    """
    Compute keyword overlap between generated text and job description.
    Returns Jaccard similarity and matched/missed keywords.
    """
    stop = {
        "the", "and", "for", "with", "you", "your", "are", "will", "job",
        "role", "our", "that", "this", "from", "have", "has", "been", "can",
        "all", "but", "not", "they", "their", "what", "when", "who", "how",
        "also", "more", "other", "into", "over", "such", "than", "its",
        "about", "would", "could", "should",
    }
    _word_re = re.compile(r"[a-zA-Z][a-zA-Z0-9+#.-]+")

    def _tokens(text: str) -> set[str]:
        return {t for t in _word_re.findall(text.lower()) if t not in stop and len(t) > 2}

    jd_tokens = _tokens(job_description)
    gen_tokens = _tokens(generated_text)

    if not jd_tokens:
        return {"jaccard": 0.0, "recall": 0.0, "matched": [], "missed": [], "score": 0.0, "max_score": 1.0}

    matched = jd_tokens & gen_tokens
    missed = jd_tokens - gen_tokens
    union = jd_tokens | gen_tokens
    jaccard = len(matched) / len(union) if union else 0.0
    recall = len(matched) / len(jd_tokens) if jd_tokens else 0.0

    return {
        "jaccard": round(jaccard, 4),
        "recall": round(recall, 4),
        "matched": sorted(matched),
        "missed": sorted(missed),
        "score": round(recall, 4),
        "max_score": 1.0,
    }


# ---------------------------------------------------------------------------
# 7. PARSER ACCURACY — compare parsed profile against golden reference
# ---------------------------------------------------------------------------

def parser_accuracy_score(
    parsed: dict[str, Any],
    golden: dict[str, Any],
) -> dict[str, Any]:
    """
    Compare a parsed candidate profile against a golden reference.
    Checks field-level accuracy for name, contact, work experience, etc.
    """
    checks: dict[str, float] = {}

    # Name
    checks["name"] = 1.0 if parsed.get("name", "").strip().lower() == golden.get("name", "").strip().lower() else 0.0

    # Contact fields
    golden_contact = golden.get("contact", {})
    parsed_contact = parsed.get("contact", {})
    contact_fields = ["email", "phone", "website"]
    contact_matches = sum(
        1 for f in contact_fields
        if parsed_contact.get(f, "").strip().lower() == golden_contact.get(f, "").strip().lower()
    )
    checks["contact"] = contact_matches / len(contact_fields)

    # Work experience count
    golden_work = golden.get("work_experience", [])
    parsed_work = parsed.get("work_experience", [])
    if golden_work:
        checks["work_experience_count"] = min(len(parsed_work), len(golden_work)) / len(golden_work)
        # Check company names
        golden_companies = {w.get("company", "").strip().lower() for w in golden_work}
        parsed_companies = {w.get("company", "").strip().lower() for w in parsed_work}
        overlap = golden_companies & parsed_companies
        checks["work_companies_matched"] = len(overlap) / len(golden_companies) if golden_companies else 1.0
    else:
        checks["work_experience_count"] = 1.0 if not parsed_work else 0.5
        checks["work_companies_matched"] = 1.0

    # Education
    golden_edu = golden.get("education", [])
    parsed_edu = parsed.get("education", [])
    if golden_edu:
        checks["education_count"] = min(len(parsed_edu), len(golden_edu)) / len(golden_edu)
        golden_schools = {e.get("school", "").strip().lower() for e in golden_edu}
        parsed_schools = {e.get("school", "").strip().lower() for e in parsed_edu}
        overlap = golden_schools & parsed_schools
        checks["education_schools_matched"] = len(overlap) / len(golden_schools) if golden_schools else 1.0
    else:
        checks["education_count"] = 1.0 if not parsed_edu else 0.5
        checks["education_schools_matched"] = 1.0

    # Skills
    golden_skills = golden.get("skills", {})
    parsed_skills = parsed.get("skills", {})
    for category in ["technical", "tools", "soft_skills"]:
        g_list = {s.strip().lower() for s in golden_skills.get(category, [])}
        p_list = {s.strip().lower() for s in parsed_skills.get(category, [])}
        if g_list:
            overlap = g_list & p_list
            checks[f"skills_{category}"] = len(overlap) / len(g_list)
        else:
            checks[f"skills_{category}"] = 1.0 if not p_list else 0.5

    # Projects
    golden_projects = golden.get("projects", [])
    parsed_projects = parsed.get("projects", [])
    if golden_projects:
        checks["projects_count"] = min(len(parsed_projects), len(golden_projects)) / len(golden_projects)
    else:
        checks["projects_count"] = 1.0 if not parsed_projects else 0.5

    # Certifications
    golden_certs = golden.get("certifications", [])
    parsed_certs = parsed.get("certifications", [])
    if golden_certs:
        checks["certifications_count"] = min(len(parsed_certs), len(golden_certs)) / len(golden_certs)
    else:
        checks["certifications_count"] = 1.0 if not parsed_certs else 0.5

    values = list(checks.values())
    overall = sum(values) / len(values) if values else 0.0

    return {
        "field_scores": checks,
        "score": round(overall, 4),
        "max_score": 1.0,
    }
