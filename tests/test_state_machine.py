"""The loan state machine (FR-29, NFR-09, R11): only the seven allowed transitions work, for the right actor only."""
import itertools

import pytest

from app.models import Loan, User
from app.services import loan_service
from app.services.loan_service import ALLOWED_TRANSITIONS, STATUS_ORDER, LoanError, change_status

STATUSES = ["Applied", "Under Review", "Approved", "Disbursed", "Repaying", "Closed", "Rejected", "Cancelled"]

# Six kinds of actor: the loan's owner, another borrower, the assigned officer, another officer, an admin, the system
ACTORS = {
    "owner": User(id=10, role="borrower"),
    "other_borrower": User(id=11, role="borrower"),
    "assigned_officer": User(id=20, role="officer"),
    "other_officer": User(id=21, role="officer"),
    "admin": User(id=30, role="admin"),
    "system": "system",
}

# The only (from, to, actor) cases that may succeed: 7 transitions, 8 cases (any officer may pick up)
ACCEPTED = {
    ("Applied", "Cancelled", "owner"),
    ("Applied", "Under Review", "assigned_officer"),
    ("Applied", "Under Review", "other_officer"),
    ("Under Review", "Approved", "assigned_officer"),
    ("Under Review", "Rejected", "assigned_officer"),
    ("Approved", "Disbursed", "assigned_officer"),
    ("Disbursed", "Repaying", "system"),
    ("Repaying", "Closed", "system"),
}

COMBINATIONS = list(itertools.product(STATUSES, STATUSES, ACTORS))


def test_there_are_384_combinations_and_8_are_allowed():
    assert len(COMBINATIONS) == 384
    assert len(ACCEPTED) == 8


def test_transition_table_matches_the_blueprint():
    assert ALLOWED_TRANSITIONS == {
        ("Applied", "Cancelled"): "borrower",
        ("Applied", "Under Review"): "officer",
        ("Under Review", "Approved"): "officer",
        ("Under Review", "Rejected"): "officer",
        ("Approved", "Disbursed"): "officer",
        ("Disbursed", "Repaying"): "system",
        ("Repaying", "Closed"): "system",
    }


def test_status_order_lists_all_eight_statuses():
    assert STATUS_ORDER == ["Applied", "Under Review", "Approved", "Disbursed", "Repaying", "Closed", "Rejected", "Cancelled"]


@pytest.mark.parametrize("old, new, actor_kind", COMBINATIONS, ids=[f"{a}->{b}:{c}" for a, b, c in COMBINATIONS])
def test_every_combination(old, new, actor_kind):
    loan = Loan(id=1, status=old, borrower_id=10, officer_id=20)
    actor = ACTORS[actor_kind]
    if (old, new, actor_kind) in ACCEPTED:
        change_status(loan, new, actor)
        assert loan.status == new
    else:
        with pytest.raises(LoanError):
            change_status(loan, new, actor)
        assert loan.status == old, "a refused change must leave the status alone"


@pytest.mark.parametrize("final", ["Closed", "Rejected", "Cancelled"])
def test_final_statuses_cannot_change_at_all(final):
    for new, actor_kind in itertools.product(STATUSES, ACTORS):
        loan = Loan(id=1, status=final, borrower_id=10, officer_id=20)
        with pytest.raises(LoanError):
            change_status(loan, new, ACTORS[actor_kind])


def test_error_message_names_the_loan_and_both_statuses():
    loan = Loan(id=7, status="Applied", borrower_id=10)
    with pytest.raises(LoanError, match=r"LN-0007 cannot move from Applied to Approved"):
        change_status(loan, "Approved", ACTORS["assigned_officer"])


def test_rule_11_other_officer_message():
    loan = Loan(id=6, status="Under Review", borrower_id=10, officer_id=20)
    with pytest.raises(LoanError, match="Only the officer who picked up"):
        change_status(loan, "Approved", ACTORS["other_officer"])


def test_wrong_role_message_names_the_role_that_may_do_it():
    loan = Loan(id=6, status="Under Review", borrower_id=10, officer_id=20)
    with pytest.raises(LoanError, match="Only the officer can move a loan from Under Review to Approved"):
        change_status(loan, "Approved", ACTORS["admin"])


def test_borrower_can_only_change_own_loan():
    loan = Loan(id=3, status="Applied", borrower_id=10)
    with pytest.raises(LoanError, match="your own loans"):
        change_status(loan, "Cancelled", ACTORS["other_borrower"])


def test_change_status_does_not_commit(app):
    """change_status only assigns the status; the calling service function does the single commit."""
    from app import db
    with app.app_context():
        loan = db.session.get(Loan, 7)  # Applied
        officer = User.query.filter_by(email="officer1@microloan.com").one()
        change_status(loan, "Under Review", officer)
        assert loan.status == "Under Review"
        db.session.rollback()
        assert db.session.get(Loan, 7).status == "Applied"


def test_service_functions_walk_a_loan_through_the_whole_lifecycle(app):
    """Applied -> Under Review -> Approved -> Disbursed -> Repaying -> Closed with the real service functions."""
    from app import db
    with app.app_context():
        loan = db.session.get(Loan, 7)
        officer = User.query.filter_by(email="officer1@microloan.com").one()
        borrower = loan.borrower
        loan_service.pick_up_loan(loan, officer)
        assert (loan.status, loan.officer_id) == ("Under Review", officer.id)
        loan_service.approve_loan(loan, officer, "ok")
        assert loan.status == "Approved" and loan.reviewed_on is not None
        loan_service.disburse_loan(loan, officer)
        assert loan.status == "Disbursed" and len(loan.repayments) == loan.tenure_months
        first = True
        while loan.next_due_installment() is not None:
            loan_service.pay_installment(loan, borrower, loan.next_due_installment().id)
            if first:
                assert loan.status == "Repaying"
                first = False
        assert loan.status == "Closed" and loan.closed_on is not None


def test_cancel_only_while_applied_via_service(app):
    from app import db
    with app.app_context():
        applied = db.session.get(Loan, 7)
        loan_service.cancel_loan(applied, applied.borrower)
        assert applied.status == "Cancelled"
        under_review = db.session.get(Loan, 6)
        with pytest.raises(LoanError):
            loan_service.cancel_loan(under_review, under_review.borrower)
        assert under_review.status == "Under Review"
