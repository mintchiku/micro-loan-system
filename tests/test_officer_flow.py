"""Officer review workflow: list, search, detail, pick up, approve, reject, disburse, dashboard (FR-22 to FR-28, FR-47, R7, R11)."""
import re
from datetime import date

import pytest

from app import db
from app.models import Loan
from app.services import loan_service
from app.services.emi import add_months
from support import post, text

# Seeded loans: 1 Closed (Sneha), 2 Repaying (Aman, Rahul), 3 Rejected (Rohan), 4 Cancelled (Kavya),
# 5 Approved (Kavya, Rahul), 6 Under Review (Sneha, Priya), 7 Applied (Rohan)
BY_STATUS = {"Applied": [7], "Under Review": [6], "Approved": [5], "Disbursed": [], "Repaying": [2], "Closed": [1], "Rejected": [3], "Cancelled": [4]}


def shown_loans(response):
    """The set of loan numbers whose rows (links to the application page) the list shows."""
    return {int(n) for n in re.findall(r'href="/officer/applications/(\d+)"', text(response))}


def action(client, loan_id, name, **data):
    return post(client, f"/officer/applications/{loan_id}/{name}", data, follow_redirects=True)


# ---------- list, filter, search (FR-22) ----------

def test_the_list_shows_every_application_by_default(priya):
    assert shown_loans(priya.get("/officer/applications")) == {1, 2, 3, 4, 5, 6, 7}


@pytest.mark.parametrize("status, expected", sorted(BY_STATUS.items()))
def test_filter_by_status(priya, status, expected):
    response = priya.get("/officer/applications", query_string={"status": status})
    assert response.status_code == 200
    assert shown_loans(response) == set(expected)
    if not expected:
        assert "No applications match this filter." in text(response)


def test_an_unknown_status_filter_is_ignored(priya):
    assert shown_loans(priya.get("/officer/applications", query_string={"status": "Nonsense"})) == {1, 2, 3, 4, 5, 6, 7}


@pytest.mark.parametrize("query, expected", [
    ("LN-0007", {7}), ("ln-0007", {7}), ("ln7", {7}), ("7", {7}), ("LN0003", {3}),
    ("Sneha", {1, 6}), ("sneha iyer", {1, 6}), ("Rohan", {3, 7}), ("zzz-nobody", set()),
])
def test_search_by_loan_number_or_borrower_name(priya, query, expected):
    assert shown_loans(priya.get("/officer/applications", query_string={"q": query})) == expected


def test_status_and_search_combine(priya):
    assert shown_loans(priya.get("/officer/applications", query_string={"status": "Under Review", "q": "Sneha"})) == {6}
    assert shown_loans(priya.get("/officer/applications", query_string={"status": "Applied", "q": "Sneha"})) == set()


def test_admin_may_open_the_list_read_only(admin):
    assert shown_loans(admin.get("/officer/applications")) == {1, 2, 3, 4, 5, 6, 7}


# ---------- detail (FR-23) ----------

def test_the_detail_page_has_everything_for_the_decision(priya):
    html = text(priya.get("/officer/applications/6"))
    for expected in ("Sneha Iyer", "sneha@example.com", "9876543211", "₹60,000.00",  # borrower
                     "₹25,000.00", "9 months", "12% a year", "₹2,918.51", "₹26,266.59", "Medical expenses",  # loan
                     "Affordability", "4.9%", "Status history"):
        assert expected in html


def test_the_detail_page_of_a_disbursed_loan_shows_the_schedule(priya):
    html = text(priya.get("/officer/applications/2"))
    assert "EMI schedule" in html and "Overdue" in html


@pytest.mark.parametrize("loan_id, officer, expect, absent", [
    (7, "priya", "Pick up for review", "Your decision"),
    (6, "priya", "Your decision", "Pick up for review"),
    (5, "rahul", "Disburse", "Your decision"),
])
def test_the_decision_card_depends_on_the_status(request, loan_id, officer, expect, absent):
    html = text(request.getfixturevalue(officer).get(f"/officer/applications/{loan_id}"))
    assert expect in html and absent not in html


def test_another_officer_sees_a_lock_notice_and_no_buttons(rahul):
    html = text(rahul.get("/officer/applications/6"))
    assert "Assigned to Priya Sharma. Only they can act on this application." in html
    assert "Your decision" not in html and "Pick up for review" not in html


# ---------- pick up (FR-24) ----------

def test_any_officer_can_pick_up_an_applied_loan(priya, state):
    html = text(action(priya, 7, "pickup"))
    assert "You picked up LN-0007 for review." in html
    assert state(7)[:2] == ("Under Review", "Priya Sharma")


def test_the_second_officer_cannot_pick_it_up_again(priya, rahul, state):
    action(priya, 7, "pickup")
    html = text(action(rahul, 7, "pickup"))
    assert "cannot move from Under Review to Under Review" in html
    assert state(7)[:2] == ("Under Review", "Priya Sharma")


@pytest.mark.parametrize("loan_id", [1, 2, 3, 4, 5, 6])
def test_only_an_applied_loan_can_be_picked_up(priya, state, loan_id):
    before = state(loan_id)
    html = text(action(priya, loan_id, "pickup"))
    assert "cannot move from" in html and state(loan_id) == before


# ---------- approve (FR-25) ----------

def test_assigned_officer_approves(priya, state, app):
    html = text(action(priya, 6, "approve", remarks="Income checked"))
    assert "LN-0006 approved. You can now disburse it." in html
    assert state(6)[0] == "Approved"
    with app.app_context():
        loan = db.session.get(Loan, 6)
        assert loan.reviewed_on is not None and loan.remarks == "Income checked"


def test_approve_remarks_are_optional(priya, state, app):
    action(priya, 6, "approve")
    assert state(6)[0] == "Approved"
    with app.app_context():
        assert db.session.get(Loan, 6).remarks is None


def test_approve_remarks_are_limited_to_300_characters(priya, state):
    assert "Remarks must be at most 300 characters." in text(action(priya, 6, "approve", remarks="x" * 301))
    assert state(6)[0] == "Under Review"


def test_another_officer_cannot_approve_it(rahul, state):
    html = text(action(rahul, 6, "approve"))
    assert "Only the officer who picked up this application can do this." in html
    assert state(6)[:2] == ("Under Review", "Priya Sharma")


def test_an_applied_loan_cannot_be_approved_without_a_pick_up(priya, state):
    assert "cannot move from Applied to Approved" in text(action(priya, 7, "approve"))
    assert state(7)[0] == "Applied"


# ---------- reject (FR-26) ----------

@pytest.mark.parametrize("remarks", ["", "   "])
def test_reject_needs_remarks(priya, state, remarks):
    assert "Please enter remarks explaining why the application is rejected." in text(action(priya, 6, "reject", remarks=remarks))
    assert state(6)[0] == "Under Review"


def test_reject_remarks_are_limited_to_300_characters(priya, state):
    assert "Remarks must be at most 300 characters." in text(action(priya, 6, "reject", remarks="x" * 301))
    assert state(6)[0] == "Under Review"


def test_reject_saves_the_reason_and_the_borrower_sees_it(priya, sneha, state, app):
    assert "LN-0006 rejected." in text(action(priya, 6, "reject", remarks="Document unreadable"))
    assert state(6)[0] == "Rejected"
    with app.app_context():
        assert db.session.get(Loan, 6).reviewed_on is not None
    page = text(sneha.get("/borrower/loans/6"))
    assert "Rejected" in page and "Document unreadable" in page


def test_another_officer_cannot_reject_it(rahul, state):
    assert "Only the officer who picked up" in text(action(rahul, 6, "reject", remarks="no"))
    assert state(6)[0] == "Under Review"


def test_a_rejected_borrower_can_apply_again(priya, sneha):
    from support import apply
    action(priya, 6, "reject", remarks="Please resubmit")
    assert sneha.get("/borrower/apply").status_code == 200
    assert apply(sneha).status_code in (200, 302)  # Sneha's other loan LN-0001 is Closed, so nothing blocks her


# ---------- disburse (FR-28, FR-34, R7) ----------

def test_assigned_officer_disburses_and_the_schedule_is_created(rahul, state, app):
    html = text(action(rahul, 5, "disburse"))
    assert "LN-0005 disbursed. 12 installments were created." in html
    assert state(5)[0] == "Disbursed"
    with app.app_context():
        loan = db.session.get(Loan, 5)
        rows = sorted(loan.repayments, key=lambda r: r.installment_no)
        assert loan.disbursed_on == date.today()
        assert [r.installment_no for r in rows] == list(range(1, 13))
        assert all(r.status == "Pending" and r.paid_on is None for r in rows)
        assert [r.due_date for r in rows] == [add_months(date.today(), i) for i in range(1, 13)]
        assert round(sum(r.amount for r in rows), 2) == round(loan.emi_amount * 12, 2)


def test_due_dates_are_month_end_safe(rahul, app, monkeypatch):
    class FakeDate(date):
        @classmethod
        def today(cls):
            return date(2026, 1, 31)
    monkeypatch.setattr(loan_service, "date", FakeDate)
    action(rahul, 5, "disburse")
    with app.app_context():
        rows = sorted(db.session.get(Loan, 5).repayments, key=lambda r: r.installment_no)
        assert rows[0].due_date == date(2026, 2, 28) and rows[1].due_date == date(2026, 3, 31) and rows[2].due_date == date(2026, 4, 30)


def test_another_officer_cannot_disburse(priya, state, app):
    assert "Only the officer who picked up" in text(action(priya, 5, "disburse"))
    assert state(5)[0] == "Approved"
    with app.app_context():
        assert db.session.get(Loan, 5).repayments == []


def test_disbursing_twice_creates_no_second_schedule(rahul, app):
    action(rahul, 5, "disburse")
    assert "cannot move from Disbursed to Disbursed" in text(action(rahul, 5, "disburse"))
    with app.app_context():
        assert len(db.session.get(Loan, 5).repayments) == 12


@pytest.mark.parametrize("loan_id", [6, 7])
def test_only_an_approved_loan_can_be_disbursed(priya, state, loan_id):
    before = state(loan_id)
    assert "cannot move from" in text(action(priya, loan_id, "disburse"))
    assert state(loan_id) == before


def test_the_schedule_is_not_created_before_disbursal(priya, app):
    with app.app_context():
        assert all(loan.repayments == [] for loan in Loan.query.filter(Loan.status.in_(["Applied", "Under Review", "Approved", "Rejected", "Cancelled"])))


# ---------- dashboard (FR-47) ----------

def test_officer_summary_counts(app):
    from app.models import User
    with app.app_context():
        priya = User.query.filter_by(email="officer1@microloan.com").one()
        rahul = User.query.filter_by(email="officer2@microloan.com").one()
        s1, s2 = loan_service.officer_summary(priya), loan_service.officer_summary(rahul)
        assert (s1["new_count"], s1["review_count"], s1["approved_count"]) == (1, 1, 0)
        assert (s2["new_count"], s2["review_count"], s2["approved_count"]) == (1, 0, 1)
        assert [loan.id for loan in s1["my_pending"]] == [6] and [loan.id for loan in s2["my_pending"]] == [5]


def test_the_dashboard_shows_the_pending_work(priya, rahul):
    assert "LN-0006" in text(priya.get("/officer/dashboard")) and "LN-0005" not in text(priya.get("/officer/dashboard"))
    assert "LN-0005" in text(rahul.get("/officer/dashboard"))


def test_the_dashboard_shows_an_empty_state_without_pending_work(priya):
    action(priya, 6, "reject", remarks="no")
    assert "Nothing pending." in text(priya.get("/officer/dashboard"))


def test_picking_up_a_loan_adds_it_to_my_pending_work(priya):
    action(priya, 7, "pickup")
    html = text(priya.get("/officer/dashboard"))
    assert "LN-0007" in html and "LN-0006" in html
