"""Resolve each company's public ATS and pull its jobs (Greenhouse/Lever/Ashby)."""
import re
import time
from random import uniform
from urllib.parse import urljoin

import requests

UA = "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0"

# Each fetcher returns (list_of_raw_jobs, resolved_slug) or None.
GREENHOUSE = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
LEVER = "https://api.lever.co/v0/postings/{slug}?mode=json"
ASHBY = "https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true"

# ATS board-link patterns, tried in order; the capture group is the real slug.
_ATS_PATTERNS = [
    ("greenhouse", re.compile(r"greenhouse\.io/embed/job_board\?for=([A-Za-z0-9][\w-]*)", re.I)),
    ("greenhouse", re.compile(r"(?:boards|job-boards)\.greenhouse\.io/([A-Za-z0-9][\w-]*)", re.I)),
    ("lever", re.compile(r"jobs\.lever\.co/([A-Za-z0-9][\w-]*)", re.I)),
    ("ashby", re.compile(r"jobs\.ashbyhq\.com/([A-Za-z0-9][\w-]*)", re.I)),
    ("ashby", re.compile(r"(?<![\w.])ashbyhq\.com/([A-Za-z0-9][\w-]*)", re.I)),
]

# Path segments that look like slugs in the patterns above but aren't company slugs.
_RESERVED_SLUGS = {"embed", "posting-api", "job-board", "job_board", "api", "www",
                   "jobs", "careers", "for", "share", "u", "assets", "static"}

_HREF_RE = re.compile(r'href=["\']([^"\']+)["\']', re.I)
_CAREERS_HINT_RE = re.compile(r"career|jobs|join|hiring|positions|openings|work-with|workwith", re.I)


def slug_variants(company):
    """Best-effort ATS slug guesses derived from YC slug, name, and website."""
    out, seen = [], set()
    cands = []
    s = (company.get("slug") or "").strip()
    if s:
        cands += [s, s.replace("-", ""), s.replace("-", "_")]
    name = (company.get("name") or "").strip()
    if name:
        n = re.sub(r"[^a-z0-9]", "", name.lower())
        if n:
            cands.append(n)
    m = re.search(r"https?://(?:www\.)?([^./]+)", company.get("website") or "")
    if m:
        cands.append(m.group(1).lower())
    for v in cands:
        if v and v not in seen:
            seen.add(v)
            out.append(v)
    return out


def _get_json(session, url):
    r = session.get(url, timeout=20)
    if r.status_code != 200:
        return None
    return r.json()


def fetch_greenhouse(session, slug):
    data = _get_json(session, GREENHOUSE.format(slug=slug))
    jobs = (data or {}).get("jobs") if isinstance(data, dict) else None
    return jobs or None


def fetch_lever(session, slug):
    data = _get_json(session, LEVER.format(slug=slug))
    return data if isinstance(data, list) and data else None


def fetch_ashby(session, slug):
    data = _get_json(session, ASHBY.format(slug=slug))
    jobs = (data or {}).get("jobs") if isinstance(data, dict) else None
    return jobs or None


_FETCHERS = (("greenhouse", fetch_greenhouse), ("lever", fetch_lever), ("ashby", fetch_ashby))


def _polite_sleep(delay):
    if delay:
        time.sleep(delay + uniform(0, delay))


def _scan_html_for_ats(html):
    """Return the first (ats, slug) whose board link appears in the HTML, else None."""
    for ats, rx in _ATS_PATTERNS:
        for m in rx.finditer(html):
            slug = m.group(1)
            if slug.lower() in _RESERVED_SLUGS:
                continue
            return ats, slug
    return None


def _fetch_html(session, url):
    """Fetch a page and return its HTML text, or None on any failure / non-HTML."""
    try:
        r = session.get(url, timeout=15)
    except Exception:
        return None
    if r.status_code != 200:
        return None
    ctype = r.headers.get("Content-Type", "")
    if ctype and "html" not in ctype.lower() and "text" not in ctype.lower():
        return None
    return r.text


def _careers_links(html, base_url, limit=3):
    """Pull up to `limit` likely careers/jobs page URLs out of a page's hrefs."""
    out, seen = [], set()
    for m in _HREF_RE.finditer(html):
        href = m.group(1)
        if not _CAREERS_HINT_RE.search(href):
            continue
        url = urljoin(base_url, href)
        if url.startswith("http") and url not in seen:
            seen.add(url)
            out.append(url)
            if len(out) >= limit:
                break
    return out


def detect_ats_from_website(website_url, session=None, follow_careers=True, delay=0.0):
    """Scrape a company's website (and a linked careers page) for an ATS board link.

    Returns (ats_provider, ats_slug) or None; never raises on network/parse failure.
    """
    if not website_url:
        return None
    if session is None:
        session = requests.Session()
        session.headers.update({"User-Agent": UA})

    html = _fetch_html(session, website_url)
    if not html:
        return None
    hit = _scan_html_for_ats(html)
    if hit:
        return hit
    if follow_careers:
        for link in _careers_links(html, website_url):
            _polite_sleep(delay)
            sub = _fetch_html(session, link)
            if sub:
                hit = _scan_html_for_ats(sub)
                if hit:
                    return hit
    return None


def resolve_company(session, company, cache=None, website_detect=True, delay=0.25):
    """Resolve a company to (ats, ats_slug, raw_jobs); cache the slug->ats mapping."""
    slug = company.get("slug")
    if cache is not None and slug:
        cached = cache.get(slug)
        if cached is not None:
            if not cached.get("ats"):
                return None
            fetch = dict(_FETCHERS)[cached["ats"]]
            jobs = fetch(session, cached["ats_slug"])
            _polite_sleep(delay)
            if jobs:
                return cached["ats"], cached["ats_slug"], jobs

    for variant in slug_variants(company):
        for ats, fetch in _FETCHERS:
            try:
                jobs = fetch(session, variant)
            except Exception:
                jobs = None
            _polite_sleep(delay)
            if jobs:
                if cache is not None and slug:
                    cache.set(slug, ats, variant)
                return ats, variant, jobs

    # Fallback: only when slug-guessing missed, scrape the website for the real slug.
    if website_detect:
        found = detect_ats_from_website(company.get("website"), session=session, delay=delay)
        _polite_sleep(delay)
        if found:
            ats, real_slug = found
            fetch = dict(_FETCHERS)[ats]
            try:
                jobs = fetch(session, real_slug)
            except Exception:
                jobs = None
            _polite_sleep(delay)
            if jobs:
                if cache is not None and slug:
                    cache.set(slug, ats, real_slug)
                return ats, real_slug, jobs

    if cache is not None and slug:
        cache.set(slug, None, None)
    return None
