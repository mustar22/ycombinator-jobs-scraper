import json
from datetime import datetime, timedelta, timezone
from html import escape

from ycombinator_jobs_scraper import waas
from ycombinator_jobs_scraper.ats import resolve_company
from ycombinator_jobs_scraper.normalize import _relative_to_date, normalize_job
from ycombinator_jobs_scraper.waas import fetch_waas

COMPANY = {
    "name": "Acme", "slug": "acme", "batch": "Fall 2025",
    "team_size": 4, "website": "https://acme.com",
    "url": "https://www.ycombinator.com/companies/acme",
}

POSTING = {
    "id": 1, "title": "Founding Engineer",
    "url": "/companies/acme/jobs/abc123-founding-engineer",
    "applyUrl": "https://account.ycombinator.com/authenticate?continue=...",
    "location": "Remote (US)", "type": "Full-time",
    "salaryRange": "$150K - $200K", "equityRange": "1.00% - 2.00%",
    "minExperience": "3+ years", "visa": "US citizen/visa only",
    "createdAt": "5 months",
}


class FakeResponse:
    def __init__(self, text="", status_code=200):
        self.text = text
        self.status_code = status_code


class FakeSession:
    def __init__(self, pages):
        self.pages = pages
        self.requested = []

    def get(self, url, timeout=None, headers=None):
        self.requested.append(url)
        if url in self.pages:
            return FakeResponse(self.pages[url])
        return FakeResponse("", status_code=404)


def page_html(props):
    return f'<div data-page="{escape(json.dumps({"props": props}))}"></div>'


def days_ago(iso_date):
    return (datetime.now(timezone.utc).date() - datetime.fromisoformat(iso_date).date()).days


def test_relative_to_date_assumes_oldest():
    assert 170 <= days_ago(_relative_to_date("5 months")) <= 190
    assert days_ago(_relative_to_date("14 days")) == 15
    assert days_ago(_relative_to_date("about 1 year")) >= 365
    assert _relative_to_date("just now") is None
    assert _relative_to_date(None) is None


def test_normalize_waas_posting():
    job = normalize_job(POSTING, "waas", COMPANY, "acme", "now")
    assert job["title"] == "Founding Engineer"
    assert job["job_url"] == "https://www.ycombinator.com/companies/acme/jobs/abc123-founding-engineer"
    assert "account.ycombinator.com" not in job["job_url"]
    assert job["is_remote"] is True
    assert job["job_type"] == "Full-time"
    assert job["salary_range"] == "$150K - $200K"
    assert job["equity_range"] == "1.00% - 2.00%"
    assert job["visa"] == "US citizen/visa only"
    assert days_ago(job["date_posted"]) > 150


def test_fetch_waas_parses_postings():
    waas.reset_stats()
    session = FakeSession(
        {"https://www.ycombinator.com/companies/acme/jobs": page_html({"jobPostings": [POSTING]})})
    jobs = fetch_waas(session, "acme")
    assert jobs == [POSTING]
    assert waas.zero_postings_warning() is None


def test_fetch_waas_descriptions_from_detail_page():
    detail = {"job": {"description": "### Build stuff"}}
    session = FakeSession({
        "https://www.ycombinator.com/companies/acme/jobs": page_html({"jobPostings": [POSTING]}),
        "https://www.ycombinator.com" + POSTING["url"]: page_html(detail),
    })
    jobs = fetch_waas(session, "acme", descriptions=True)
    assert jobs[0]["description"] == "### Build stuff"


def test_zero_postings_canary():
    waas.reset_stats()
    session = FakeSession({
        f"https://www.ycombinator.com/companies/c{i}/jobs": page_html({"jobPostings": []})
        for i in range(3)})
    for i in range(3):
        assert fetch_waas(session, f"c{i}") is None
    assert "format may have changed" in waas.zero_postings_warning()


def test_resolve_cached_miss_goes_straight_to_waas():
    class FakeCache(dict):
        def get(self, slug):
            return dict.get(self, slug)

        def set(self, slug, ats, ats_slug):
            self[slug] = {"ats": ats, "ats_slug": ats_slug}

    cache = FakeCache(acme={"ats": None, "ats_slug": None})
    session = FakeSession(
        {"https://www.ycombinator.com/companies/acme/jobs": page_html({"jobPostings": [POSTING]})})
    resolved = resolve_company(session, COMPANY, cache=cache, delay=0)
    assert resolved == ("waas", "acme", [POSTING])
    assert cache["acme"] == {"ats": "waas", "ats_slug": "acme"}
    # cached miss must not retrigger ATS probing or website detection
    assert session.requested == ["https://www.ycombinator.com/companies/acme/jobs"]
