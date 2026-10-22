"""The demo script of CLAUDE.md section 13, end to end through the pages (FR-10, FR-24 to FR-28, FR-35 to FR-37, FR-43)."""
from datetime import date

from app import db
from app.models import Loan, Repayment, User
from app.services.emi import calculate_emi
from support import apply, new_client, post, register_data, text

SETTINGS = {"interest_rate": "14", "min_amount": "5000", "max_amount": "100000", "min_tenure": "3", "max_tenure": "24", "max_emi_to_income": "50"}


def newest_loan(app, email):
    with app.app_context():
        return Loan.query.join(User, Loan.borrower_id == User.id).filter(User.email == email).order_by(Loan.id.desc()).first().id


def test_the_whole_demo_script(app, anon, priya, admin, aman, sneha):
    # 1. Register a new borrower and apply for 50,000 over 12 months: the EMI is about 4,442.44 at 12 %
    response = post(anon, "/register", register_data(name="Demo Borrower", email="demo@example.com"))
    assert response.status_code == 302 and response.headers["Location"].endswith("/borrower/dashboard")
    response = apply(anon, amount="50000", tenure="12", purpose="Shop stock", follow_redirects=True)
    page = text(response)
    assert "submitted" in page and "₹4,442.44" in page and "Applied" in page
    loan_id = newest_loan(app, "demo@example.com")

    # 2. Applying again is blocked (an active loan exists)
    blocked = apply(anon, amount="10000", tenure="6")
    assert blocked.status_code == 200 and "You already have an active loan." in text(blocked)

    # 3. The officer picks it up, approves it and disburses it: 12 installments appear
    assert "You picked up" in text(post(priya, f"/officer/applications/{loan_id}/pickup", follow_redirects=True))
    assert "approved" in text(post(priya, f"/officer/applications/{loan_id}/approve", {"remarks": "Looks good"}, follow_redirects=True))
    assert "12 installments were created." in text(post(priya, f"/officer/applications/{loan_id}/disburse", follow_redirects=True))
    with app.app_context():
        loan = db.session.get(Loan, loan_id)
        assert loan.status == "Disbursed" and len(loan.repayments) == 12 and loan.disbursed_on == date.today()

    # 4. The borrower pays installment 1: the status becomes Repaying
    with app.app_context():
        first = Repayment.query.filter_by(loan_id=loan_id, installment_no=1).one().id
    assert "Installment 1 of 12 paid." in text(post(anon, f"/borrower/loans/{loan_id}/pay", {"repayment_id": first}, follow_redirects=True))
    with app.app_context():
        assert db.session.get(Loan, loan_id).status == "Repaying"

    # 5. The admin changes the interest rate to 14 %: new applications use it, the reports show the new loan
    assert "Loan settings saved." in text(post(admin, "/admin/settings", SETTINGS, follow_redirects=True))
    with app.app_context():
        assert db.session.get(Loan, loan_id).interest_rate == 12.0, "the loan made before the change keeps its rate"
    reports = text(admin.get("/admin/reports"))
    assert "Repaying" in reports and '"values": [1, 1, 1, 0, 2, 1, 1, 1]' in reports
    # a new borrower now gets 14 %
    other = new_client(app)
    post(other, "/register", register_data(name="Second Borrower", email="second@example.com"))
    assert apply(other, amount="50000", tenure="12").status_code == 302
    with app.app_context():
        second = db.session.get(Loan, newest_loan(app, "second@example.com"))
        assert second.interest_rate == 14.0 and second.emi_amount == calculate_emi(50000, 14, 12)
        assert second.emi_amount > 4442.44, "a higher rate means a higher EMI"

    # 6. The seeded Repaying loan shows an overdue installment and the Closed loan shows as closed
    dashboard = text(aman.get("/borrower/dashboard"))
    assert "1 overdue installment" in dashboard
    assert "Overdue" in text(aman.get("/borrower/loans/2"))
    assert "Closed" in text(sneha.get("/borrower/loans/1"))


def test_a_loan_can_be_paid_off_completely_and_the_borrower_can_apply_again(app, anon, priya):
    post(anon, "/register", register_data(email="full@example.com"))
    apply(anon, amount="20000", tenure="4")
    loan_id = newest_loan(app, "full@example.com")
    post(priya, f"/officer/applications/{loan_id}/pickup")
    post(priya, f"/officer/applications/{loan_id}/approve")
    post(priya, f"/officer/applications/{loan_id}/disburse")
    with app.app_context():
        ids = [r.id for r in Repayment.query.filter_by(loan_id=loan_id).order_by(Repayment.installment_no)]
    for rid in ids[:-1]:
        post(anon, f"/borrower/loans/{loan_id}/pay", {"repayment_id": rid})
    last = text(post(anon, f"/borrower/loans/{loan_id}/pay", {"repayment_id": ids[-1]}, follow_redirects=True))
    assert "All installments are paid. Your loan is now closed!" in last
    with app.app_context():
        loan = db.session.get(Loan, loan_id)
        assert loan.status == "Closed" and loan.closed_on == date.today() and loan.outstanding() == 0
    assert apply(anon, amount="15000", tenure="5").status_code == 302, "after closing, the borrower may apply again"


def test_a_cancelled_application_frees_the_borrower(app, anon):
    post(anon, "/register", register_data(email="cancel@example.com"))
    apply(anon, amount="10000", tenure="6")
    loan_id = newest_loan(app, "cancel@example.com")
    assert "has been cancelled." in text(post(anon, f"/borrower/loans/{loan_id}/cancel", follow_redirects=True))
    with app.app_context():
        assert db.session.get(Loan, loan_id).status == "Cancelled"
    assert apply(anon, amount="12000", tenure="6").status_code == 302


def test_a_rejected_application_shows_the_reason_and_frees_the_borrower(app, anon, priya):
    post(anon, "/register", register_data(email="reject@example.com"))
    apply(anon, amount="10000", tenure="6")
    loan_id = newest_loan(app, "reject@example.com")
    post(priya, f"/officer/applications/{loan_id}/pickup")
    post(priya, f"/officer/applications/{loan_id}/reject", {"remarks": "Please upload a clearer copy"})
    page = text(anon.get(f"/borrower/loans/{loan_id}"))
    assert "Rejected" in page and "Please upload a clearer copy" in page
    assert apply(anon, amount="10000", tenure="6").status_code == 302
