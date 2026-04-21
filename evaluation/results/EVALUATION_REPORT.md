# HireMe.AI — Evaluation Report

**Date:** March 31, 2026  
**Total Runtime:** 3,545 seconds (~59 minutes)  
**Test Matrix:** 3 candidates × 5 job descriptions = 15 generation pairs  

---

## Executive Summary

| Component | Key Metric | Score | Verdict |
|---|---|---|---|
| Resume Parser | Field-level accuracy | **100.0%** | ✅ Excellent |
| Resume Generation | Avg. faithfulness / coherence / completeness | **64.7% / 82.7% / 93.3%** | ⚠️ Good (edge cases lower avg) |
| Cover Letter Generation | Avg. faithfulness / coherence | **54.7% / 70.7%** | ⚠️ Moderate |
| RAG Job Ranking | NDCG@3 / MRR / Precision@3 | **1.00 / 1.00 / 1.00** | ✅ Perfect |
| A/B Test (nano vs mini) | Win rate for gpt-4.1-nano | **100%** (3/3 criteria) | ✅ Nano wins |

---

## 1. Resume Parser Evaluation

**Input:** `sample_resume.txt` (Taylor Morgan)  
**Method:** Parse resume → compare extracted fields against golden reference profile  
**Time:** 33.75 seconds  

| Field | Accuracy |
|---|---|
| Name | 100% |
| Contact (email, phone, website) | 100% |
| Work experience count | 100% |
| Work companies matched | 100% |
| Education count | 100% |
| Education schools matched | 100% |
| Skills — technical | 100% |
| Skills — tools | 100% |
| Skills — soft skills | 100% |
| Projects count | 100% |
| Certifications count | 100% |
| **Overall** | **100%** |

**Finding:** The LLM-based parser perfectly extracts all structured fields from a plain-text resume.

---

## 2. Document Generation Evaluation

### 2.1 Aggregate Scores (averaged across all 15 pairs)

#### Resume

| Metric | Type | Avg. Score | Scale |
|---|---|---|---|
| Faithfulness | LLM-as-judge | **6.47 / 10** (64.7%) | 0–10 |
| Relevance | LLM-as-judge | **3.53 / 10** (35.3%) | 0–10 |
| Coherence | LLM-as-judge | **8.27 / 10** (82.7%) | 0–10 |
| Completeness | Deterministic | **93.3%** | 0–1 |
| Keyword Overlap (recall) | Deterministic | **30.7%** | 0–1 |
| Template Adherence | Deterministic | **94.9%** | 0–1 |

#### Cover Letter

| Metric | Type | Avg. Score | Scale |
|---|---|---|---|
| Faithfulness | LLM-as-judge | **5.47 / 10** (54.7%) | 0–10 |
| Relevance | LLM-as-judge | **3.40 / 10** (34.0%) | 0–10 |
| Coherence | LLM-as-judge | **7.07 / 10** (70.7%) | 0–10 |
| Keyword Overlap (recall) | Deterministic | **33.6%** | 0–1 |
| Template Adherence | Deterministic | **100%** | 0–1 |

### 2.2 Per-Pair Breakdown — Resume Scores

| Candidate | Job | Faith. | Relev. | Coher. | Compl. | KW Overlap | Template | Time (s) |
|---|---|---|---|---|---|---|---|---|
| candidate_1 | Data Analyst | 9.0 | 8.0 | 8.0 | 100% | 41.7% | 100% | 74.3 |
| candidate_1 | Sr. Software Engineer | 9.0 | 2.0 | 8.0 | 100% | 23.1% | 100% | 89.9 |
| candidate_1 | ML Engineer | 8.0 | 3.0 | 8.0 | 100% | 39.5% | 100% | 68.2 |
| candidate_1 | *(edge) Minimal JD* | 9.0 | 4.0 | 8.0 | 100% | 20.0% | 100% | 80.1 |
| candidate_1 | *(edge) Very Long JD* | 8.0 | 2.0 | 8.0 | 100% | 11.9% | 100% | 92.3 |
| candidate_2 | Data Analyst | 9.0 | 4.0 | 9.0 | 100% | 33.3% | 100% | 103.7 |
| candidate_2 | Sr. Software Engineer | 10.0 | 6.0 | 9.0 | 100% | 43.6% | 100% | 74.7 |
| candidate_2 | ML Engineer | 9.0 | 3.0 | 8.0 | 100% | 55.3% | 100% | 100.6 |
| candidate_2 | *(edge) Minimal JD* | 9.0 | 4.0 | 9.0 | 100% | 20.0% | 100% | 59.3 |
| candidate_2 | *(edge) Very Long JD* | 9.0 | 4.0 | 9.0 | 100% | 24.6% | 100% | 57.7 |
| *(edge) Empty* | Data Analyst | 2.0 | 4.0 | 8.0 | 80% | 16.7% | 100% | 52.2 |
| *(edge) Empty* | Sr. Software Engineer | 2.0 | 3.0 | 8.0 | 80% | 12.8% | 100% | 51.0 |
| *(edge) Empty* | ML Engineer | 2.0 | 3.0 | 8.0 | 80% | 13.2% | 100% | 49.3 |
| *(edge) Empty* | *(edge) Minimal JD* | 0.0 | 1.0 | 8.0 | 80% | 100% | 23.1% | 47.7 |
| *(edge) Empty* | *(edge) Very Long JD* | 2.0 | 2.0 | 8.0 | 80% | 4.8% | 100% | 83.0 |

### 2.3 Per-Pair Breakdown — Cover Letter Scores

| Candidate | Job | Faith. | Relev. | Coher. | KW Overlap | Template | 
|---|---|---|---|---|---|---|
| candidate_1 | Data Analyst | 8.0 | 7.0 | 8.0 | 41.7% | 100% |
| candidate_1 | Sr. Software Engineer | 4.0 | 2.0 | 7.0 | 25.6% | 100% |
| candidate_1 | ML Engineer | 8.0 | 4.0 | 8.0 | 44.7% | 100% |
| candidate_1 | *(edge) Minimal JD* | 8.0 | 4.0 | 8.0 | 20.0% | 100% |
| candidate_1 | *(edge) Very Long JD* | 4.0 | 2.0 | 8.0 | 34.9% | 100% |
| candidate_2 | Data Analyst | 4.0 | 4.0 | 7.0 | 31.3% | 100% |
| candidate_2 | Sr. Software Engineer | 8.0 | 4.0 | 8.0 | 38.5% | 100% |
| candidate_2 | ML Engineer | 8.0 | 3.0 | 8.0 | 50.0% | 100% |
| candidate_2 | *(edge) Minimal JD* | 8.0 | 4.0 | 8.0 | 20.0% | 100% |
| candidate_2 | *(edge) Very Long JD* | 8.0 | 4.0 | 8.0 | 31.8% | 100% |
| *(edge) Empty* | Data Analyst | 2.0 | 2.0 | 4.0 | 16.7% | 100% |
| *(edge) Empty* | Sr. Software Engineer | 2.0 | 4.0 | 8.0 | 48.7% | 100% |
| *(edge) Empty* | ML Engineer | 0.0 | 2.0 | 4.0 | 36.8% | 100% |
| *(edge) Empty* | *(edge) Minimal JD* | 2.0 | 1.0 | 4.0 | 20.0% | 100% |
| *(edge) Empty* | *(edge) Very Long JD* | 8.0 | 4.0 | 8.0 | 43.7% | 100% |

### 2.4 Key Observations

**Strengths:**
- **Template adherence is near-perfect** (94.9% resume, 100% cover letter) — the LLM reliably follows the markdown template structure.
- **Completeness is consistently high** (100% for all real candidates) — the model includes all candidate data in the output.
- **Coherence is strong** (8–9/10 for real candidates) — outputs are well-organized and professional.

**Weaknesses:**
- **Faithfulness drops sharply for the empty candidate** (0–2/10) — the model hallucinated entire work histories, skills, and credentials when given no data. This is the most critical failure mode.
- **Relevance scores are low for cross-domain pairs** (2–3/10 when a data analyst applies to an ML Engineer role) — expected, but shows the model doesn't gracefully handle skill mismatches.
- **Keyword overlap is naturally modest** (~30%) because resumes use varied phrasing, not verbatim JD keywords.

**Edge Case Findings:**
- **Empty candidate + Minimal JD** is the worst-case scenario: faithfulness = 0/10 and template adherence drops to 23.1% as the model produces unstructured filler text.
- **Very long JDs** cause slightly lower relevance — the model struggles to focus on the most important requirements.

---

## 3. RAG Job Ranking Evaluation

**Method:** BM25 lexical ranking on synthetic jobs with known relevance labels (0=irrelevant, 1=somewhat, 2=relevant, 3=highly relevant).

### Test Case 1: "data analyst SQL Tableau dashboards"

| Rank | Job Title | Company | Relevance |
|---|---|---|---|
| 1 | Business Intelligence Analyst | FinTech Inc | 3 (high) ✅ |
| 2 | Senior Data Analyst | DataCo | 3 (high) ✅ |
| 3 | Data Analyst Intern | StartupX | 2 (relevant) ✅ |
| 4 | Machine Learning Engineer | AI Labs | 0 (irrelevant) |
| 5 | Marketing Coordinator | BrandCo | 0 (irrelevant) |

### Test Case 2: "software engineer Python microservices AWS"

| Rank | Job Title | Company | Relevance |
|---|---|---|---|
| 1 | Backend Software Engineer | CloudScale | 3 (high) ✅ |
| 2 | Python Developer | DataPipe | 3 (high) ✅ |
| 3 | DevOps Engineer | InfraTeam | 1 (somewhat) ✅ |
| 4 | Frontend Developer | WebCraft | 0 (irrelevant) |

### Ranking Metrics

| Metric | Test Case 1 | Test Case 2 | Average |
|---|---|---|---|
| NDCG@3 | 1.0000 | 1.0000 | **1.0000** |
| MRR | 1.0000 | 1.0000 | **1.0000** |
| Precision@3 | 1.0000 | 1.0000 | **1.0000** |

**Finding:** BM25 achieves perfect ranking on these test cases. Relevant jobs consistently appear at the top, irrelevant jobs at the bottom.

---

## 4. A/B Testing: gpt-4.1-nano vs gpt-4.1-mini

**Test Pair:** candidate_1 (Taylor Morgan) × Data Analyst at Acme Analytics  
**Criteria evaluated:** Overall Quality, Job Relevance, Faithfulness to Candidate Data  

| Criteria | Winner | 
|---|---|
| Overall Quality | **gpt-4.1-nano** |
| Job Relevance | **gpt-4.1-nano** |
| Faithfulness to Candidate Data | **gpt-4.1-nano** |

**Timing:**
- gpt-4.1-nano: **6.48s** (generation only)
- gpt-4.1-mini: **12.15s** (generation only)

**Finding:** gpt-4.1-nano wins all 3 criteria while being ~2× faster. For this use case, the smaller model is both better and cheaper.

---

## 5. Failure Modes & Edge Cases

| Scenario | What Happens | Severity |
|---|---|---|
| **Empty candidate profile** | Model hallucinated entire resume from nothing — fake employers, fake skills, fake metrics | 🔴 Critical |
| **Minimal job description** ("help with data stuff") | Output is generic and unfocused; template structure may break down | 🟡 Medium |
| **Very long job description** (300+ words) | Model struggles to prioritize; relevance scores drop | 🟡 Medium |
| **Cross-domain mismatch** (data analyst → ML engineer) | Low relevance but honest — model doesn't fabricate ML credentials | 🟢 Acceptable |
| **Well-matched pair** (data analyst → data analyst) | High scores across all metrics (9/10 faithfulness, 8/10 relevance) | ✅ Strong |

---

## 6. Recommendations

1. **Add guardrails for empty/minimal input** — Validate that the candidate profile has minimum viable data (name, at least one work experience) before generating. Currently the model hallucinates when given nothing.

2. **Improve relevance for mismatched roles** — Consider adding a pre-generation step that identifies which candidate skills are transferable to the target role, so the prompt can focus on those.

3. **Keyword optimization** — The 30% keyword overlap is typical for natural-language resumes, but adding a post-processing step to inject missing high-value JD keywords (e.g., specific tool names) could improve ATS pass rates.

4. **Expand test coverage** — Add `.docx` and `.pdf` resume files to `test_data/parser_inputs/` to test parser accuracy across formats. Add more A/B test pairs (e.g., different temperatures, prompt variants).

5. **Monitor faithfulness** — The cover letter showed lower faithfulness (54.7% avg) than resumes (64.7%). Consider tightening the cover letter prompt to reduce creative embellishment.

---

## Appendix: Metrics Definitions

| Metric | Type | Scale | Description |
|---|---|---|---|
| Faithfulness | LLM-as-judge | 0–10 | Output contains only facts from candidate data; no hallucinations |
| Relevance | LLM-as-judge | 0–10 | Output is tailored to the target job description |
| Coherence | LLM-as-judge | 0–10 | Output is well-structured, grammatical, and professional |
| Completeness | Deterministic | 0–1 | Key candidate data (name, companies, schools, skills, headers) present |
| Keyword Overlap | Deterministic | 0–1 | Recall of job description keywords in generated text |
| Template Adherence | Deterministic | 0–1 | Structural match of markdown headers to template |
| Parser Accuracy | Deterministic | 0–1 | Field-level match against golden reference profile |
| NDCG@3 | Deterministic | 0–1 | Ranking quality with graded relevance at top 3 |
| MRR | Deterministic | 0–1 | Reciprocal rank of first relevant result |
| Precision@3 | Deterministic | 0–1 | Fraction of top-3 results that are relevant |
