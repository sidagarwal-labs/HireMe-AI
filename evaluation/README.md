# HireMe.AI Evaluation Framework

Comprehensive evaluation suite for measuring the quality and reliability of every component in the HireMe.AI pipeline.

## What's Evaluated

| Component | Module | Metrics |
|---|---|---|
| **Resume Parser** | `eval_parser.py` | Field-level accuracy (name, contact, work experience, education, skills, projects, certifications) against golden reference profiles |
| **Document Generator** | `eval_generator.py` | Faithfulness, Relevance, Coherence, Completeness, Keyword Overlap, Template Adherence |
| **RAG Job Ranker** | `eval_rag.py` | NDCG@3, MRR, Precision@3 using synthetic jobs with known relevance labels |
| **A/B Testing** | `ab_testing.py` | Pairwise LLM-as-judge comparison across models/prompts/temperatures |

## Metrics Explained

### LLM-as-Judge Metrics (0–10 scale, via `metrics.py`)

- **Faithfulness** — Does the generated text contain *only* facts from the candidate data? Detects hallucinated employers, metrics, or credentials.
- **Relevance** — Is the output tailored to the target job description? Are the right skills and experiences emphasized?
- **Coherence** — Is the document well-organized, grammatically correct, and professional?

### Deterministic Metrics (0–1 scale)

- **Completeness** — Checks that key candidate data (name, companies, schools, skills, section headers) appears in the output.
- **Keyword Overlap** — Jaccard/recall overlap between job description keywords and generated text keywords.
- **Template Adherence** — Structural match of markdown headers between the template and the output.
- **Parser Accuracy** — Field-by-field comparison of parsed profiles against golden references (name, contact, companies, schools, skills, certifications).

### Ranking Metrics

- **NDCG@3** — Normalized Discounted Cumulative Gain at rank 3; measures ranking quality with graded relevance.
- **MRR** — Mean Reciprocal Rank; how early the first relevant result appears.
- **Precision@3** — Fraction of top-3 results that are relevant.

## Quick Start

```bash
# From the repo root:

# Install evaluation dependencies
pip install -r evaluation/requirements.txt

# Run the full evaluation suite
python -m evaluation.run_all

# Quick run (parser + RAG + 1 generation pair, no A/B test)
python -m evaluation.run_all --quick

# Run individual components
python -m evaluation.run_all --parser-only
python -m evaluation.run_all --generator-only
python -m evaluation.run_all --rag-only
python -m evaluation.run_all --ab-only
```

## Output

Reports are saved as timestamped JSON files in `evaluation/results/`:

```
evaluation/results/eval_report_full_20260331_201500.json
```

Each report contains:
- Per-component summaries with averaged scores
- Detailed per-test-case results with LLM judge reasoning
- Timing information
- A/B test preference breakdowns

### Example Summary Output

```
--- Summary ---
Parser accuracy:       95.2%
Resume faithfulness:   87.0%
Resume relevance:      82.0%
Resume coherence:      90.0%
Resume completeness:   91.3%
Resume kw overlap:     64.2%
Resume template adh:   85.7%
RAG NDCG@3:            0.9120
RAG MRR:               1.0000
RAG Precision@3:       0.8333
A/B win rates:         {'gpt-4.1-nano': 0.33, 'gpt-4.1-mini': 0.50, 'tie': 0.17}
```

## Test Data

| File | Description |
|---|---|
| `test_data/candidates.json` | 3 candidate profiles (2 realistic + 1 edge-case empty profile) |
| `test_data/jobs.json` | 5 job descriptions (3 realistic + 1 minimal edge case + 1 very long description) |
| `test_data/parser_inputs/` | Raw resume files for parser accuracy testing |

## Edge Cases Tested

- **Empty candidate profile** — No name, no experience, no skills. Tests graceful handling.
- **Minimal job description** — Vague single-sentence JD. Tests robustness.
- **Very long job description** — 300+ word JD with extensive requirements. Tests truncation/focus.
- **Skill mismatch** — Candidate skills don't match job requirements. Tests honest tailoring vs. hallucination.
- **Cross-domain** — Data analyst applying to ML engineer role. Tests relevance scoring calibration.

## Extending the Framework

### Adding new test candidates or jobs

Edit `test_data/candidates.json` or `test_data/jobs.json`. Each entry needs a unique `id` field.

### Adding new metrics

Add a function to `metrics.py` following the pattern:

```python
def my_new_metric(generated_text: str, ...) -> dict[str, Any]:
    return {"score": ..., "max_score": ..., "details": ...}
```

Then wire it into the relevant evaluator (`eval_generator.py`, etc.).

### Running A/B tests with custom variants

```python
from evaluation.ab_testing import PipelineVariant, run_ab_test

variant_a = PipelineVariant(name="baseline", model="gpt-4.1-nano", temperature=0.2)
variant_b = PipelineVariant(name="creative", model="gpt-4.1-nano", temperature=0.7)

result = run_ab_test(variant_a, variant_b, candidate_dict, job_dict)
```

## Environment Variables

| Variable | Purpose | Default |
|---|---|---|
| `OPENAI_API_KEY` | Required for LLM generation and LLM-as-judge metrics | — |
| `EVAL_MODEL` | Model used for LLM-as-judge evaluations | `gpt-4.1-nano` |
| `HIREME_USE_FAISS` | Enable FAISS semantic ranking in RAG eval | `0` (BM25 only) |
