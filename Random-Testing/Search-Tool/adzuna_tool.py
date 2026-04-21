import os
import requests
from typing import Optional, Literal

from dotenv import load_dotenv
from langchain.tools import tool

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", ".env"), override=True)

app_id = os.getenv("ADZUNA_APP_ID")
app_key = os.getenv("ADZUNA_APP_KEY")


@tool(
    "adzuna_search",
    parse_docstring=True,
    description=(
        "Search for job listings on Adzuna."
        "Use this tool to find jobs based on title, location, and salary range."
    ),
)
def adzuna_jobs(
    what: str,
    country: Optional[str] = "us",
    where: Optional[str] = None,
    results_per_page: int = 10,
    salary_min: Optional[int] = None,
    salary_max: Optional[int] = None,
    full_time: Optional[Literal["1"]] = None,
    part_time: Optional[Literal["1"]] = None,
    contract: Optional[Literal["1"]] = None,
    permanent: Optional[Literal["1"]] = None,
    sort_by: Optional[str] = None,
    max_days_old: Optional[int] = None,
    category: Optional[str] = None,
    company: Optional[str] = None,
    distance: Optional[int] = None,
    what_exclude: Optional[str] = None,
    title_only: Optional[str] = None,
) -> dict:
    """
    Search for job listings on Adzuna.

    Args:
        what: Job title or keywords to search for (e.g., 'data scientist').
        country: Two-letter country code (e.g., 'us', 'gb', 'ca'). Defaults to 'us'.
        where: Geographic city or region to filter by (e.g., 'New York', 'Charlotte'). Must be a real place name — do NOT pass 'Remote' here. To search for remote jobs, include 'remote' in the `what` field instead (e.g., what='data scientist remote').
        results_per_page: Number of results to return (1-50). Defaults to 10.
        salary_min: Minimum annual salary filter.
        salary_max: Maximum annual salary filter.
        full_time: Set to 1 to return only full-time positions.
        part_time: Set to 1 to return only part-time positions.
        contract: Set to 1 to return only contract positions.
        permanent: Set to 1 to return only permanent positions.
        sort_by: How to sort results. One of 'default', 'hybrid', 'date', 'salary', 'relevance'.
        max_days_old: Only return jobs posted within this many days.
        category: Adzuna category tag (e.g., 'it-jobs', 'healthcare-nursing-jobs', 'engineering-jobs', 'accounting-finance-jobs').
        company: Filter by company name.
        distance: Radius in km from the location to search within.
        what_exclude: Keywords to exclude from results (e.g., 'intern junior').
        title_only: Keywords that must appear in the job title only.

    Returns:
        A dictionary with job listings or an error message.

    Raises:
        ValueError: If no job listings are found or if there is an error with the API request.
    """
    try:
        if not app_id or not app_key:
            return {
                "success": False,
                "error": "Adzuna credentials are not configured. Set ADZUNA_APP_ID and ADZUNA_APP_KEY.",
            }

        # Adzuna `where` is geographic-only; "remote" must go in the keyword query
        if where and where.strip().lower() == "remote":
            what = f"{what} remote"
            where = None

        print(f"Calling Adzuna API with query='{what}'")

        url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/1"

        params = {
            "app_id": app_id,
            "app_key": app_key,
            "content-type": "application/json",
        }

        func_args = {
            "what": what,
            "where": where,
            "results_per_page": results_per_page,
            "salary_min": salary_min,
            "salary_max": salary_max,
            "full_time": full_time,
            "part_time": part_time,
            "contract": contract,
            "permanent": permanent,
            "sort_by": sort_by,
            "max_days_old": max_days_old,
            "category": category,
            "company": company,
            "distance": distance,
            "what_exclude": what_exclude,
            "title_only": title_only,
        }

        params.update({k: v for k, v in func_args.items() if v is not None})

        response = requests.get(url, params=params, timeout=10)

        if response.status_code == 400:
            return {
                "success": False,
                "error": "Bad request to Adzuna. You may have used an invalid parameter combination. Try simplifying your search.",
            }
        elif response.status_code == 401:
            return {
                "success": False,
                "error": "Authentication failed with Adzuna API. Check API credentials.",
            }
        elif response.status_code >= 500:
            return {
                "success": False,
                "error": "Adzuna API is temporarily unavailable. Try again in a moment.",
            }
        elif response.status_code != 200:
            return {
                "success": False,
                "error": f"Adzuna API error {response.status_code}: {response.text}",
            }

        data = response.json()
        jobs = data.get("results", [])

        if not jobs:
            return {
                "success": False,
                "error": f"No jobs found for '{what}'. Try different keywords, remove filters, or search a different location.",
            }

        return {
            "success": True,
            "data": jobs,
            "count": data.get("count", len(jobs)),
        }

    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error": "Request to Adzuna timed out. Try again with a simpler query.",
        }
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": f"Network error calling Adzuna: {str(e)}. Check your connection.",
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}",
        }
