"""Security and integrity: CSRF on every POST, rollback when a commit fails, error pages, escaping (FR-55, FR-56, NFR-04, NFR-10)."""
import io
import os
import re

import pytest

from app import db
from app.models import Document, Loan, LoanSetting, Repayment, User
from app.services import loan_service
from support import PDF, TOKEN, apply_data, post, register_data, text


def snapshot(app):
    """Everything the POST routes can change, as one comparable value."""
    with app.app_context():
        return (
            sorted((u.id, u.email, u.role, u.is_active) for u in User.query.all()),
            sorted((l.id, l.status, l.officer_id, l.remarks) for l in Loan.query.all()),
            sorted((r.id, r.status) for r in Repayment.query.all()),
            Document.query.count(),
            (lambda s: (s.interest_rate, s.min_amount, s.max_amount, s.min_tenure, s.max_tenure, s.max_emi_to_income))(db.session.get(LoanSetting, 1)),
        )


# (url, who, form data): one entry for each of the 11 POST routes; 'who' is a fixture name or "anon"
POST_ROUTES = [
    ("/register", "anon", register_data(email="csrf@example.com")),
    ("/login", "anon", {"email": "aman@example.com", "password": "Borrower@123"}),
    ("/logout", "aman", {}),
    ("/borrower/apply", "newbie", None),
    ("/borrower/loans/2/pay", "aman", {"repayment_id": "4"}),
    ("/borrower/loans/7/cancel", "rohan", {}),
    ("/officer/applications/7/pickup", "priya", {}),
    ("/officer/applications/6/reassign", "admin", {"officer_id": "3"}),
    ("/admin/users/new-officer", "admin", {"name": "Csrf Officer", "email": "csrf-officer@microloan.com", "phone": "9000000055",
                                           "password": "Officer@789", "confirm_password": "Officer@789"}),
    ("/admin/users/5/toggle", "admin", {}),
    ("/admin/settings", "admin", {"interest_rate": "20", "min_amount": "5000", "max_amount": "100000", "min_tenure": "3", "max_tenure": "24", "max_emi_to_income": "50"}),
]


@pytest.fixture
def rohan(login):
    return login("rohan@example.com")


def client_for(request, who):
    return request.getfixturevalue("anon" if who == "anon" else who)


def test_the_list_covers_every_post_route(app):
    post_rules = [r for r in app.url_map.iter_rules() if "POST" in r.methods and r.endpoint != "static"]
    assert len(post_rules) == 11 == len(POST_ROUTES)


@pytest.mark.parametrize("token", [None, "", "wrong-token", TOKEN + "x"])
@pytest.mark.parametrize("url, who, data", POST_ROUTES, ids=[r[0] for r in POST_ROUTES])
def test_a_post_without_a_valid_token_changes_nothing(app, request, url, who, data, token):
    client = client_for(request, who)
    before = snapshot(app)
    if url == "/borrower/apply":
        form = apply_data()
    else:
        form = dict(data)
    if token is not None:
        form["csrf_token"] = token
    response = client.post(url, data=form, content_type="multipart/form-data" if url == "/borrower/apply" else None)
    assert response.status_code == 302, "the visitor is sent back with a message"
    assert snapshot(app) == before, f"{url} must not change anything without a valid token"
    assert "Your form expired or was invalid" in text(client.get("/")), "the visitor is told why nothing happened"


def test_the_message_after_a_rejected_post(aman):
    response = aman.post("/borrower/loans/2/pay", data={"repayment_id": "4"}, follow_redirects=True)
    assert "Your form expired or was invalid. Please try again." in text(response)


def test_a_rejected_login_stays_logged_out(anon):
    anon.post("/login", data={"email": "aman@example.com", "password": "Borrower@123"})
    assert anon.get("/borrower/dashboard").status_code == 302


def test_the_redirect_only_goes_back_to_this_site(aman):
    evil = aman.post("/logout", data={}, headers={"Referer": "http://evil.example.com/steal"})
    assert evil.status_code == 302 and "evil.example.com" not in evil.headers["Location"]
    here = aman.post("/logout", data={}, headers={"Referer": "http://localhost/borrower/loans"})
    assert here.headers["Location"].endswith("/borrower/loans")


def test_get_requests_do_not_need_a_token(anon):
    assert anon.get("/").status_code == 200


def test_each_session_has_its_own_random_token(app):
    tokens = set()
    for _ in range(3):
        client = app.test_client()
        html = text(client.get("/login"))
        tokens.add(re.search(r'name="csrf_token" value="([0-9a-f]{32})"', html).group(1))
    assert len(tokens) == 3, "the token must be random per session"


def test_every_form_carries_the_token(aman, priya, admin, anon):
    pages = [(anon, "/login"), (anon, "/register"), (aman, "/borrower/apply"), (aman, "/borrower/loans/2"), (priya, "/officer/applications/6"),
             (admin, "/admin/users"), (admin, "/admin/settings"), (admin, "/admin/users/new-officer"), (admin, "/officer/applications/6")]
    for client, url in pages:
        html = text(client.get(url))
        forms = re.findall(r"<form[^>]*method=\"post\"", html)
        assert forms, url
        assert html.count('name="csrf_token"') >= len(forms), f"a POST form on {url} has no csrf_token"


# ---------- rollback when a commit fails (NFR-10) ----------

class DiskFull(RuntimeError):
    pass


def boom():
    raise DiskFull("disk full")


def run_failing(app, monkeypatch, function):
    """Run `function()` in an app context while every commit fails; it must raise and leave nothing behind."""
    with app.app_context():
        monkeypatch.setattr(db.session, "commit", boom)
        with pytest.raises(DiskFull):
            function()
        monkeypatch.undo()


def test_a_failed_application_leaves_no_loan_document_or_file(app, monkeypatch, borrower_with_income):
    from werkzeug.datastructures import FileStorage
    client, uid = borrower_with_income(80000)
    before = snapshot(app)
    file = FileStorage(stream=io.BytesIO(PDF), filename="slip.pdf")

    def apply_now():
        borrower = db.session.get(User, uid)
        loan_service.apply_for_loan(borrower, 10000.0, 6, "Test", file)

    run_failing(app, monkeypatch, apply_now)
    assert snapshot(app) == before
    assert os.listdir(app.config["UPLOAD_FOLDER"]) == [], "the file saved just before the failure must be removed again"


@pytest.mark.parametrize("name, loan_id, call", [
    ("cancel", 7, lambda loan, users: loan_service.cancel_loan(loan, loan.borrower)),
    ("pick up", 7, lambda loan, users: loan_service.pick_up_loan(loan, users["priya"])),
    ("approve", 6, lambda loan, users: loan_service.approve_loan(loan, users["priya"], "fine")),
    ("reject", 6, lambda loan, users: loan_service.reject_loan(loan, users["priya"], "no")),
    ("disburse", 5, lambda loan, users: loan_service.disburse_loan(loan, users["rahul"])),
    ("pay", 2, lambda loan, users: loan_service.pay_installment(loan, loan.borrower, loan.next_due_installment().id)),
    ("reassign", 6, lambda loan, users: loan_service.reassign_loan(loan, users["rahul"], users["admin"])),
])
def test_a_failed_commit_changes_nothing(app, monkeypatch, name, loan_id, call):
    before = snapshot(app)

    def go():
        users = {"priya": User.query.filter_by(email="officer1@microloan.com").one(), "rahul": User.query.filter_by(email="officer2@microloan.com").one(),
                 "admin": User.query.filter_by(email="admin@microloan.com").one()}
        call(db.session.get(Loan, loan_id), users)

    run_failing(app, monkeypatch, go)
    assert snapshot(app) == before, f"{name}: nothing may be half-saved"


def test_a_failed_disbursal_creates_no_installments(app, monkeypatch):
    def go():
        loan_service.disburse_loan(db.session.get(Loan, 5), User.query.filter_by(email="officer2@microloan.com").one())
    run_failing(app, monkeypatch, go)
    with app.app_context():
        loan = db.session.get(Loan, 5)
        assert loan.status == "Approved" and loan.disbursed_on is None and loan.repayments == []


def test_a_failed_payment_leaves_the_installment_pending(app, monkeypatch):
    def go():
        loan = db.session.get(Loan, 2)
        loan_service.pay_installment(loan, loan.borrower, loan.next_due_installment().id)
    run_failing(app, monkeypatch, go)
    with app.app_context():
        assert Repayment.query.filter_by(loan_id=2, installment_no=4).one().status == "Pending"
        assert db.session.get(Loan, 2).status == "Repaying"


def test_failed_account_and_settings_changes_change_nothing(app, monkeypatch):
    before = snapshot(app)
    run_failing(app, monkeypatch, lambda: loan_service.toggle_user_active(User.query.filter_by(email="aman@example.com").one(),
                                                                          User.query.filter_by(email="admin@microloan.com").one()))
    run_failing(app, monkeypatch, lambda: loan_service.update_settings({"interest_rate": 30.0}))
    run_failing(app, monkeypatch, lambda: loan_service.create_user({"name": "N", "email": "n@x.com", "phone": "9000000000", "monthly_income": "1"}, "Passw0rd1", "borrower"))
    assert snapshot(app) == before


def test_an_unexpected_error_shows_the_500_page_and_saves_nothing(app, aman, monkeypatch):
    app.config["PROPAGATE_EXCEPTIONS"] = False  # let the error handler answer instead of the test client
    before = snapshot(app)
    with app.app_context():
        due = Repayment.query.filter_by(loan_id=2, installment_no=4).one().id  # the installment that may be paid
    monkeypatch.setattr(db.session, "commit", boom)
    response = post(aman, "/borrower/loans/2/pay", {"repayment_id": due})
    monkeypatch.undo()
    assert response.status_code == 500 and "Something went wrong" in text(response)
    assert snapshot(app) == before


# ---------- error pages (FR-55) ----------

def test_unknown_urls_show_the_404_page(anon, aman):
    for client in (anon, aman):
        response = client.get("/no/such/page")
        assert response.status_code == 404 and "Page not found" in text(response)


def test_the_403_page(aman):
    response = aman.get("/officer/dashboard")
    assert response.status_code == 403 and "You do not have permission to open this page." in text(response)


# ---------- output escaping and hostile input ----------

SCRIPT = "<script>alert(1)</script>"


def test_script_tags_in_the_purpose_are_shown_as_text(app, borrower_with_income):
    client, uid = borrower_with_income(80000)
    client.post("/borrower/apply", data=apply_data(purpose=SCRIPT) | {"csrf_token": TOKEN}, content_type="multipart/form-data")
    with app.app_context():
        loan_id = Loan.query.filter_by(borrower_id=uid).one().id
    html = text(client.get(f"/borrower/loans/{loan_id}"))
    assert SCRIPT not in html and "&lt;script&gt;alert(1)&lt;/script&gt;" in html


def test_script_tags_in_a_name_are_escaped_everywhere(anon, admin):
    post(anon, "/register", register_data(name=SCRIPT, email="xss@example.com"))
    html = text(admin.get("/admin/users", query_string={"q": "xss"}))
    assert SCRIPT not in html and "&lt;script&gt;" in html
    assert SCRIPT not in text(anon.get("/borrower/dashboard"))


@pytest.mark.parametrize("q", ["' OR 1=1 --", "'; DROP TABLE loan; --", "%", "_", "\\"])
def test_search_input_is_never_treated_as_sql(app, priya, admin, q):
    before = snapshot(app)
    assert priya.get("/officer/applications", query_string={"q": q}).status_code == 200
    assert admin.get("/admin/users", query_string={"q": q}).status_code == 200
    assert snapshot(app) == before


def test_the_secret_key_is_read_from_the_environment_file_example():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    assert "SECRET_KEY=" in open(os.path.join(root, ".env.example"), encoding="utf-8").read()
    assert ".env" in open(os.path.join(root, ".gitignore"), encoding="utf-8").read().split()
