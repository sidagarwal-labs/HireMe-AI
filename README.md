# HireMe.AI
By: @sidagarwal-labs & @jeffsengsy

An AI-powered resume & cover letter builder with integrated job search. Upload your resume, paste a job description, and get tailored documents — or search across multiple job boards and let RAG rank the best matches.

**Live App:** [![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)]([https://YOUR-APP-URL.streamlit.app](https://hireme-ai.streamlit.app/))

[![PPT](https://github.com/sidagarwal-labs/HireMe-AI/blob/main/HireMe_AI_Presentation.pdf)], [![Doc](https://github.com/sidagarwal-labs/HireMe-AI/blob/main/Project%20Documentation.pdf)]

---

## What It Does

1. **Resume Parsing** — Upload a PDF/DOCX/TXT resume → LLM extracts structured data into a validated JSON profile (Pydantic schema)
2. **Document Generation** — Combines your profile + a job description + markdown templates → generates a tailored resume and cover letter via parallel LLM calls
3. **Job Search** — Natural language search across Adzuna, The Muse, and JobSpy → results ranked using hybrid BM25 + FAISS with Reciprocal Rank Fusion (RRF)
4. **One-Click Tailoring** — Select a job from search results → auto-fills the resume builder for instant tailoring

---

## Evaluation Results

Ran a full evaluation suite with LLM-as-judge scoring + deterministic metrics:

| Metric | Resume | Cover Letter |
|---|---|---|
| Faithfulness (0–10) | 6.5 | 5.5 |
| Coherence (0–10) | 8.3 | 7.1 |
| Completeness (0–1) | 0.93 | — |
| Template Adherence (0–1) | 0.95+ | 0.95+ |

**A/B Test:** gpt-4.1-nano beat gpt-4.1-mini on quality, relevance, and faithfulness while being 2× faster

**Known limitation:** Empty/minimal candidate profiles cause hallucination — the model invents credentials when given no data.

---

## Architecture

```
Resume (PDF/DOCX/TXT)          Job Description (paste or search)
        │                                    │
        ▼                                    │
   LLM Parser ──► CandidateProfile (JSON)    │
                        │                    │
                        ▼                    ▼
                  Prompt Builder (template + profile + JD)
                        │
              ┌─────────┴─────────┐
              ▼                   ▼
       Resume Writer LLM   Cover Letter Writer LLM   ← parallel (ThreadPoolExecutor)
              │                   │
              ▼                   ▼
       Formatted Markdown   Formatted Markdown
```

```
Job Search Flow:
  Query ──► LLM Agent routes to Adzuna / Muse / JobSpy
                    │
                    ▼
           Normalize to common schema
                    │
            ┌───────┴───────┐
            ▼               ▼
          BM25           FAISS (OpenAI embeddings)
            └───────┬───────┘
                    ▼
         Reciprocal Rank Fusion ──► Top-N ranked jobs
```

---

## Tech Stack

| Layer | Tools |
|---|---|
| **Frontend** | Streamlit (multi-page app) |
| **LLM Orchestration** | LangChain, LangGraph, OpenAI GPT models |
| **Data Validation** | Pydantic schemas (`CandidateProfile`, `JobPosting`) |
| **RAG Ranking** | BM25 (rank-bm25) + FAISS (faiss-cpu) + OpenAI embeddings |
| **Job Search APIs** | Adzuna API, The Muse API, python-jobspy (scraper) |
| **Document Parsing** | pypdf, python-docx |
| **Document Export** | python-docx (Word), Markdown |

---

## What we Learned

- Building end-to-end LLM applications with structured outputs (Pydantic + LangChain)
- Hybrid retrieval (BM25 + dense embeddings + RRF) for ranking without a traditional vector DB
- Prompt engineering for faithfulness — explicit anti-hallucination instructions matter
- LLM-as-judge evaluation — using one model to score another's outputs
- Agentic tool use — letting the LLM decide which APIs to call based on user intent
- Streamlit session state management for multi-page apps with shared data

---

## Key Implementation Details

### LLM-Powered Resume Parsing
- Supports PDF, DOCX, TXT, and image formats
- LLM extracts structured fields into a `CandidateProfile` Pydantic model
- Robust JSON extraction handles markdown code blocks and malformed responses
- Explicit instructions: *"Do NOT invent employers, dates, credentials, or metrics"*

### Prompt Engineering
- Templates separate structure from content — LLM fills in the blanks
- All user inputs (resume text, job descriptions) treated as untrusted data
- Prompt injection defense built into system prompts

### Hybrid RAG for Job Ranking
- **BM25** — lexical/keyword matching (rank-bm25)
- **FAISS** — semantic similarity via OpenAI `text-embedding-3-small` embeddings
- **Reciprocal Rank Fusion** — combines rankings: $\text{score} = \sum \frac{1}{k + \text{rank} + 1}$ with $k=60$
- Jobs normalized from 3 different API schemas into a common `NormalizedJob` format

### Agentic Job Search
- LangChain agent decides which APIs to call based on query intent
- Adzuna for keyword/salary filtering, Muse for category browsing, JobSpy for broad multi-board scraping
- Full job descriptions fetched from web pages when summaries are incomplete

### Parallel Generation
- Resume and cover letter generated concurrently via `ThreadPoolExecutor`
- Optional LLM tool calling loop for keyword extraction and location normalization

---
