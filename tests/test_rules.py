"""Business rules R1 to R4 and R6 through the apply form (FR-10 to FR-18, FR-44)."""
import pytest

from app import db
from app.models import ACTIVE_STATUSES, Document, Loan, User
from app.services.emi import calculate_emi, max_affordable_amount
from app.utils.formatters import inr
from support import apply, post, text


def loans_of(app, user_id):
    with app.app_context():
        return Loan.query.filter_by(borrower_id=user_id).all()


def amount_message(response):
    return text(response)


# ---------- a valid application ----------

def test_valid_application_is_saved_with_emi_and_locked_rate(app, borrower_with_income):
    client, uid = borrower_with_income(80000)
    response = apply(client, amount="50000", tenure="12", purpose="Shop stock")
    assert response.status_code == 302
    (loan,) = loans_of(app, uid)
    with app.app_context():
        loan = db.session.get(Loan, loan.id)
        assert (loan.status, loan.amount, loan.tenure_months, loan.purpose) == ("Applied", 50000, 12, "Shop stock")
        assert loan.emi_amount == 4442.44 and loan.interest_rate == 12.0
        assert loan.officer_id is None and loan.applied_on is not None
        assert loan.document is not None and Document.query.filter_by(loan_id=loan.id).count() == 1


def test_success_message_and_redirect_to_the_loan_page(borrower_with_income):
    client, _ = borrower_with_income(80000)
    response = apply(client, follow_redirects=True)
    assert "submitted. An officer will review it soon." in text(response)


# ---------- R1: amount ----------

@pytest.mark.parametrize("amount, ok", [
    ("5000", True), ("100000", True), ("50000", True),
    ("4999.99", False), ("100000.01", False), ("0", False), ("-5000", False),
])
def test_r1_amount_limits(app, borrower_with_income, amount, ok):
    client, uid = borrower_with_income(500000)
    response = apply(client, amount=amount, tenure="24")
    assert (response.status_code == 302) is ok
    assert len(loans_of(app, uid)) == (1 if ok else 0)
    if not ok:
        assert "Amount must be between ₹5,000.00 and ₹1,00,000.00." in text(response)


@pytest.mark.parametrize("amount", ["", "abc", "nan", "inf"])
def test_r1_amount_must_be_a_number(borrower_with_income, amount):
    client, _ = borrower_with_income(80000)
    assert "Enter the loan amount." in text(apply(client, amount=amount))


@pytest.mark.parametrize("amount, ok", [
    ("10000", True), ("10000.5", True), ("10000.99", True), ("10000.990", True),
    ("10000.999", False), ("5000.001", False), ("20000.123", False),
])
def test_r1_at_most_two_decimal_places(app, borrower_with_income, amount, ok):
    client, uid = borrower_with_income(80000)
    response = apply(client, amount=amount)
    assert (response.status_code == 302) is ok
    if not ok:
        html = text(response)
        assert "Use at most 2 decimal places." in html
        assert f'value="{amount}"' in html, "the typed value must be kept"
        assert loans_of(app, uid) == []


# ---------- R2: tenure ----------

@pytest.mark.parametrize("tenure, ok", [("3", True), ("24", True), ("12", True), ("2", False), ("25", False), ("0", False), ("-6", False)])
def test_r2_tenure_limits(borrower_with_income, tenure, ok):
    client, _ = borrower_with_income(80000)
    response = apply(client, tenure=tenure)
    assert (response.status_code == 302) is ok
    if not ok:
        assert "Tenure must be between 3 and 24 months." in text(response)


@pytest.mark.parametrize("tenure", ["", "6.5", "abc"])
def test_r2_tenure_must_be_whole_months(borrower_with_income, tenure):
    client, _ = borrower_with_income(80000)
    assert "Enter the tenure in whole months." in text(apply(client, tenure=tenure))


# ---------- R3: one active loan ----------

@pytest.mark.parametrize("status", sorted(ACTIVE_STATUSES))
def test_r3_an_active_loan_blocks_a_new_application(app, give_loan, borrower_with_income, status):
    client, uid = borrower_with_income(80000)
    with app.app_context():
        email = db.session.get(User, uid).email
    give_loan(email, status)
    response = apply(client)
    assert response.status_code == 200 and "You already have an active loan." in text(response)
    assert len(loans_of(app, uid)) == 1  # only the one we gave


@pytest.mark.parametrize("status", ["Closed", "Rejected", "Cancelled"])
def test_r3_finished_loans_do_not_block(app, give_loan, borrower_with_income, status):
    client, uid = borrower_with_income(80000)
    with app.app_context():
        email = db.session.get(User, uid).email
    give_loan(email, status)
    assert apply(client).status_code == 302
    assert len(loans_of(app, uid)) == 2


def test_r3_the_active_statuses_are_the_five_open_ones():
    assert set(ACTIVE_STATUSES) == {"Applied", "Under Review", "Approved", "Disbursed", "Repaying"}


def test_r3_seeded_borrower_with_a_repaying_loan_is_blocked(aman, app):
    response = apply(aman)
    assert response.status_code == 200 and "active loan" in text(response)
    assert len(loans_of(app, 4)) == 1  # Aman (id 4) still has only LN-0002


def test_r3_blocks_even_when_the_rest_of_the_form_is_wrong(aman):
    html = text(apply(aman, amount="1", tenure="99", purpose=""))
    assert "active loan" in html and "Amount must be between" not in html  # rule 3 is checked first and alone


# ---------- R4: affordability ----------

def test_r4_emi_within_the_income_limit_is_accepted(borrower_with_income):
    client, _ = borrower_with_income(10000)  # limit 50 % = 5,000; EMI of 50,000 / 12 months = 4,442.44
    assert apply(client, amount="50000", tenure="12").status_code == 302


def test_r4_emi_above_the_limit_is_refused_with_the_maximum_amount(app, borrower_with_income):
    client, uid = borrower_with_income(10000)
    response = apply(client, amount="60000", tenure="12")  # EMI 5,329 is above 5,000
    html = text(response)
    assert response.status_code == 200 and loans_of(app, uid) == []
    assert "is more than 50% of your monthly income" in html
    maximum = max_affordable_amount(5000, 12, 12)
    assert f"you can borrow at most {inr(maximum)}" in html


def test_r4_the_quoted_maximum_is_really_affordable(borrower_with_income):
    client, _ = borrower_with_income(10000)
    maximum = max_affordable_amount(5000, 12, 12)
    assert apply(client, amount=str(maximum), tenure="12").status_code == 302


def test_r4_boundary_emi_equal_to_the_limit_passes_and_one_paisa_over_fails(borrower_with_income):
    emi = calculate_emi(50000, 12, 12)  # 4442.44
    ok_client, _ = borrower_with_income(emi * 2)  # limit is exactly the EMI
    assert apply(ok_client, amount="50000", tenure="12").status_code == 302
    bad_client, _ = borrower_with_income(round(emi * 2 - 0.02, 2))  # limit is a paisa below the EMI
    assert apply(bad_client, amount="50000", tenure="12").status_code == 200


def test_r4_is_only_checked_when_amount_and_tenure_are_valid(borrower_with_income):
    client, _ = borrower_with_income(500)  # could never afford a loan
    html = text(apply(client, amount="1", tenure="12"))
    assert "Amount must be between" in html
    assert "you can borrow at most" not in html


def test_r4_tiny_income_says_to_try_a_longer_tenure(borrower_with_income):
    client, _ = borrower_with_income(500)
    html = text(apply(client, amount="5000", tenure="3"))
    assert "below the minimum loan amount; try a longer tenure" in html


# ---------- all messages together, purpose, document presence ----------

def test_all_errors_are_shown_together(borrower_with_income):
    client, _ = borrower_with_income(80000)
    html = text(apply(client, amount="1", tenure="99", purpose="", document=None))
    for message in ("Amount must be between", "Tenure must be between", "Purpose is required.", "Please upload a supporting document"):
        assert message in html


@pytest.mark.parametrize("purpose, ok", [("x", True), ("y" * 200, True), ("z" * 201, False), ("   ", False)])
def test_purpose_rules(borrower_with_income, purpose, ok):
    client, _ = borrower_with_income(80000)
    response = apply(client, purpose=purpose)
    assert (response.status_code == 302) is ok


def test_typed_values_are_kept_on_error(borrower_with_income):
    client, _ = borrower_with_income(80000)
    html = text(apply(client, amount="1", tenure="8", purpose="Keep me"))
    assert 'value="1"' in html and 'value="8"' in html and "Keep me" in html


def test_document_is_required(borrower_with_income):
    client, _ = borrower_with_income(80000)
    assert "Please upload a supporting document" in text(apply(client, document=None))


# ---------- R6: the interest rate is locked when the application is made ----------

def test_r6_rate_is_locked_and_settings_changes_only_affect_new_loans(app, admin, borrower_with_income):
    settings = {"interest_rate": "14", "min_amount": "5000", "max_amount": "100000", "min_tenure": "3", "max_tenure": "24", "max_emi_to_income": "50"}
    assert post(admin, "/admin/settings", settings).status_code == 302
    client, uid = borrower_with_income(80000)
    assert apply(client, amount="50000", tenure="12").status_code == 302
    (loan,) = loans_of(app, uid)
    with app.app_context():
        new_loan = db.session.get(Loan, loan.id)
        assert new_loan.interest_rate == 14.0 and new_loan.emi_amount == calculate_emi(50000, 14, 12)
        assert db.session.get(Loan, 2).interest_rate == 12.0, "an existing loan keeps the rate it was given"
        assert db.session.get(Loan, 2).emi_amount == calculate_emi(30000, 12, 6)


def test_new_limits_apply_to_new_applications(admin, borrower_with_income):
    settings = {"interest_rate": "12", "min_amount": "7000", "max_amount": "90000", "min_tenure": "3", "max_tenure": "24", "max_emi_to_income": "50"}
    post(admin, "/admin/settings", settings)
    client, _ = borrower_with_income(80000)
    html = text(apply(client, amount="6000"))
    assert "Amount must be between ₹7,000.00 and ₹90,000.00." in html


def test_the_landing_and_apply_pages_show_the_live_limits(admin, anon, borrower_with_income):
    settings = {"interest_rate": "15", "min_amount": "7000", "max_amount": "90000", "min_tenure": "4", "max_tenure": "20", "max_emi_to_income": "40"}
    post(admin, "/admin/settings", settings)
    landing = text(anon.get("/"))
    assert "Micro-loans from ₹7,000 to ₹90,000" in landing and "4 &ndash; 20 months" in landing
    assert "15% a year" in landing and "EMI up to 40%" in landing
    client, _ = borrower_with_income(80000)
    form = text(client.get("/borrower/apply"))
    assert "15%" in form and "₹7,000.00" in form


def test_apply_page_opens_for_a_borrower_without_a_loan(borrower_with_income):
    client, _ = borrower_with_income(80000)
    assert client.get("/borrower/apply").status_code == 200
