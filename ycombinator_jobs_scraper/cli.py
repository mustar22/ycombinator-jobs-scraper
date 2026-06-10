"""Command-line interface: scrape YC startup jobs and write JSON + CSV."""
import argparse
import csv
import json
import sys

from .scraper import scrape_yc_jobs

# Stable column order for CSV output (JobSpy-compatible first, YC extras after).
CSV_COLUMNS = [
    "title", "company", "location", "job_url", "job_type", "is_remote",
    "date_posted", "description", "batch", "team_size", "ats", "ats_slug",
    "company_yc_slug", "company_website", "company_yc_url", "scraped_at",
]


def build_parser():
    p = argparse.ArgumentParser(
        prog="yc-jobs",
        description="Scrape jobs from small early-stage YC startups via public ATS boards.",
    )
    p.add_argument("--max-team-size", type=int, default=50,
                   help="exclude companies larger than this (default: 50)")
    p.add_argument("--batches", default=None,
                   help="comma-separated batch labels, e.g. 'Winter 2025,Spring 2025' "
                        "(overrides --years-back)")
    p.add_argument("--years-back", type=int, default=3,
                   help="keep companies whose batch year is within the last N years "
                        "(default: 3)")
    p.add_argument("--hiring-only", dest="hiring_only", action="store_true", default=True,
                   help="only companies with isHiring == true (default: on)")
    p.add_argument("--no-hiring-only", dest="hiring_only", action="store_false",
                   help="include companies regardless of isHiring")
    p.add_argument("--keyword", default=None, help="case-insensitive filter on job title")
    p.add_argument("--max-companies", type=int, default=None,
                   help="cap the number of companies probed (default: no cap)")
    p.add_argument("--source", default="hiring", choices=["hiring", "all", "top"],
                   help="yc-oss company endpoint to start from (default: hiring)")
    p.add_argument("--no-website-detect", dest="website_detect", action="store_false",
                   default=True,
                   help="disable the website-scraping fallback used on a slug miss "
                        "(faster, lower coverage)")
    p.add_argument("--waas-descriptions", action="store_true", default=False,
                   help="fetch full descriptions for WaaS-fallback jobs "
                        "(one extra request per job)")
    p.add_argument("--delay", type=float, default=0.25,
                   help="base per-request delay in seconds; jittered (default: 0.25)")
    p.add_argument("--cache", default=".yc_ats_cache.json",
                   help="slug->ATS cache file; set empty to disable")
    p.add_argument("--out", default="yc_jobs",
                   help="output basename; writes <out>.json and <out>.csv")
    p.add_argument("--quiet", action="store_true", help="suppress progress output")
    return p


def write_outputs(rows, basename):
    with open(f"{basename}.json", "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)
    if rows:
        columns = CSV_COLUMNS + sorted({k for r in rows for k in r} - set(CSV_COLUMNS))
        with open(f"{basename}.csv", "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)


def main(argv=None):
    args = build_parser().parse_args(argv)
    batches = [b for b in (args.batches.split(",") if args.batches else []) if b.strip()]

    rows = scrape_yc_jobs(
        max_team_size=args.max_team_size,
        batches=batches or None,
        years_back=args.years_back,
        hiring_only=args.hiring_only,
        keyword=args.keyword,
        max_companies=args.max_companies,
        source=args.source,
        website_detect=args.website_detect,
        waas_descriptions=args.waas_descriptions,
        delay=args.delay,
        cache_path=args.cache or None,
        progress=not args.quiet,
    )

    write_outputs(rows, args.out)
    print(f"\nwrote {args.out}.json" + (f" + {args.out}.csv" if rows else "")
          + f"  ({len(rows)} jobs)")
    if rows and not args.quiet:
        print("\nsample row:")
        print(json.dumps(rows[0], indent=2, ensure_ascii=False)[:900])
    return 0


if __name__ == "__main__":
    sys.exit(main())
