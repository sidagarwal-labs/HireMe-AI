# HireMeAI

HireMeAI is an AI-powered job coach that helps users build stronger job applications by tailoring resume content to specific roles.

## What It Does

- Generates resume content from a user profile and target job description.
- Supports multiple model providers through `.env` config (`azure`, `openai`, `local`).

## Deploying The Streamlit App

Deploy the app with Streamlit Community Cloud using:

- App file: `Resume_CV_Tailor.py`
- Python version: `3.11` via `runtime.txt`
- Dependencies: `requirements.txt`

### Required Secrets

Add these secrets in the Streamlit Cloud dashboard or locally in `.streamlit/secrets.toml`:

```toml
OPENAI_API_KEY = "sk-..."
OPENAI_MODEL_RESUME = "gpt-5-nano"
OPENAI_MODEL_PARSER = "gpt-5-nano"
OPENAI_MODEL_COVERLETTER = "gpt-5-nano"
```

The app loads both `.env` and Streamlit secrets. In production, Streamlit secrets should be your source of truth so deployed users can use the hosted LLM-backed workflow without providing their own keys.

### Optional Job Search Secrets

The job search page can also use:

```toml
ADZUNA_APP_ID = ""
ADZUNA_APP_KEY = ""
MUSE_API_KEY = ""
```

If those are omitted, the main resume-tailoring app still works and the search tools return clear configuration errors instead of breaking app startup.
