from ycombinator_jobs_scraper.normalize import normalize_job, strip_html

COMPANY = {
    "name": "Acme", "slug": "acme", "batch": "Winter 2025",
    "team_size": 7, "website": "https://acme.com",
    "url": "https://www.ycombinator.com/companies/acme",
}


def test_strip_html_unescapes_and_collapses():
    assert strip_html("<p>Hello&amp;   <b>world</b></p>") == "Hello& world"
    assert strip_html("") is None
    assert strip_html(None) is None


def test_normalize_greenhouse():
    raw = {
        "title": "Backend Engineer",
        "location": {"name": "Remote - US"},
        "absolute_url": "https://boards.greenhouse.io/acme/jobs/1",
        "updated_at": "2025-03-01T12:00:00Z",
        "content": "<p>Build &amp; ship</p>",
    }
    job = normalize_job(raw, "greenhouse", COMPANY, "acme", "now")
    assert job["title"] == "Backend Engineer"
    assert job["company"] == "Acme"
    assert job["location"] == "Remote - US"
    assert job["is_remote"] is True
    assert job["date_posted"] == "2025-03-01"
    assert job["description"] == "Build & ship"
    assert job["ats"] == "greenhouse"
    assert job["batch"] == "Winter 2025"
    assert job["team_size"] == 7


def test_normalize_lever_epoch_date():
    raw = {
        "text": "Founding Engineer",
        "categories": {"location": "New York", "commitment": "Full-time"},
        "hostedUrl": "https://jobs.lever.co/acme/abc",
        "createdAt": 1709294400000,  # 2024-03-01 (ms epoch)
        "descriptionPlain": "Join us",
    }
    job = normalize_job(raw, "lever", COMPANY, "acme", "now")
    assert job["title"] == "Founding Engineer"
    assert job["job_type"] == "Full-time"
    assert job["date_posted"] == "2024-03-01"
    assert job["is_remote"] is None


def test_normalize_ashby_remote_flag():
    raw = {
        "title": "ML Engineer",
        "location": "San Francisco",
        "jobUrl": "https://jobs.ashbyhq.com/acme/xyz",
        "employmentType": "FullTime",
        "isRemote": True,
        "descriptionPlain": "Do ML",
    }
    job = normalize_job(raw, "ashby", COMPANY, "acme", "now")
    assert job["job_url"].endswith("/xyz")
    assert job["is_remote"] is True
    assert job["job_type"] == "FullTime"
    assert job["description"] == "Do ML"
