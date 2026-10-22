"""Repayment: pay in order (R8), Repaying and automatic Closed, overdue (R9), the pay button, totals (FR-35 to FR-38)."""
from datetime import date, timedelta

import pytest

from app import db
from app.models import Loan, Repayment, User
from app.services import loan_service
from support import apply, post, text


def installments(app, loan_id):
    """(id, number, status) of every installment of a loan, in order."""
    with app.app_context():
        rows = Repayment.query.filter_by(loan_id=loan_id).order_by(Repayment.installment_no).all()
        return [(r.id, r.installment_no, r.status) for r in rows]


def pay(client, loan_id, repayment_id, follow=True):
    return post(client, f"/borrower/loans/{loan_id}/pay", {"repayment_id": repayment_id}, follow_redirects=follow)


def loan_status(app, loan_id):
    with app.app_context():
        return db.session.get(Loan, loan_id).status


# ---------- the seeded repaying loan ----------

def test_seeded_loan_has_three_paid_one_overdue_and_two_pending(app):
    rows = installments(app, 2)
    assert [r[2] for r in rows] == ["Paid", "Paid", "Paid", "Pending", "Pending", "Pending"]
    with app.app_context():
        flags = [r.is_overdue() for r in Repayment.query.filter_by(loan_id=2).order_by(Repayment.installment_no)]
    assert flags == [False, False, False, True, False, False]


def test_loan_money_methods(app):
    with app.app_context():
        loan = db.session.get(Loan, 2)
        assert loan.total_payable() == round(loan.emi_amount * 6, 2) == 31058.70
        assert loan.amount_paid() == round(3 * loan.emi_amount, 2) == 15529.35
        assert loan.outstanding() == round(loan.total_payable() - loan.amount_paid(), 2) == 15529.35
        assert loan.next_due_installment().installment_no == 4


@pytest.mark.parametrize("status, offset_days, expected", [
    ("Pending", -1, True), ("Pending", 0, False), ("Pending", 1, False), ("Paid", -30, False), ("Pending", -400, True),
])
def test_is_overdue_is_computed_from_status_and_due_date(status, offset_days, expected):
    row = Repayment(status=status, due_date=date.today() + timedelta(days=offset_days), amount=100.0, installment_no=1)
    assert row.is_overdue() is expected


def test_overdue_is_not_stored_and_there_is_no_late_fee(app):
    with app.app_context():
        columns = {c.name for c in Repayment.__table__.columns}
        assert "overdue" not in columns and "late_fee" not in columns and "status" in columns
        overdue = Repayment.query.filter_by(loan_id=2, installment_no=4).one()
        assert overdue.amount == db.session.get(Loan, 2).emi_amount, "an overdue installment costs the same as any other"


# ---------- paying in order (R8) ----------

def test_only_the_earliest_pending_installment_can_be_paid(app, aman):
    rows = installments(app, 2)
    html = text(pay(aman, 2, rows[4][0]))  # installment 5 before installment 4
    assert "Only the earliest pending installment can be paid." in html
    assert [r[2] for r in installments(app, 2)] == ["Paid", "Paid", "Paid", "Pending", "Pending", "Pending"]


def test_paying_the_earliest_installment_marks_it_paid(app, aman):
    rows = installments(app, 2)
    assert "Installment 4 of 6 paid." in text(pay(aman, 2, rows[3][0]))
    with app.app_context():
        row = db.session.get(Repayment, rows[3][0])
        assert row.status == "Paid" and row.paid_on == date.today()
        assert db.session.get(Loan, 2).status == "Repaying"


@pytest.mark.parametrize("repayment_id", ["", "abc", "0", "99999", "-4"])
def test_a_bad_installment_id_is_refused(app, aman, repayment_id):
    assert "Only the earliest pending installment can be paid." in text(pay(aman, 2, repayment_id))
    assert [r[2] for r in installments(app, 2)].count("Paid") == 3


def test_an_installment_of_another_loan_cannot_be_used(app, aman):
    other_loan_row = installments(app, 1)[0][0]  # LN-0001 belongs to Sneha
    assert "Only the earliest pending installment can be paid." in text(pay(aman, 2, other_loan_row))
    assert [r[2] for r in installments(app, 2)].count("Paid") == 3


def test_paying_the_same_installment_twice_is_refused(app, aman):
    rows = installments(app, 2)
    pay(aman, 2, rows[3][0])
    assert "Only the earliest pending installment can be paid." in text(pay(aman, 2, rows[3][0]))
    assert [r[2] for r in installments(app, 2)].count("Paid") == 4


def test_paying_everything_closes_the_loan(app, aman):
    rows = installments(app, 2)
    for number in (3, 4, 5):  # installments 4, 5 and 6 are still pending
        html = text(pay(aman, 2, rows[number][0]))
    assert "All installments are paid. Your loan is now closed!" in html
    assert loan_status(app, 2) == "Closed"
    with app.app_context():
        loan = db.session.get(Loan, 2)
        assert loan.closed_on == date.today() and loan.next_due_installment() is None
        assert loan.outstanding() == 0


def test_nothing_can_be_paid_on_a_closed_loan(app, sneha):
    row = installments(app, 1)[0][0]
    assert "This loan has no installments to pay." in text(pay(sneha, 1, row))


def test_nothing_can_be_paid_before_disbursal(app, login):
    kavya = login("kavya@example.com")  # her LN-0005 is only Approved
    assert "This loan has no installments to pay." in text(pay(kavya, 5, 1))


def test_the_first_payment_moves_a_disbursed_loan_to_repaying(app, rahul, login):
    post(rahul, "/officer/applications/5/disburse")
    assert loan_status(app, 5) == "Disbursed"
    kavya = login("kavya@example.com")
    first = installments(app, 5)[0][0]
    pay(kavya, 5, first)
    assert loan_status(app, 5) == "Repaying"


def test_service_function_payment_in_order_and_final_close(app):
    with app.app_context():
        loan = db.session.get(Loan, 2)
        borrower = loan.borrower
        paid = loan_service.pay_installment(loan, borrower, loan.next_due_installment().id)
        assert paid.installment_no == 4 and loan.status == "Repaying"
        loan_service.pay_installment(loan, borrower, loan.next_due_installment().id)
        loan_service.pay_installment(loan, borrower, loan.next_due_installment().id)
        assert loan.status == "Closed"


# ---------- what the borrower sees ----------

def test_the_pay_button_is_only_on_the_earliest_pending_row(app, aman):
    html = text(aman.get("/borrower/loans/2"))
    rows = installments(app, 2)
    assert html.count('name="repayment_id"') == 1
    assert f'name="repayment_id" value="{rows[3][0]}"' in html
    assert "confirm('Pay installment 4" in html
    pay(aman, 2, rows[3][0])
    html = text(aman.get("/borrower/loans/2"))
    assert html.count('name="repayment_id"') == 1 and f'name="repayment_id" value="{rows[4][0]}"' in html


def test_a_closed_loan_has_no_pay_button(app, aman):
    for row in installments(app, 2)[3:]:
        pay(aman, 2, row[0])
    page = text(aman.get("/borrower/loans/2"))
    assert 'name="repayment_id"' not in page
    assert "You can apply for a new loan any time." in page


def test_the_overdue_badge_and_alert_disappear_after_paying(app, aman):
    assert "Overdue" in text(aman.get("/borrower/loans/2")) and "overdue installment" in text(aman.get("/borrower/dashboard"))
    pay(aman, 2, installments(app, 2)[3][0])
    assert "Overdue" not in text(aman.get("/borrower/loans/2"))
    assert "overdue installment" not in text(aman.get("/borrower/dashboard"))


def test_dashboard_shows_the_next_installment_and_recent_payments(app, aman):
    with app.app_context():
        summary = loan_service.borrower_summary(db.session.get(User, 4))
        assert summary["next_due"].installment_no == 4 and summary["overdue_count"] == 1
        assert [r.installment_no for r in summary["recent_payments"]] == [3, 2, 1]
    pay(aman, 2, installments(app, 2)[3][0])
    with app.app_context():
        summary = loan_service.borrower_summary(db.session.get(User, 4))
        assert summary["next_due"].installment_no == 5 and summary["overdue_count"] == 0
        assert summary["recent_payments"][0].installment_no == 4


def test_after_closing_the_borrower_can_apply_again(app, aman):
    for row in installments(app, 2)[3:]:
        pay(aman, 2, row[0])
    assert apply(aman).status_code == 302


def test_payment_is_simulated_no_real_money_text(aman):
    assert "Payments are simulated" in text(aman.get("/borrower/loans/2"))
