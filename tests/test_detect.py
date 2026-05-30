from ycombinator_jobs_scraper.ats import detect_ats_from_website


class FakeResponse:
    def __init__(self, text="", status_code=200, content_type="text/html"):
        self.text = text
        self.status_code = status_code
        self.headers = {"Content-Type": content_type}


class FakeSession:
    """Serves canned HTML per URL; unknown URLs 404 (simulates unreachable pages)."""

    def __init__(self, pages):
        self.pages = pages
        self.requested = []

    def get(self, url, timeout=None):
        self.requested.append(url)
        if url in self.pages:
            return FakeResponse(self.pages[url])
        return FakeResponse("", status_code=404)


def test_detects_greenhouse_link_on_homepage():
    html = '<a href="https://boards.greenhouse.io/acmeco">We are hiring</a>'
    session = FakeSession({"https://acme.com": html})
    assert detect_ats_from_website("https://acme.com", session=session) == ("greenhouse", "acmeco")


def test_returns_none_when_no_ats_link():
    html = '<html><body><a href="/about">About us</a> no boards here</body></html>'
    session = FakeSession({"https://acme.com": html})
    assert detect_ats_from_website("https://acme.com", session=session) is None
    assert session.requested == ["https://acme.com"]  # no careers link to follow


def test_follows_careers_page_to_find_lever():
    home = '<a href="/careers">Careers</a>'
    careers = '<iframe src="https://jobs.lever.co/acme/"></iframe>'
    session = FakeSession({
        "https://acme.com": home,
        "https://acme.com/careers": careers,
    })
    assert detect_ats_from_website("https://acme.com", session=session) == ("lever", "acme")


def test_ignores_reserved_ashby_path():
    html = '<script src="https://jobs.ashbyhq.com/embed/foo"></script>'
    session = FakeSession({"https://acme.com": html})
    assert detect_ats_from_website("https://acme.com", session=session) is None


def test_unreachable_website_returns_none():
    session = FakeSession({})  # homepage 404s
    assert detect_ats_from_website("https://nope.example", session=session) is None


def test_empty_website_returns_none():
    assert detect_ats_from_website("", session=FakeSession({})) is None
