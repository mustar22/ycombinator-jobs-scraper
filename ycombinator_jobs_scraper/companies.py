"""Fetch the YC company registry from yc-oss/api and filter to small startups."""
import re
from datetime import datetime, timezone

META_URL = "https://yc-oss.github.io/api/meta.json"
_FALLBACK = {
    "all": "https://yc-oss.github.io/api/companies/all.json",
    "hiring": "https://yc-oss.github.io/api/companies/hiring.json",
    "top": "https://yc-oss.github.io/api/companies/top.json",
}
_YEAR_RE = re.compile(r"(\d{4})")


def discover_endpoints(session):
    """Resolve company-list endpoints from meta.json, falling back to known URLs."""
    try:
        meta = session.get(META_URL, timeout=30).json()
        endpoints = meta.get("companies")
        if isinstance(endpoints, dict):
            return {k: v for k, v in endpoints.items() if isinstance(v, str)}
    except Exception:
        pass
    return dict(_FALLBACK)


def fetch_companies(session, source="hiring"):
    """Return the raw company list for a named endpoint ('hiring', 'all', 'top')."""
    endpoints = discover_endpoints(session)
    url = endpoints.get(source) or _FALLBACK.get(source)
    if not url:
        raise ValueError(f"unknown company source: {source!r}")
    data = session.get(url, timeout=60).json()
    return data if isinstance(data, list) else data.get("companies", [])


def batch_year(batch):
    """Extract the 4-digit year from a batch label like 'Winter 2025'."""
    if not batch:
        return None
    m = _YEAR_RE.search(str(batch))
    return int(m.group(1)) if m else None


def filter_companies(companies, max_team_size=50, batches=None, years_back=3,
                     hiring_only=True, now_year=None):
    """Keep small, recently-batched, hiring companies (the v0.1 target audience)."""
    if now_year is None:
        now_year = datetime.now(timezone.utc).year
    wanted = {b.strip().lower() for b in batches} if batches else None
    min_year = now_year - years_back

    out = []
    for c in companies:
        if hiring_only and not c.get("isHiring"):
            continue
        size = c.get("team_size")
        if max_team_size is not None and (size is None or size > max_team_size):
            continue
        if wanted is not None:
            if (c.get("batch") or "").strip().lower() not in wanted:
                continue
        else:
            yr = batch_year(c.get("batch"))
            if yr is None or yr < min_year:
                continue
        out.append(c)
    return out
