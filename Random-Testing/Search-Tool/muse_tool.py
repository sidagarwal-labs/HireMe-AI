import os
import requests
from typing import Optional

from dotenv import load_dotenv
from langchain.tools import tool

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", ".env"), override=True)

api_key = os.getenv("MUSE_API_KEY")


@tool(
    "muse_search",
    parse_docstring=True,
    description=(
        "Search for job listings on The Muse."
        "Use this tool to find jobs by category, location, experience level, or company."
    ),
)
def muse_jobs(
    category: Optional[str] = None,
    location: Optional[str] = None,
    level: Optional[str] = None,
    company: Optional[str] = None,
    page: int = 0,
    descending: Optional[bool] = None,
) -> dict:
    """
    Search for job listings on The Muse.

    Args:
        category: Job category to filter by (e.g., 'Software Engineering', 'Data Science', 'Marketing', 'Sales', 'Design', 'Education', 'Healthcare', 'Finance').
        location: City and state to filter by (e.g., 'New York, NY', 'San Francisco, CA', 'Chicago, IL', 'Flexible / Remote').
        level: Experience level filter. One of 'Internship', 'Entry Level', 'Mid Level', 'Senior Level', 'Management'.
        company: Company name to filter by (e.g., 'Meta', 'Ansys').
        page: Page number for results (0-indexed). Defaults to 0.
        descending: Set to true to sort results in descending order.

    Returns:
        A dictionary with job listings or an error message.

    Raises:
        ValueError: If no job listings are found or if there is an error with the API request.
    """
    try:
        if not api_key:
            return {
                "success": False,
                "error": "Muse API credentials are not configured. Set MUSE_API_KEY.",
            }

        print(f"Calling The Muse API with category='{category}', location='{location}', level='{level}', company='{company}'")

        url = "https://www.themuse.com/api/public/jobs"

        params = {
            "api_key": api_key,
        }

        func_args = {
            "category": category,
            "location": location,
            "level": level,
            "company": company,
            "page": page,
            "descending": descending,
        }

        params.update({k: v for k, v in func_args.items() if v is not None})

        response = requests.get(url, params=params, timeout=10)

        if response.status_code == 401:
            return {
                "success": False,
                "error": "Authentication failed with Muse API. Check API key.",
            }
        elif response.status_code >= 500:
            return {
                "success": False,
                "error": "Muse API is temporarily unavailable. Try again later.",
            }
        elif response.status_code != 200:
            return {
                "success": False,
                "error": f"Muse API error {response.status_code}: {response.text}",
            }

        data = response.json()
        jobs = data.get("results", [])

        if not jobs:
            return {
                "success": False,
                "error": "No jobs found with those filters. Try broadening your search (e.g., different location, remove level filter, or try a different category).",
            }

        return {
            "success": True,
            "data": jobs,
            "total": data.get("total"),
            "page": data.get("page"),
            "page_count": data.get("page_count"),
        }

    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error": "Request to Muse timed out. Try a simpler search.",
        }
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": f"Network error calling Muse: {str(e)}",
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}",
        }
