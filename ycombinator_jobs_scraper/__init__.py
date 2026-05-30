"""ycombinator-jobs-scraper: scrape jobs from small early-stage YC startups."""
from .ats import detect_ats_from_website
from .companies import batch_year, fetch_companies, filter_companies
from .normalize import normalize_job, strip_html
from .scraper import make_session, scrape_yc_jobs

__version__ = "0.1.0"
__all__ = [
    "scrape_yc_jobs",
    "make_session",
    "fetch_companies",
    "filter_companies",
    "batch_year",
    "normalize_job",
    "strip_html",
    "detect_ats_from_website",
]
