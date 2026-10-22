"""The demo data of seed.py: accounts, loans in every status, one overdue installment, the default settings (FR-45, FR-57)."""
import pytest

import seed
from app import db
from app.models import ACTIVE_STATUSES, Document, Loan, LoanSetting, Repayment, User
from app.services.emi import calculate_emi
from support import PASSWORDS, post

DEMO = [
    ("Admin User", "admin@microloan.com", "Admin@123", "admin"),
    ("Priya Sharma", "officer1@microloan.com", "Officer@123", "officer"),
    ("Rahul Verma", "officer2@microloan.com", "Officer@123", "officer"),
    ("Aman Gupta", "aman@example.com", "Borrower@123", "borrower"),
    ("Sneha Iyer", "sneha@example.com", "Borrower@123", "borrower"),
    ("Rohan Das", "rohan@example.com", "Borrower@123", "borrower"),
    ("Kavya Reddy", "kavya@example.com", "Borrower@123", "borrower"),
]


def test_the_seven_demo_accounts_match_the_blueprint(app):
    with app.app_context():
        found = [(u.name, u.email, u.role) for u in User.query.order_by(User.id).all()]
    assert found == [(n, e, r) for n, e, _p, r in DEMO]
    assert {e: p for _n, e, p, _r in DEMO} == PASSWORDS


@pytest.mark.parametrize("name, email, password, role", DEMO, ids=[d[1] for d in DEMO])
def test_every_demo_account_can_log_in(anon, name, email, password, role):
    response = post(anon, "/login", {"email": email, "password": password})
    assert response.status_code == 302 and response.headers["Location"].endswith(f"/{role}/dashboard")


def test_only_one_admin_and_borrowers_have_an_income(app):
    with app.app_context():
        assert User.query.filter_by(role="admin").count() == 1
        for user in User.query.all():
            assert (user.monthly_income is not None) == (user.role == "borrower")
            assert user.is_active is True


def test_loans_cover_the_seven_statuses_of_the_demo(app):
    with app.app_context():
        statuses = sorted(loan.status for loan in Loan.query.all())
    assert statuses == sorted(["Applied", "Under Review", "Approved", "Repaying", "Closed", "Rejected", "Cancelled"])


def test_loan_numbers_follow_the_age_of_the_loans(app):
    """The tests (and the demo script) rely on this order: LN-0001 is the oldest, LN-0007 the newest."""
    with app.app_context():
        by_id = {loan.id: (loan.status, loan.borrower.email, loan.officer.email if loan.officer else None) for loan in Loan.query.all()}
    assert by_id == {
        1: ("Closed", "sneha@example.com", "officer1@microloan.com"),
        2: ("Repaying", "aman@example.com", "officer2@microloan.com"),
        3: ("Rejected", "rohan@example.com", "officer1@microloan.com"),
        4: ("Cancelled", "kavya@example.com", None),
        5: ("Approved", "kavya@example.com", "officer2@microloan.com"),
        6: ("Under Review", "sneha@example.com", "officer1@microloan.com"),
        7: ("Applied", "rohan@example.com", None),
    }


def test_no_borrower_has_two_active_loans(app):
    with app.app_context():
        for user in User.query.filter_by(role="borrower"):
            assert sum(1 for loan in user.loans if loan.status in ACTIVE_STATUSES) <= 1, user.email


def test_the_repaying_loan_has_one_overdue_installment(app):
    with app.app_context():
        rows = Repayment.query.filter_by(loan_id=2).order_by(Repayment.installment_no).all()
        assert [r.status for r in rows] == ["Paid"] * 3 + ["Pending"] * 3
        assert [r.installment_no for r in rows if r.is_overdue()] == [4]
        assert sum(1 for r in Repayment.query.all() if r.is_overdue()) == 1, "exactly one overdue installment in the whole demo"


def test_the_closed_loan_is_fully_paid_and_closed_on_time(app):
    with app.app_context():
        loan = db.session.get(Loan, 1)
        assert loan.closed_on is not None and loan.next_due_installment() is None
        assert len(loan.repayments) == 4 and all(r.status == "Paid" and not r.is_overdue() for r in loan.repayments)


def test_schedules_exist_only_for_disbursed_loans(app):
    with app.app_context():
        for loan in Loan.query.all():
            assert bool(loan.repayments) == (loan.disbursed_on is not None) == (loan.status in ("Closed", "Repaying")), loan.display_id()


def test_every_demo_loan_has_the_locked_rate_and_the_matching_emi(app):
    with app.app_context():
        for loan in Loan.query.all():
            assert loan.interest_rate == 12.0
            assert loan.emi_amount == calculate_emi(loan.amount, 12.0, loan.tenure_months)


def test_review_dates_and_remarks_follow_the_status(app):
    with app.app_context():
        for loan in Loan.query.all():
            reviewed = loan.status in ("Approved", "Rejected", "Repaying", "Closed")
            assert (loan.reviewed_on is not None) == reviewed, loan.display_id()
        assert db.session.get(Loan, 3).remarks, "a rejected loan carries the reason"


def test_the_default_settings_row(app):
    with app.app_context():
        assert LoanSetting.query.count() == 1
        s = db.session.get(LoanSetting, 1)
        assert (s.interest_rate, s.min_amount, s.max_amount, s.min_tenure, s.max_tenure, s.max_emi_to_income) == (12.0, 5000, 100000, 3, 24, 50)


def test_the_demo_has_no_documents_yet(app):
    with app.app_context():
        assert Document.query.count() == 0


def test_seeding_twice_gives_the_same_database(app):
    """Running the seed again resets the tables (only ever on this temporary database)."""
    with app.app_context():
        seed.reset_database()
        users = seed.seed_users()
        seed.seed_loans(users)
        db.session.commit()
        assert User.query.count() == 7 and Loan.query.count() == 7 and LoanSetting.query.count() == 1
        assert Repayment.query.count() == 10  # 4 for the closed loan, 6 for the repaying one


def test_the_seed_asks_before_it_deletes_anything():
    assert seed.confirm_reset.__doc__ and "DELETES" in open(seed.__file__, encoding="utf-8").read()
