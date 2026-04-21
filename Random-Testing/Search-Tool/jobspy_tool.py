from typing import Optional, List
from langchain.tools import tool
from jobspy import scrape_jobs


@tool(
    "jobspy_search",
    parse_docstring=True,
    description=(
        "Search for job listings across multiple job boards (LinkedIn, Indeed, Glassdoor, ZipRecruiter, Google Jobs). "
        "Use this tool for broad searches across many sources at once, remote job filtering, or when other tools return few results."
    ),
)
def jobspy_jobs(
    search_term: str,
    location: Optional[str] = None,
    site_name: Optional[List[str]] = None,
    results_wanted: int = 10,
    hours_old: Optional[int] = None,
    job_type: Optional[str] = None,
    is_remote: Optional[bool] = None,
    country_indeed: Optional[str] = "USA",
    distance: Optional[int] = None,
) -> dict:
    """
    Search for job listings across multiple job boards simultaneously.

    Args:
        search_term: Job title or keywords to search for (e.g., 'data scientist').
        location: City and state to search in (e.g., 'Charlotte, NC', 'New York, NY').
        site_name: List of job boards to search. Options: 'linkedin', 'indeed', 'glassdoor', 'zip_recruiter', 'google'. Defaults to all.
        results_wanted: Number of results to return per site (default 10).
        hours_old: Only return jobs posted within this many hours (applies to Indeed, LinkedIn, Glassdoor).
        job_type: Filter by job type. One of 'fulltime', 'parttime', 'internship', 'contract'.
        is_remote: Set to true to filter for remote positions only.
        country_indeed: Country for Indeed/Glassdoor searches (e.g., 'USA', 'UK', 'Canada'). Defaults to 'USA'.
        distance: Search radius in miles from the location.

    Returns:
        A dictionary with job listings or an error message.
    """
    try:
        sites = site_name or ["linkedin", "indeed", "glassdoor", "zip_recruiter", "google"]
        print(f"Calling JobSpy with search_term='{search_term}', location='{location}', sites={sites}")

        kwargs = {
            "site_name": sites,
            "search_term": search_term,
            "results_wanted": results_wanted,
        }

        if location:
            kwargs["location"] = location
        if hours_old:
            kwargs["hours_old"] = hours_old
        if job_type:
            kwargs["job_type"] = job_type
        if is_remote is not None:
            kwargs["is_remote"] = is_remote
        if distance:
            kwargs["distance"] = distance
        if country_indeed:
            kwargs["country_indeed"] = country_indeed

        df = scrape_jobs(**kwargs)

        if df.empty:
            return {
                "success": False,
                "error": f"No jobs found for '{search_term}'. Try different keywords, a broader location, or remove filters.",
            }

        # Convert DataFrame to JSON-safe dicts (avoids Timestamp / NaT objects
        # that break downstream parsing with ast.literal_eval / json.loads).
        import json as _json
        jobs = _json.loads(df.to_json(orient="records", date_format="iso"))

        return {
            "success": True,
            "data": jobs,
            "count": len(jobs),
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error calling JobSpy: {str(e)}",
        }
