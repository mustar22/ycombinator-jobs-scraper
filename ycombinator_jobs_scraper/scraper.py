"""Orchestration: company source -> filter -> ATS resolve -> normalized jobs."""
import sys
from datetime import datetime, timezone

import requests

from . import waas
from .ats import resolve_company
from .cache import SlugCache
from .companies import fetch_companies, filter_companies
from .normalize import normalize_job

UA = "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0"


def make_session():
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Accept": "application/json"})
    return s


def scrape_yc_jobs(
    max_team_size=50,
    batches=None,
    years_back=3,
    hiring_only=True,
    keyword=None,
    max_companies=None,
    source="hiring",
    website_detect=True,
    waas_descriptions=False,
    delay=0.25,
    cache_path=".yc_ats_cache.json",
    session=None,
    progress=False,
):
    """Scrape jobs from small early-stage YC startups via their public ATS boards.

    Returns a list of normalized job dicts (JobSpy-compatible fields + YC extras).
    """
    session = session or make_session()
    cache = SlugCache(cache_path) if cache_path else None

    companies = fetch_companies(session, source=source)
    companies = filter_companies(
        companies, max_team_size=max_team_size, batches=batches,
        years_back=years_back, hiring_only=hiring_only,
    )
    if max_companies is not None:
        companies = companies[:max_companies]

    if progress:
        print(f"Targeting {len(companies)} companies "
              f"(team_size<={max_team_size}, source={source}).")

    rows, hits = [], 0
    scraped_at = datetime.now(timezone.utc).isoformat()
    waas.reset_stats()
    try:
        for i, company in enumerate(companies, 1):
            # Backstop: no single company may kill the whole scrape.
            try:
                resolved = resolve_company(
                    session, company, cache=cache, website_detect=website_detect,
                    delay=delay, waas_descriptions=waas_descriptions,
                )
            except Exception as e:
                resolved = None
                print(f"WARNING: resolve failed for {company.get('name')} ({e}); skipped",
                      file=sys.stderr)
            if not resolved:
                if progress:
                    print(f"  [{i}/{len(companies)}] miss  {company.get('name')}")
                continue
            ats, ats_slug, raw_jobs = resolved
            hits += 1
            for raw in raw_jobs:
                rows.append(normalize_job(raw, ats, company, ats_slug, scraped_at))
            if progress:
                print(f"  [{i}/{len(companies)}] HIT   {company.get('name')} "
                      f"-> {ats} ({len(raw_jobs)} jobs)")
    finally:
        if cache is not None:
            cache.save()

    warn = waas.zero_postings_warning()
    if warn:
        print(warn, file=sys.stderr)

    if keyword:
        k = keyword.lower()
        rows = [r for r in rows if r.get("title") and k in r["title"].lower()]

    if progress:
        print(f"\ncompanies hit: {hits}/{len(companies)} | jobs: {len(rows)}")
    return rows
