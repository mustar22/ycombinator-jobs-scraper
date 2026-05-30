from ycombinator_jobs_scraper.companies import batch_year, filter_companies

COMPANIES = [
    {"name": "Small+Hiring+Recent", "isHiring": True, "team_size": 8, "batch": "Winter 2025"},
    {"name": "Big", "isHiring": True, "team_size": 500, "batch": "Summer 2024"},
    {"name": "NotHiring", "isHiring": False, "team_size": 5, "batch": "Winter 2025"},
    {"name": "OldBatch", "isHiring": True, "team_size": 10, "batch": "Winter 2012"},
    {"name": "NoTeamSize", "isHiring": True, "team_size": None, "batch": "Winter 2025"},
]


def names(rows):
    return {c["name"] for c in rows}


def test_batch_year():
    assert batch_year("Winter 2025") == 2025
    assert batch_year("Spring 2026") == 2026
    assert batch_year(None) is None
    assert batch_year("Unspecified") is None


def test_default_filter_keeps_only_small_recent_hiring():
    out = filter_companies(COMPANIES, max_team_size=50, years_back=3, now_year=2026)
    assert names(out) == {"Small+Hiring+Recent"}


def test_hiring_only_off_includes_nonhiring():
    out = filter_companies(COMPANIES, max_team_size=50, years_back=3,
                           hiring_only=False, now_year=2026)
    assert "NotHiring" in names(out)


def test_explicit_batches_override_years():
    out = filter_companies(COMPANIES, max_team_size=50,
                           batches=["Winter 2012"], now_year=2026)
    assert names(out) == {"OldBatch"}


def test_max_team_size_raise_includes_big():
    out = filter_companies(COMPANIES, max_team_size=1000, years_back=3, now_year=2026)
    assert "Big" in names(out)
