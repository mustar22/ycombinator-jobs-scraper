"""Fallback job source: WaaS postings embedded in public YC company profile pages."""
import json
import re
import time
from html import unescape
from random import uniform

YC_BASE = "https://www.ycombinator.com"
_DATA_PAGE_RE = re.compile(r'data-page="([^"]+)"')

# Run-level canary counters: listing pages fetched/parsed vs postings found.
_STATS = {"fetched": 0, "parsed": 0, "jobs": 0}


def reset_stats():
    _STATS.update(fetched=0, parsed=0, jobs=0)


def zero_postings_warning():
    """Return a loud warning if pages came back fine but yielded no postings at all."""
    if _STATS["fetched"] >= 3 and _STATS["jobs"] == 0:
        return (f"WARNING: WaaS fallback fetched {_STATS['fetched']} YC profile pages "
                f"(parsed {_STATS['parsed']}) but found 0 postings -- "
                "YC page format may have changed")
    return None


def _polite_sleep(delay):
    if delay:
        time.sleep(delay + uniform(0, delay))


def _page_props(session, url, stats=False):
    """Fetch a YC page and return the react_on_rails data-page props, or None."""
    try:
        # YC's Rails app 404s the shared session's Accept: application/json.
        r = session.get(url, timeout=20, headers={"Accept": "text/html"})
    except Exception:
        return None
    if r.status_code != 200:
        return None
    if stats:
        _STATS["fetched"] += 1
    m = _DATA_PAGE_RE.search(r.text)
    if not m:
        return None
    try:
        props = json.loads(unescape(m.group(1))).get("props")
    except ValueError:
        return None
    if props and stats:
        _STATS["parsed"] += 1
    return props or None


def fetch_waas(session, slug, descriptions=False, delay=0.0):
    """Return the WaaS job postings listed on a company's public YC profile page."""
    if not slug:
        return None
    props = _page_props(session, f"{YC_BASE}/companies/{slug}/jobs", stats=True)
    if props is None:
        return None
    jobs = props.get("jobPostings") or []
    _STATS["jobs"] += len(jobs)
    if descriptions:
        for j in jobs:
            if not j.get("url"):
                continue
            _polite_sleep(delay)
            detail = _page_props(session, YC_BASE + j["url"])
            desc = ((detail or {}).get("job") or {}).get("description")
            if desc:
                j["description"] = desc
    return jobs or None
