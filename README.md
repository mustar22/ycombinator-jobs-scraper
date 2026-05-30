# ycombinator-jobs-scraper

Scrape job postings from **small, early-stage Y Combinator startups** — with full
job descriptions — straight from each company's public ATS board
(Greenhouse / Lever / Ashby). No login, no Selenium, no HTML scraping of detail
pages. `requests` is the only dependency.

## Why this exists (the targeting angle)

YC's `workatastartup.com` job board is login-walled, and most job aggregators skew
toward big, well-known companies. This tool does the opposite: it's built for a job
seeker who specifically wants **small early-stage startups**. By default it keeps only
companies that are **actively hiring**, have a **team size ≤ 50**, and come from a
**recent batch (last ~3 years)**. Stripe, DoorDash, Instacart and friends are
deliberately out of scope.

The pipeline:

```
yc-oss/api (daily company dataset)  ->  filter: isHiring + small + recent batch
        ->  resolve each company's ATS (slug guess, optional website detection)
        ->  pull jobs from Greenhouse / Lever / Ashby (full descriptions in JSON)
        ->  normalize to JobSpy-compatible fields  ->  JSON + CSV
```

Company data comes from the public, daily-updated [yc-oss/api](https://yc-oss.github.io/api/)
dataset rather than YC's live API (which paginates unreliably and skews to large
companies).

## Install

```bash
pip install -e .          # from a clone
# or just install the dependency and run the module:
pip install requests
```

## CLI

```bash
# Default: hiring + team_size<=50 + last 3 batch-years -> yc_jobs.json / yc_jobs.csv
yc-jobs

# Tighten the targeting and filter job titles
yc-jobs --max-team-size 20 --keyword "machine learning"

# Pin specific batches (overrides the recent-years window)
yc-jobs --batches "Winter 2025,Spring 2025,Summer 2025"

# Website ATS-detection runs by default on a slug miss; disable it for speed
yc-jobs --no-website-detect

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
| `--no-website-detect` | _(detect on)_ | disable scraping the company site for its ATS on a slug miss |
| `--delay` | `0.25` | base per-request delay (jittered) |
| `--cache` | `.yc_ats_cache.json` | slug→ATS cache; empty string disables |

## Python API

```python
from ycombinator_jobs_scraper import scrape_yc_jobs

jobs = scrape_yc_jobs(
    max_team_size=25,
    years_back=2,
    keyword="engineer",
    detect_ats=True,
)

for j in jobs[:5]:
    print(j["company"], "—", j["title"], "—", j["location"])
    print(j["job_url"])
```

`scrape_yc_jobs(...)` returns a `list[dict]`. Each row has JobSpy-compatible fields —
`title`, `company`, `location`, `job_url`, `job_type`, `is_remote`, `description`,
`date_posted` — plus YC extras: `batch`, `team_size`, `ats`, `ats_slug`,
`company_yc_slug`, `company_website`, `company_yc_url`, `scraped_at`.

## Coverage — honest caveats

- **Slug-guessing alone resolves ~43–75% of hiring companies.** Misses are mostly
  companies whose ATS slug differs from their YC slug, or who use an unsupported ATS
  (Workday, Rippling, etc.). The **website ATS-detection fallback** (on by default)
  scrapes the company homepage and a linked careers page for an ATS board link, then
  retries with the real slug — on a 30-company small-startup sample this lifted the
  hit-rate from 13/30 to 18/30. It costs a network fetch per miss, so disable it with
  `--no-website-detect` when speed matters; resolutions are cached either way.
- **Provider mix:** Greenhouse dominates (~80% of hits), then Ashby, then Lever.
- **Slug == ATS-slug is a guess, not a guarantee.** The cache records both hits and
  misses so re-runs skip the slow probing.
- **`date_posted`** is best-effort: Greenhouse/Lever expose it directly; Ashby may not.
- **Rate limits:** Lever publishes `Crawl-delay: 1`. Requests use a jittered delay
  (`--delay`) and the resolution cache keeps re-runs light. YC domains sit behind
  Cloudflare but don't block residential IPs; datacenter/VPS IPs may get throttled.

## Development

```bash
pip install -e ".[dev]"
pytest
```

Tests cover the normalization and filtering logic with mocked/synthetic data (no
network required).

## License

Apache-2.0. See [LICENSE](LICENSE).
