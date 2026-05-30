"""Normalize raw ATS job objects into JobSpy-compatible records."""
import html
import re
from datetime import datetime, timezone

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
_REMOTE_RE = re.compile(r"\bremote\b", re.IGNORECASE)


def strip_html(text):
    """Unescape entities, drop tags, and collapse whitespace; None stays None."""
    if not text:
        return None
    text = html.unescape(text)
    text = _TAG_RE.sub(" ", text)
    return _WS_RE.sub(" ", text).strip() or None


def _infer_remote(location, explicit=None):
    if explicit is not None:
        return bool(explicit)
    if location and _REMOTE_RE.search(location):
        return True
    return None


def _epoch_to_date(value):
    """Lever/Ashby give epoch milliseconds; return an ISO date string."""
    if value in (None, ""):
        return None
    try:
        ts = float(value)
    except (TypeError, ValueError):
        return _iso_date(value)
    if ts > 1e12:  # milliseconds
        ts /= 1000.0
    try:
        return datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat()
    except (OverflowError, OSError, ValueError):
        return None


def _iso_date(value):
    """Greenhouse/Ashby give ISO timestamps; keep just the date part."""
    if not value:
        return None
    s = str(value)
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return s[:10] if len(s) >= 10 else None


def _from_greenhouse(j):
    return {
        "title": j.get("title"),
        "location": (j.get("location") or {}).get("name"),
        "job_url": j.get("absolute_url"),
        "job_type": None,
        "is_remote": _infer_remote((j.get("location") or {}).get("name")),
        "description": strip_html(j.get("content")),
        "date_posted": _iso_date(j.get("updated_at")),
    }


def _from_lever(j):
    cats = j.get("categories") or {}
    loc = cats.get("location")
    return {
        "title": j.get("text"),
        "location": loc,
        "job_url": j.get("hostedUrl"),
        "job_type": cats.get("commitment"),
        "is_remote": _infer_remote(loc, j.get("workplaceType") == "remote" or None),
        "description": strip_html(j.get("descriptionPlain") or j.get("description")),
        "date_posted": _epoch_to_date(j.get("createdAt")),
    }


def _from_ashby(j):
    return {
        "title": j.get("title"),
        "location": j.get("location"),
        "job_url": j.get("jobUrl") or j.get("applyUrl"),
        "job_type": j.get("employmentType"),
        "is_remote": _infer_remote(j.get("location"), j.get("isRemote")),
        "description": j.get("descriptionPlain") or strip_html(j.get("descriptionHtml")),
        "date_posted": _iso_date(j.get("publishedAt") or j.get("updatedAt")),
    }


_DISPATCH = {"greenhouse": _from_greenhouse, "lever": _from_lever, "ashby": _from_ashby}


def normalize_job(raw, ats, company, ats_slug, scraped_at):
    """Map one raw provider job + its YC company into the unified output schema."""
    base = _DISPATCH[ats](raw)
    base.update({
        "company": company.get("name"),
        "ats": ats,
        # YC extras
        "batch": company.get("batch"),
        "team_size": company.get("team_size"),
        "company_yc_slug": company.get("slug"),
        "company_website": company.get("website"),
        "company_yc_url": company.get("url"),
        "ats_slug": ats_slug,
        "scraped_at": scraped_at,
    })
    return base
