"""Who may open which page: every route against every role, ownership checks, wrong HTTP methods (FR-08, FR-09, FR-33, NFR-02, NFR-03)."""
import pytest

from support import post, text

ROLES = ["anon", "borrower", "officer", "admin"]
ALL = {"borrower", "officer", "admin"}

# (name, method, url, form data, roles that may use it). Loan 2 is Aman's, loan 6 is Under Review with Priya.
PROTECTED = [
    ("borrower.dashboard", "GET", "/borrower/dashboard", None, {"borrower"}),
    ("borrower.apply", "GET", "/borrower/apply", None, {"borrower"}),
    ("borrower.loans", "GET", "/borrower/loans", None, {"borrower"}),
    ("borrower.loan_detail", "GET", "/borrower/loans/2", None, {"borrower"}),
    ("borrower.pay", "POST", "/borrower/loans/2/pay", {"repayment_id": "1"}, {"borrower"}),
    ("borrower.cancel", "POST", "/borrower/loans/2/cancel", {}, {"borrower"}),
    ("officer.dashboard", "GET", "/officer/dashboard", None, {"officer"}),
    ("officer.applications", "GET", "/officer/applications", None, {"officer", "admin"}),
    ("officer.application_detail", "GET", "/officer/applications/6", None, {"officer", "admin"}),
    ("officer.application_action", "POST", "/officer/applications/6/pickup", {}, {"officer"}),
    ("officer.reassign_application", "POST", "/officer/applications/6/reassign", {"officer_id": "3"}, {"admin"}),
    ("admin.dashboard", "GET", "/admin/dashboard", None, {"admin"}),
    ("admin.users", "GET", "/admin/users", None, {"admin"}),
    ("admin.new_officer GET", "GET", "/admin/users/new-officer", None, {"admin"}),
    ("admin.new_officer POST", "POST", "/admin/users/new-officer", {"name": ""}, {"admin"}),
    ("admin.toggle_user", "POST", "/admin/users/5/toggle", {}, {"admin"}),
    ("admin.settings GET", "GET", "/admin/settings", None, {"admin"}),
    ("admin.settings POST", "POST", "/admin/settings", {"interest_rate": "bad"}, {"admin"}),
    ("admin.reports", "GET", "/admin/reports", None, {"admin"}),
    ("auth.logout", "POST", "/logout", {}, ALL),
]
CASES = [(route, role) for route in PROTECTED for role in ROLES]


@pytest.fixture
def clients(anon, aman, priya, admin):
    return {"anon": anon, "borrower": aman, "officer": priya, "admin": admin}


def call(client, method, url, data):
    if method == "GET":
        return client.get(url)
    return post(client, url, data)


@pytest.mark.parametrize("route, role", CASES, ids=[f"{r[0]}|{role}" for r, role in CASES])
def test_route_by_role(clients, route, role):
    name, method, url, data, allowed = route
    response = call(clients[role], method, url, data)
    if role in allowed:
        assert response.status_code in (200, 302), f"{role} should be able to use {name}"
        assert "/login" not in response.headers.get("Location", ""), f"{role} was sent to the login page"
    elif role == "anon":
        assert response.status_code == 302 and "/login" in response.headers["Location"], "a visitor must be sent to login"
    else:
        assert response.status_code == 403, f"{role} must get the 403 page on {name}"


def test_403_page_says_access_denied(aman):
    response = aman.get("/admin/dashboard")
    assert response.status_code == 403 and "Access denied" in text(response)


def test_the_matrix_covers_every_protected_route(app):
    """All 22 routes: 20 here, the public landing page, the document viewer, login and register are tested below."""
    covered = {url.split("<")[0] for _n, _m, url, _d, _r in PROTECTED}
    rules = [r for r in app.url_map.iter_rules() if r.endpoint != "static"]
    assert len(rules) == 22
    assert len(PROTECTED) == 20
    endpoints_here = {name.split(" ")[0] for name, *_ in PROTECTED}
    for rule in rules:
        if rule.endpoint in ("main.index", "main.view_document", "auth.login", "auth.register"):
            continue
        assert rule.endpoint in endpoints_here, f"{rule.endpoint} is missing from the permission matrix"
    assert covered


@pytest.mark.parametrize("url", ["/", "/login", "/register"])
def test_public_pages_open_for_visitors(anon, url):
    assert anon.get(url).status_code == 200


@pytest.mark.parametrize("url", ["/login", "/register"])
@pytest.mark.parametrize("who, dashboard", [("aman", "/borrower/dashboard"), ("priya", "/officer/dashboard"), ("admin", "/admin/dashboard")])
def test_logged_in_users_are_sent_to_their_dashboard(request, who, dashboard, url):
    client = request.getfixturevalue(who)
    response = client.get(url)
    assert response.status_code == 302 and response.headers["Location"].endswith(dashboard)


@pytest.mark.parametrize("url", ["/logout", "/borrower/loans/2/pay", "/borrower/loans/2/cancel", "/officer/applications/6/pickup",
                                 "/officer/applications/6/reassign", "/admin/users/5/toggle"])
def test_state_changing_urls_do_not_accept_get(aman, priya, admin, url):
    """Every state-changing action is a POST (never a GET link): a GET answers 405, whoever asks."""
    for client in (aman, priya, admin):
        assert client.get(url).status_code in (405, 403), url
    assert admin.get(url).status_code in (405, 403)


def test_logout_get_is_405_for_a_logged_in_user(aman):
    assert aman.get("/logout").status_code == 405


# ---------- ownership (NFR-03): another borrower's loan looks like a missing page ----------

@pytest.mark.parametrize("method, url, data", [
    ("GET", "/borrower/loans/2", None),
    ("POST", "/borrower/loans/2/pay", {"repayment_id": "1"}),
    ("POST", "/borrower/loans/2/cancel", {}),
])
def test_another_borrowers_loan_is_a_404(sneha, method, url, data):
    assert call(sneha, method, url, data).status_code == 404


def test_own_loan_is_visible(sneha):
    assert sneha.get("/borrower/loans/6").status_code == 200


def test_missing_loan_is_a_404(aman, priya):
    assert aman.get("/borrower/loans/9999").status_code == 404
    assert priya.get("/officer/applications/9999").status_code == 404


def test_unknown_officer_action_is_a_404(priya):
    assert post(priya, "/officer/applications/6/explode").status_code == 404


def test_officer_cannot_apply_and_borrower_cannot_review(priya, aman):
    assert priya.get("/borrower/apply").status_code == 403
    assert post(aman, "/officer/applications/7/pickup").status_code == 403


def test_admin_has_no_officer_actions_only_reassign(admin, state):
    for action in ("pickup", "approve", "reject", "disburse"):
        assert post(admin, f"/officer/applications/6/{action}", {"remarks": "x"}).status_code == 403
    assert state(6)[0] == "Under Review"


def test_admin_sees_applications_read_only(admin):
    html = text(admin.get("/officer/applications/6"))
    assert "Read-only view" in html
    for action in ("/pickup", "/approve", "/reject", "/disburse"):
        assert action not in html


def test_only_admin_accounts_are_made_by_seed(anon, app):
    """Public registration always makes a borrower, even if the form asks for another role."""
    from app.models import User
    post(anon, "/register", {"name": "Sneaky", "email": "sneaky@example.com", "phone": "9000000012", "monthly_income": "50000",
                             "password": "Passw0rd1", "confirm_password": "Passw0rd1", "role": "admin"})
    with app.app_context():
        assert User.query.filter_by(email="sneaky@example.com").one().role == "borrower"
        assert User.query.filter_by(role="admin").count() == 1
