"""Admin: users list and search, activate and deactivate, create officer, loan settings (FR-40 to FR-45)."""
import pytest

from app import db
from app.models import LoanSetting, User
from app.utils.validators import DECIMALS_MESSAGE
from support import PASSWORDS, post, text

ALL_EMAILS = ["admin@microloan.com", "officer1@microloan.com", "officer2@microloan.com", "aman@example.com",
              "sneha@example.com", "rohan@example.com", "kavya@example.com"]
GOOD_SETTINGS = {"interest_rate": "12", "min_amount": "5000", "max_amount": "100000", "min_tenure": "3", "max_tenure": "24", "max_emi_to_income": "50"}


def listed(response):
    """The seeded emails that appear on the users page."""
    html = text(response)
    return {e for e in ALL_EMAILS if e in html}


# ---------- users: list, filter, search (FR-40) ----------

def test_the_list_shows_all_users(admin):
    assert listed(admin.get("/admin/users")) == set(ALL_EMAILS)


@pytest.mark.parametrize("role, expected", [
    ("borrower", {"aman@example.com", "sneha@example.com", "rohan@example.com", "kavya@example.com"}),
    ("officer", {"officer1@microloan.com", "officer2@microloan.com"}),
    ("admin", {"admin@microloan.com"}),
])
def test_filter_by_role(admin, role, expected):
    assert listed(admin.get("/admin/users", query_string={"role": role})) == expected


def test_an_unknown_role_is_ignored(admin):
    assert listed(admin.get("/admin/users", query_string={"role": "superuser"})) == set(ALL_EMAILS)


@pytest.mark.parametrize("query, expected", [
    ("aman", {"aman@example.com"}), ("AMAN", {"aman@example.com"}), ("Priya", {"officer1@microloan.com"}),
    ("officer", {"officer1@microloan.com", "officer2@microloan.com"}), ("example.com", {"aman@example.com", "sneha@example.com", "rohan@example.com", "kavya@example.com"}),
    ("  kavya  ", {"kavya@example.com"}),
])
def test_search_by_name_or_email(admin, query, expected):
    assert listed(admin.get("/admin/users", query_string={"q": query})) == expected


def test_a_search_without_a_match_shows_the_empty_state(admin):
    html = text(admin.get("/admin/users", query_string={"q": "zzz-nobody"}))
    assert "No users match this filter." in html and listed(admin.get("/admin/users", query_string={"q": "zzz-nobody"})) == set()


def test_role_and_search_combine(admin):
    assert listed(admin.get("/admin/users", query_string={"role": "borrower", "q": "a"})) >= {"aman@example.com"}
    assert listed(admin.get("/admin/users", query_string={"role": "officer", "q": "aman"})) == set()


# ---------- activate and deactivate (FR-41) ----------

def is_active(app, email):
    with app.app_context():
        return User.query.filter_by(email=email).one().is_active


def test_deactivate_and_reactivate(app, admin, user_id):
    uid = user_id("kavya@example.com")
    assert "Kavya Reddy is now deactivated." in text(post(admin, f"/admin/users/{uid}/toggle", follow_redirects=True))
    assert is_active(app, "kavya@example.com") is False
    assert "Kavya Reddy is now active." in text(post(admin, f"/admin/users/{uid}/toggle", follow_redirects=True))
    assert is_active(app, "kavya@example.com") is True


def test_a_deactivated_user_cannot_log_in_until_reactivated(app, admin, anon, user_id):
    post(admin, f"/admin/users/{user_id('kavya@example.com')}/toggle")
    assert post(anon, "/login", {"email": "kavya@example.com", "password": PASSWORDS["kavya@example.com"]}).status_code == 200
    post(admin, f"/admin/users/{user_id('kavya@example.com')}/toggle")
    assert post(anon, "/login", {"email": "kavya@example.com", "password": PASSWORDS["kavya@example.com"]}).status_code == 302


def test_the_admin_cannot_deactivate_themselves(app, admin, user_id):
    assert "You cannot deactivate your own account." in text(post(admin, f"/admin/users/{user_id('admin@microloan.com')}/toggle", follow_redirects=True))
    assert is_active(app, "admin@microloan.com") is True


def test_toggling_an_unknown_user_is_a_404(admin):
    assert post(admin, "/admin/users/9999/toggle").status_code == 404


def test_the_users_page_asks_before_deactivating(admin):
    assert "confirm('Deactivate Aman Gupta?" in text(admin.get("/admin/users"))


# ---------- create officer (FR-42) ----------

OFFICER = {"name": "Neha Kapoor", "email": "neha@microloan.com", "phone": "9000000044", "password": "Officer@456", "confirm_password": "Officer@456"}


def test_create_officer_makes_an_officer_without_income(app, admin):
    response = post(admin, "/admin/users/new-officer", OFFICER)
    assert response.status_code == 302 and "role=officer" in response.headers["Location"]
    with app.app_context():
        user = User.query.filter_by(email="neha@microloan.com").one()
        assert (user.role, user.monthly_income, user.is_active) == ("officer", None, True)
        assert user.check_password("Officer@456")


def test_the_success_message_names_the_officer(admin):
    assert "Officer account created for Neha Kapoor." in text(post(admin, "/admin/users/new-officer", OFFICER, follow_redirects=True))


def test_the_new_officer_can_log_in_and_reach_the_officer_dashboard(admin, anon):
    post(admin, "/admin/users/new-officer", OFFICER)
    response = post(anon, "/login", {"email": "neha@microloan.com", "password": "Officer@456"})
    assert response.headers["Location"].endswith("/officer/dashboard")
    assert anon.get("/officer/dashboard").status_code == 200 and anon.get("/admin/dashboard").status_code == 403


def test_the_role_cannot_be_chosen_when_creating_an_officer(app, admin):
    post(admin, "/admin/users/new-officer", dict(OFFICER, role="admin"))
    with app.app_context():
        assert User.query.filter_by(email="neha@microloan.com").one().role == "officer"


@pytest.mark.parametrize("field, value, message", [
    ("name", "", "Name is required."),
    ("email", "bad", "Enter a valid email address."),
    ("email", "aman@example.com", "This email is already registered."),
    ("phone", "123", "Phone must be exactly 10 digits."),
    ("password", "short", "Password must be at least 8 characters and contain a letter and a number."),
])
def test_create_officer_validation(app, admin, field, value, message):
    data = dict(OFFICER, **{field: value})
    if field == "password":
        data["confirm_password"] = value
    response = post(admin, "/admin/users/new-officer", data)
    assert response.status_code == 200 and message in text(response)
    with app.app_context():
        assert User.query.filter_by(email="neha@microloan.com").count() == 0


def test_create_officer_keeps_typed_values_and_needs_no_income(admin):
    html = text(post(admin, "/admin/users/new-officer", dict(OFFICER, phone="1")))
    assert 'value="Neha Kapoor"' in html and "Monthly income" not in html


# ---------- loan settings (FR-43, FR-44) ----------

def setting(app, field):
    with app.app_context():
        return getattr(db.session.get(LoanSetting, 1), field)


def test_the_form_shows_the_saved_values_without_trailing_zeros(admin):
    html = text(admin.get("/admin/settings"))
    for field, value in GOOD_SETTINGS.items():
        assert f'name="{field}"' in html and f'value="{value}"' in html


def test_a_valid_change_is_saved(app, admin):
    new = dict(GOOD_SETTINGS, interest_rate="14", min_amount="6000.50", max_amount="90000.25", min_tenure="4", max_tenure="20", max_emi_to_income="40")
    before = setting(app, "updated_at")
    response = post(admin, "/admin/settings", new, follow_redirects=True)
    assert "Loan settings saved. They apply to new applications only." in text(response)
    assert [setting(app, f) for f in new] == [14.0, 6000.5, 90000.25, 4, 20, 40.0]
    assert setting(app, "updated_at") >= before


@pytest.mark.parametrize("overrides", [
    {"interest_rate": "0"}, {"interest_rate": "36"}, {"max_emi_to_income": "1"}, {"max_emi_to_income": "100"},
    {"min_amount": "1", "max_amount": "2"}, {"min_tenure": "1", "max_tenure": "2"}, {"min_amount": "5000.50"}, {"max_amount": "100000.25"},
])
def test_boundary_values_are_accepted(app, admin, overrides):
    assert post(admin, "/admin/settings", dict(GOOD_SETTINGS, **overrides)).status_code == 302


@pytest.mark.parametrize("overrides, field, message", [
    ({"interest_rate": "-1"}, "interest_rate", "Interest rate must be between 0 and 36 % per year."),
    ({"interest_rate": "36.5"}, "interest_rate", "Interest rate must be between 0 and 36 % per year."),
    ({"interest_rate": "abc"}, "interest_rate", "Interest rate must be between 0 and 36 % per year."),
    ({"min_amount": "0"}, "min_amount", "Minimum amount must be a number greater than 0."),
    ({"min_amount": "abc"}, "min_amount", "Minimum amount must be a number greater than 0."),
    ({"min_amount": "5000.555"}, "min_amount", DECIMALS_MESSAGE),
    ({"max_amount": "0"}, "max_amount", "Maximum amount must be a number greater than 0."),
    ({"max_amount": "100000.001"}, "max_amount", DECIMALS_MESSAGE),
    ({"max_amount": "5000"}, "max_amount", "Maximum amount must be greater than the minimum amount."),
    ({"min_tenure": "0"}, "min_tenure", "Minimum tenure must be a whole number of months (at least 1)."),
    ({"min_tenure": "2.5"}, "min_tenure", "Minimum tenure must be a whole number of months (at least 1)."),
    ({"max_tenure": "0"}, "max_tenure", "Maximum tenure must be a whole number of months (at least 1)."),
    ({"max_tenure": "3"}, "max_tenure", "Maximum tenure must be greater than the minimum tenure."),
    ({"max_emi_to_income": "0"}, "max_emi_to_income", "EMI-to-income limit must be between 1 and 100 %."),
    ({"max_emi_to_income": "101"}, "max_emi_to_income", "EMI-to-income limit must be between 1 and 100 %."),
])
def test_invalid_settings_are_refused_and_nothing_is_saved(app, admin, overrides, field, message):
    response = post(admin, "/admin/settings", dict(GOOD_SETTINGS, **overrides))
    assert response.status_code == 200 and message in text(response)
    html = text(response)
    assert f'value="{overrides[field]}"' in html, "the typed value must be kept"
    assert [setting(app, f) for f in GOOD_SETTINGS] == [12.0, 5000.0, 100000.0, 3, 24, 50.0]


def test_each_wrong_setting_gets_its_own_message(admin):
    html = text(post(admin, "/admin/settings", {"interest_rate": "99", "min_amount": "0", "max_amount": "0",
                                                  "min_tenure": "0", "max_tenure": "0", "max_emi_to_income": "0"}))
    assert html.count("is-invalid") >= 6 or html.count("invalid-feedback") >= 6


def test_the_settings_page_says_only_new_applications_are_affected(admin):
    assert "only to new applications" in text(admin.get("/admin/settings"))


def test_only_an_admin_can_change_settings(priya, aman, app):
    assert post(priya, "/admin/settings", dict(GOOD_SETTINGS, interest_rate="20")).status_code == 403
    assert post(aman, "/admin/settings", dict(GOOD_SETTINGS, interest_rate="20")).status_code == 403
    assert setting(app, "interest_rate") == 12.0
