"""Register, login, logout, deactivation, duplicate emails, password storage, cookie flags (FR-01 to FR-07, FR-45, NFR-01, NFR-06)."""
import pytest

from app import db
from app.models import User
from app.services import loan_service
from support import TOKEN, post, register_data, text

PASSWORD_MESSAGE = "Password must be at least 8 characters and contain a letter and a number."


def user_count(app, **filters):
    with app.app_context():
        return User.query.filter_by(**filters).count()


# ---------- registration (FR-01, FR-02) ----------

def test_register_creates_a_borrower_and_logs_in(app, anon):
    response = post(anon, "/register", register_data(email="NewPerson@Example.COM"))
    assert response.status_code == 302 and response.headers["Location"].endswith("/borrower/dashboard")
    with app.app_context():
        user = User.query.filter_by(email="newperson@example.com").one()  # saved in lower case
        assert (user.role, user.is_active, user.monthly_income) == ("borrower", True, 80000.0)
    page = anon.get("/borrower/dashboard")  # a flash message is shown once, so read the page once
    assert page.status_code == 200, "the new borrower is logged in"
    assert "Welcome, Test Borrower! Your account has been created." in text(page)


def test_the_role_cannot_be_chosen(app, anon):
    post(anon, "/register", register_data(role="admin"))
    post(anon, "/register", register_data(email="second@example.com", role="officer"))
    with app.app_context():
        assert {u.role for u in User.query.filter(User.email.in_(["test@example.com", "second@example.com"])).all()} == {"borrower"}


@pytest.mark.parametrize("field, value, message", [
    ("name", "", "Name is required."),
    ("name", "x" * 101, "Name must be at most 100 characters."),
    ("email", "not-an-email", "Enter a valid email address."),
    ("email", "a@b", "Enter a valid email address."),
    ("email", ("x" * 115) + "@example.com", "Enter a valid email address."),
    ("phone", "12345", "Phone must be exactly 10 digits."),
    ("phone", "98765432101", "Phone must be exactly 10 digits."),
    ("phone", "98765abcde", "Phone must be exactly 10 digits."),
    ("monthly_income", "-5", "Monthly income must be a number greater than 0."),
    ("monthly_income", "0", "Monthly income must be a number greater than 0."),
    ("monthly_income", "abc", "Monthly income must be a number greater than 0."),
    ("monthly_income", "", "Monthly income must be a number greater than 0."),
    ("password", "short1", PASSWORD_MESSAGE),
    ("password", "onlyletters", PASSWORD_MESSAGE),
    ("password", "12345678", PASSWORD_MESSAGE),
])
def test_registration_field_errors(app, anon, field, value, message):
    overrides = {field: value}
    if field == "password":
        overrides["confirm_password"] = value
    response = post(anon, "/register", register_data(**overrides))
    assert response.status_code == 200 and message in text(response)
    assert user_count(app, email="test@example.com") == 0


@pytest.mark.parametrize("income, ok", [
    ("80000", True), ("80000.5", True), ("80000.99", True), ("80000.990", True),
    ("80000.999", False), ("1234.567", False), ("0.001", False),
])
def test_monthly_income_has_at_most_two_decimal_places(app, anon, income, ok):
    response = post(anon, "/register", register_data(monthly_income=income))
    assert (response.status_code == 302) is ok
    if not ok:
        html = text(response)
        assert "Use at most 2 decimal places." in html and f'value="{income}"' in html, "same message as the amounts; typed value kept"
    assert user_count(app, email="test@example.com") == (1 if ok else 0)


def test_passwords_must_match(anon):
    assert "Passwords do not match." in text(post(anon, "/register", register_data(confirm_password="Different1")))


def test_typed_values_are_kept_but_passwords_are_not(anon):
    html = text(post(anon, "/register", register_data(name="Keep Me", phone="123", password="Secret123x", confirm_password="Secret123x")))
    assert 'value="Keep Me"' in html and 'value="123"' in html
    assert "Secret123x" not in html, "a password must never be shown again"


def test_all_registration_errors_appear_together(anon):
    html = text(post(anon, "/register", register_data(name="", email="bad", phone="1", monthly_income="0", password="x", confirm_password="y")))
    for message in ("Name is required.", "Enter a valid email address.", "Phone must be exactly 10 digits.",
                    "Monthly income must be a number greater than 0.", PASSWORD_MESSAGE, "Passwords do not match."):
        assert message in html


# ---------- unique email (FR-03) ----------

@pytest.mark.parametrize("email", ["aman@example.com", "AMAN@example.com", "  Aman@Example.com  "])
def test_duplicate_email_is_refused_in_any_case(app, anon, email):
    response = post(anon, "/register", register_data(email=email))
    assert response.status_code == 200 and "This email is already registered." in text(response)
    assert user_count(app) == 7


def test_create_user_returns_a_field_error_for_a_duplicate(app):
    values = {"name": "A", "email": "dup@example.com", "phone": "9000000020", "monthly_income": "50000"}
    with app.app_context():
        first, errors = loan_service.create_user(values, "Passw0rd1", "borrower")
        assert first is not None and errors == {}
        second, errors = loan_service.create_user(dict(values, phone="9000000021"), "Passw0rd1", "borrower")
        assert second is None and errors == {"email": "This email is already registered."}
        assert User.query.filter_by(email="dup@example.com").count() == 1, "the failed insert was rolled back cleanly"


def test_simultaneous_registration_gives_the_form_error_not_a_500(app, anon, monkeypatch):
    """The form pre-check is skipped here, so it is the database's unique index that catches the second sign-up."""
    import app.routes.auth as auth_routes
    values = {"name": "Race", "email": "aman@example.com", "phone": "9000000022", "monthly_income": "50000"}
    monkeypatch.setattr(auth_routes, "validate_user_form", lambda form, with_income=True: (values, {}))
    response = post(anon, "/register", register_data(email="aman@example.com"))
    assert response.status_code == 200 and "This email is already registered." in text(response)
    assert "Something went wrong" not in text(response)
    assert user_count(app, email="aman@example.com") == 1
    assert anon.get("/borrower/dashboard").status_code == 302, "nobody is logged in after the failed registration"


def test_simultaneous_officer_creation_gives_the_form_error_too(app, admin, monkeypatch):
    import app.routes.admin as admin_routes
    values = {"name": "Race", "email": "officer1@microloan.com", "phone": "9000000023", "monthly_income": ""}
    monkeypatch.setattr(admin_routes, "validate_user_form", lambda form, with_income=True: (values, {}))
    response = post(admin, "/admin/users/new-officer", {"name": "Race", "email": "officer1@microloan.com", "phone": "9000000023",
                                                          "password": "Passw0rd1", "confirm_password": "Passw0rd1"})
    assert response.status_code == 200 and "This email is already registered." in text(response)
    assert user_count(app, email="officer1@microloan.com") == 1


# ---------- login (FR-04, FR-05, FR-06) ----------

@pytest.mark.parametrize("email, dashboard", [
    ("aman@example.com", "/borrower/dashboard"), ("officer1@microloan.com", "/officer/dashboard"), ("admin@microloan.com", "/admin/dashboard"),
])
def test_each_role_lands_on_its_own_dashboard(anon, email, dashboard):
    from support import PASSWORDS
    response = post(anon, "/login", {"email": email, "password": PASSWORDS[email]})
    assert response.status_code == 302 and response.headers["Location"].endswith(dashboard)
    assert anon.get(dashboard).status_code == 200


def test_login_redirect_and_welcome_message(anon):
    response = post(anon, "/login", {"email": "aman@example.com", "password": "Borrower@123"})
    assert response.status_code == 302 and response.headers["Location"].endswith("/borrower/dashboard")
    assert "Welcome back, Aman Gupta!" in text(anon.get("/borrower/dashboard"))


def test_email_is_not_case_sensitive_at_login(anon):
    response = post(anon, "/login", {"email": "  AMAN@Example.com ", "password": "Borrower@123"})
    assert response.status_code == 302


@pytest.mark.parametrize("email, password", [
    ("aman@example.com", "WrongPass1"), ("nobody@example.com", "Borrower@123"), ("aman@example.com", ""), ("", ""),
])
def test_wrong_credentials_give_one_and_the_same_message(anon, email, password):
    response = post(anon, "/login", {"email": email, "password": password})
    assert response.status_code == 200 and "Invalid email or password." in text(response)
    assert anon.get("/borrower/dashboard").status_code == 302


def test_failed_login_keeps_the_email_but_not_the_password(anon):
    html = text(post(anon, "/login", {"email": "aman@example.com", "password": "WrongPass1"}))
    assert 'value="aman@example.com"' in html and "WrongPass1" not in html


def test_deactivated_account_cannot_log_in(app, anon):
    with app.app_context():
        User.query.filter_by(email="aman@example.com").one().is_active = False
        db.session.commit()
    response = post(anon, "/login", {"email": "aman@example.com", "password": "Borrower@123"})
    assert response.status_code == 200 and "Your account has been deactivated. Please contact the admin." in text(response)


def test_a_user_deactivated_while_signed_in_is_signed_out(app, aman):
    assert aman.get("/borrower/dashboard").status_code == 200
    with app.app_context():
        User.query.filter_by(email="aman@example.com").one().is_active = False
        db.session.commit()
    response = aman.get("/borrower/dashboard")
    assert response.status_code == 302 and "/login" in response.headers["Location"]


def test_a_login_attempt_with_a_bad_token_is_refused(anon):
    response = anon.post("/login", data={"email": "aman@example.com", "password": "Borrower@123", "csrf_token": "wrong"})
    assert response.status_code == 302 and anon.get("/borrower/dashboard").status_code == 302


# ---------- logout is a POST (FR-07) ----------

def test_logout_with_the_token_ends_the_session(aman):
    response = post(aman, "/logout")
    assert response.status_code == 302 and response.headers["Location"].endswith("/")
    assert aman.get("/borrower/dashboard").status_code == 302
    assert "You have been logged out." in text(aman.get("/"))


def test_get_logout_is_405_and_keeps_the_session(aman):
    assert aman.get("/logout").status_code == 405
    assert aman.get("/borrower/dashboard").status_code == 200


def test_logout_without_the_token_does_nothing(aman):
    aman.post("/logout", data={})
    assert aman.get("/borrower/dashboard").status_code == 200
    aman.post("/logout", data={"csrf_token": "wrong"})
    assert aman.get("/borrower/dashboard").status_code == 200


def test_anonymous_logout_goes_to_login(anon):
    response = post(anon, "/logout")
    assert response.status_code == 302 and "/login" in response.headers["Location"]


@pytest.mark.parametrize("who", ["aman", "priya", "admin"])
def test_the_navbar_logout_is_a_post_form_with_the_token(request, who):
    client = request.getfixturevalue(who)
    path = {"aman": "/borrower/dashboard", "priya": "/officer/dashboard", "admin": "/admin/dashboard"}[who]
    html = text(client.get(path))
    assert '<form method="post" action="/logout"' in html and 'name="csrf_token"' in html
    assert 'href="/logout"' not in html


# ---------- passwords and cookies (NFR-01, NFR-06) ----------

def test_passwords_are_stored_as_salted_hashes(app):
    with app.app_context():
        for user in User.query.all():
            assert user.password_hash.startswith(("scrypt:", "pbkdf2:"))
            assert user.password_hash not in ("Admin@123", "Officer@123", "Borrower@123")
        aman = User.query.filter_by(email="aman@example.com").one()
        assert aman.check_password("Borrower@123") and not aman.check_password("borrower@123")
        other = User(name="x", email="x@x.com", phone="9000000000", role="borrower")
        other.set_password("Borrower@123")
        assert other.password_hash != aman.password_hash, "the salt makes equal passwords hash differently"


def test_a_password_never_appears_in_any_page_after_login(login_with_password):
    client = login_with_password("aman@example.com")
    for url in ("/borrower/dashboard", "/borrower/loans", "/borrower/loans/2", "/borrower/apply"):
        assert "Borrower@123" not in text(client.get(url))


def test_session_cookie_has_samesite_lax_and_httponly(anon):
    response = post(anon, "/login", {"email": "aman@example.com", "password": "Borrower@123"})
    cookies = response.headers.getlist("Set-Cookie")
    assert any("SameSite=Lax" in c for c in cookies), cookies
    assert any("HttpOnly" in c for c in cookies), cookies


def test_cookie_settings_in_config(app):
    assert app.config["SESSION_COOKIE_SAMESITE"] == "Lax"
    assert app.config["SESSION_COOKIE_HTTPONLY"] is True


def test_the_secret_key_comes_from_the_environment_with_a_dev_default(app):
    assert app.config["SECRET_KEY"], "a SECRET_KEY must be set"
