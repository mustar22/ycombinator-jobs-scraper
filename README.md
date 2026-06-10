# ycombinator-jobs-scraper

Scrape job postings from **small, early-stage Y Combinator startups**, straight from
each company's public ATS board (Greenhouse / Lever / Ashby) — with a **Work at a
Startup fallback** that covers companies without any public ATS. No login, no
Selenium. `requests` is the only dependency.

## Why this exists (the targeting angle)

Most job aggregators skew toward big, well-known companies. This tool does the
opposite: by default it keeps only YC companies that are **actively hiring**, have a
**team size ≤ 50**, and come from a **recent batch (last ~3 years)**. Stripe,
DoorDash, Instacart and friends are deliberately out of scope.

The pipeline:

```
yc-oss/api (daily company dataset)  ->  filter: isHiring + small + recent batch
        ->  resolve jobs, in order:
              1. ATS slug-guessing against Greenhouse / Lever / Ashby
              2. website ATS-detection (scrape homepage + careers page for a board link)
              3. WaaS fallback: postings embedded in the public YC profile page
        ->  normalize to JobSpy-compatible fields  ->  JSON + CSV
```

Company data comes from the public, daily-updated [yc-oss/api](https://yc-oss.github.io/api/)
dataset rather than YC's live API (which paginates unreliably and skews large).

## Install

```bash
pip install -e .          # from a clone
```

## CLI

```bash
# Default: hiring + team_size<=50 + last 3 batch-years -> yc_jobs.json / yc_jobs.csv
yc-jobs

# Tighten the targeting and filter job titles
yc-jobs --max-team-size 20 --keyword "machine learning"

# Pin specific batches (overrides the recent-years window)
yc-jobs --batches "Winter 2025,Spring 2025"

# Full descriptions for WaaS-fallback jobs too (one extra request per job)
yc-jobs --waas-descriptions

# Probe a small sample, custom output name
yc-jobs --max-companies 30 --out sample
```

Run `yc-jobs --help` for all flags. Key ones:

| Flag | Default | Meaning |
|---|---|---|
| `--max-team-size` | `50` | drop companies larger than this |
| `--batches` | _(off)_ | explicit batch labels, comma-separated; overrides `--years-back` |
| `--years-back` | `3` | keep batches within the last N years |
| `--hiring-only` / `--no-hiring-only` | on | require `isHiring == true` |
| `--keyword` | _(off)_ | case-insensitive filter on job title |
| `--max-companies` | _(no cap)_ | cap companies probed (handy for testing) |
| `--source` | `hiring` | yc-oss endpoint: `hiring`, `all`, or `top` |
| `--no-website-detect` | _(detect on)_ | skip scraping the company site for its ATS on a slug miss |
| `--waas-descriptions` | off | fetch full descriptions for WaaS-fallback jobs (1 request/job) |
| `--delay` | `0.25` | base per-request delay (jittered) |
| `--cache` | `.yc_ats_cache.json` | slug→ATS cache; empty string disables |

## Python API

```python
from ycombinator_jobs_scraper import scrape_yc_jobs

jobs = scrape_yc_jobs(max_team_size=25, years_back=2, keyword="engineer")
for j in jobs[:5]:
    print(j["company"], "—", j["title"], "—", j["job_url"])
```

Returns a `list[dict]` with JobSpy-compatible fields — `title`, `company`, `location`,
`job_url`, `job_type`, `is_remote`, `description`, `date_posted` — plus YC extras:
`batch`, `team_size`, `ats`, `ats_slug`, `company_yc_slug`, `company_website`,
`company_yc_url`, `scraped_at`. WaaS rows (`ats == "waas"`) additionally carry
`salary_range`, `equity_range`, `min_experience`, and `visa`.

## Coverage & data notes

- **ATS resolution alone hits ~36% of hiring companies** (slug guess + website
  detection); Greenhouse dominates, then Ashby, then Lever. The rest mostly have no
  discoverable ATS board at all.
- **The WaaS fallback closes the gap to ~100%.** `isHiring` in yc-oss derives from
  Work at a Startup, so every targeted company has postings embedded as JSON in its
  public YC profile page (`ycombinator.com/companies/<slug>/jobs`) — in testing, 64/64
  ATS misses resolved this way. The YC slug is the URL key, so no guessing needed.
- **WaaS specifics:** `job_url` is the public YC job page (applying requires a YC
  login, viewing doesn't). `date_posted` is parsed from rounded relative ages
  ("5 months") and conservatively assumes the **oldest** day they could mean — WaaS
  listings can stay up for months, treat dates as approximate. Descriptions need one
  extra request per job (`--waas-descriptions`, off by default). If profile pages
  fetch fine but yield zero postings across a run, a format-change warning is printed
  to stderr.
- **ATS dates:** Greenhouse/Lever expose `date_posted` directly; Ashby may not.
- **Cache** records hits and misses (including `"waas"` resolutions) so re-runs skip
  the slow probing; pre-WaaS miss entries self-upgrade on the next run.
- **Rate limits:** Lever publishes `Crawl-delay: 1`; requests use a jittered `--delay`.
  YC domains sit behind Cloudflare but don't block residential IPs; datacenter/VPS
  IPs may get throttled.

## Development

```bash
pip install -e ".[dev]"
pytest
```

Tests cover normalization, filtering, ATS detection, and the WaaS fallback with
synthetic data (no network required).

## License

Apache-2.0. See [LICENSE](LICENSE).
