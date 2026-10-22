"""Every page answers in under two seconds on a local machine with the demo data (NFR-07)."""
import time

import pytest

LIMIT_SECONDS = 2.0

PAGES = [
    (None, "/"), (None, "/login"), (None, "/register"),
    ("aman", "/borrower/dashboard"), ("aman", "/borrower/apply"), ("aman", "/borrower/loans"), ("aman", "/borrower/loans/2"),
    ("sneha", "/borrower/loans/1"),
    ("priya", "/officer/dashboard"), ("priya", "/officer/applications"), ("priya", "/officer/applications/6"), ("priya", "/officer/applications/2"),
    ("admin", "/admin/dashboard"), ("admin", "/admin/users"), ("admin", "/admin/users/new-officer"), ("admin", "/admin/settings"),
    ("admin", "/admin/reports"), ("admin", "/officer/applications/6"),
    ("admin", "/admin/users?role=borrower&q=a"), ("priya", "/officer/applications?status=Applied&q=Rohan"),
]


def test_there_are_at_least_twenty_pages_in_the_check():
    assert len(PAGES) >= 20


@pytest.mark.parametrize("who, url", PAGES, ids=[f"{w or 'anon'}:{u}" for w, u in PAGES])
def test_page_loads_in_under_two_seconds(request, who, url):
    client = request.getfixturevalue(who or "anon")
    started = time.perf_counter()
    response = client.get(url)
    elapsed = time.perf_counter() - started
    assert response.status_code == 200
    assert elapsed < LIMIT_SECONDS, f"{url} took {elapsed:.2f} s"


def test_the_whole_demo_tour_is_fast(aman, priya, admin, anon):
    started = time.perf_counter()
    for client, url in ((anon, "/"), (aman, "/borrower/dashboard"), (aman, "/borrower/loans/2"), (priya, "/officer/applications"), (admin, "/admin/reports")):
        client.get(url)
    assert time.perf_counter() - started < LIMIT_SECONDS
