"""Admin reassignment of an application to another officer, and the warning on deactivation (FR-30, FR-31, FR-32, R11, Part 2c)."""
import re

import pytest

from app import db
from app.models import Loan, User
from app.services import loan_service
from app.services.loan_service import LoanError
from support import post, text

NOT_REASSIGNABLE = [(7, "Applied"), (1, "Closed"), (3, "Rejected"), (4, "Cancelled"), (2, "Repaying")]


def reassign(client, loan_id, officer_id, follow=True):
    return post(client, f"/officer/applications/{loan_id}/reassign", {"officer_id": officer_id}, follow_redirects=follow)


def action(client, loan_id, name, **data):
    return post(client, f"/officer/applications/{loan_id}/{name}", data, follow_redirects=True)


def enabled_yellow_buttons(html):
    """Enabled btn-primary buttons and links (the one yellow action per page rule)."""
    tags = re.findall(r"<(?:a|button)\b[^>]*>", html)
    return [t for t in tags if re.search(r'class="[^"]*\bbtn-primary\b', t) and " disabled" not in t]


# ---------- it works, and only the officer changes ----------

def test_admin_reassigns_an_under_review_loan(admin, state, user_id):
    html = text(reassign(admin, 6, user_id("officer2@microloan.com")))
    assert "LN-0006 reassigned from Priya Sharma to Rahul Verma." in html
    assert state(6)[:2] == ("Under Review", "Rahul Verma"), "the status must not change"


def test_admin_reassigns_an_approved_loan(admin, state, user_id):
    reassign(admin, 5, user_id("officer1@microloan.com"))
    assert state(5)[:2] == ("Approved", "Priya Sharma")


def test_the_old_officer_is_refused_and_the_new_officer_can_approve(admin, priya, rahul, state, user_id):
    reassign(admin, 6, user_id("officer2@microloan.com"))
    assert "Only the officer who picked up" in text(action(priya, 6, "approve", remarks="old"))
    assert state(6)[0] == "Under Review"
    assert "approved" in text(action(rahul, 6, "approve", remarks="new"))
    assert state(6)[:2] == ("Approved", "Rahul Verma")


def test_a_reassigned_approved_loan_is_disbursed_by_the_new_officer(admin, priya, rahul, state, user_id):
    reassign(admin, 5, user_id("officer1@microloan.com"))
    assert "Only the officer who picked up" in text(action(rahul, 5, "disburse"))
    assert state(5)[0] == "Approved"
    assert "disbursed" in text(action(priya, 5, "disburse"))
    assert state(5)[0] == "Disbursed"


def test_the_borrower_sees_the_new_officer(admin, aman, sneha, user_id):
    reassign(admin, 6, user_id("officer2@microloan.com"))
    assert "Rahul Verma" in text(sneha.get("/borrower/loans/6"))


# ---------- what is refused ----------

@pytest.mark.parametrize("loan_id, status", NOT_REASSIGNABLE)
def test_other_statuses_cannot_be_reassigned(admin, state, user_id, loan_id, status):
    before = state(loan_id)
    html = text(reassign(admin, loan_id, user_id("officer2@microloan.com") if before[1] != "Rahul Verma" else user_id("officer1@microloan.com")))
    assert "Only loans that are Under Review or Approved can be reassigned." in html
    assert state(loan_id) == before
    assert "Reassign application" not in text(admin.get(f"/officer/applications/{loan_id}")), "no form on a loan that cannot be reassigned"


def test_a_disbursed_loan_cannot_be_reassigned(admin, rahul, state, user_id):
    action(rahul, 5, "disburse")
    before = state(5)
    assert "Only loans that are Under Review or Approved" in text(reassign(admin, 5, user_id("officer1@microloan.com")))
    assert state(5) == before


def test_the_same_officer_is_refused(admin, state, user_id):
    assert "LN-0006 is already assigned to Priya Sharma." in text(reassign(admin, 6, user_id("officer1@microloan.com")))
    assert state(6)[1] == "Priya Sharma"


@pytest.mark.parametrize("target", ["aman@example.com", "admin@microloan.com"])
def test_only_an_officer_account_can_be_the_new_owner(admin, state, user_id, target):
    assert "Choose an active loan officer." in text(reassign(admin, 6, user_id(target)))
    assert state(6)[1] == "Priya Sharma"


def test_an_inactive_officer_cannot_be_the_new_owner(app, admin, state, user_id):
    with app.app_context():
        User.query.filter_by(email="officer2@microloan.com").one().is_active = False
        db.session.commit()
    assert "Choose an active loan officer." in text(reassign(admin, 6, user_id("officer2@microloan.com")))
    assert state(6)[1] == "Priya Sharma"


@pytest.mark.parametrize("officer_id", ["", "abc", "9999", "-1"])
def test_empty_or_unknown_choices_are_refused(admin, state, officer_id):
    assert "Choose an active loan officer." in text(reassign(admin, 6, officer_id))
    assert state(6)[1] == "Priya Sharma"


def test_an_unknown_loan_is_a_404(admin, user_id):
    assert reassign(admin, 9999, user_id("officer2@microloan.com"), follow=False).status_code == 404


# ---------- who may do it ----------

@pytest.mark.parametrize("who", ["priya", "rahul", "aman", "sneha"])
def test_only_the_admin_may_reassign(request, state, user_id, who):
    client = request.getfixturevalue(who)
    assert reassign(client, 6, user_id("officer2@microloan.com"), follow=False).status_code == 403
    assert state(6)[1] == "Priya Sharma"


def test_a_visitor_is_sent_to_login(anon, state, user_id):
    response = reassign(anon, 6, user_id("officer2@microloan.com"), follow=False)
    assert response.status_code == 302 and "/login" in response.headers["Location"]
    assert state(6)[1] == "Priya Sharma"


def test_no_csrf_token_changes_nothing(admin, state, user_id):
    admin.post("/officer/applications/6/reassign", data={"officer_id": user_id("officer2@microloan.com")})
    assert state(6)[1] == "Priya Sharma"


def test_the_service_refuses_a_non_admin_actor(app):
    with app.app_context():
        loan = db.session.get(Loan, 6)
        officer = User.query.filter_by(email="officer1@microloan.com").one()
        other = User.query.filter_by(email="officer2@microloan.com").one()
        with pytest.raises(LoanError, match="Only an admin can reassign an application."):
            loan_service.reassign_loan(loan, other, officer)
        assert loan.officer_id == officer.id


# ---------- the form on the admin's page (FR-31) ----------

def test_the_admin_sees_the_form_with_the_other_active_officers_only(admin, user_id):
    html = text(admin.get("/officer/applications/6"))
    assert "Reassign application" in html and 'name="officer_id"' in html
    assert f'<option value="{user_id("officer2@microloan.com")}">' in html
    assert f'<option value="{user_id("officer1@microloan.com")}">' not in html, "the current officer is not offered"


def test_a_deactivated_officer_is_not_offered_and_the_page_says_so(app, admin, user_id):
    with app.app_context():
        User.query.filter_by(email="officer1@microloan.com").one().is_active = False
        db.session.commit()
    html = text(admin.get("/officer/applications/6"))
    assert "(deactivated)" in html
    assert f'<option value="{user_id("officer1@microloan.com")}">' not in html


def test_the_form_says_so_when_there_is_no_other_active_officer(app, admin):
    with app.app_context():
        User.query.filter_by(email="officer2@microloan.com").one().is_active = False
        db.session.commit()
    html = text(admin.get("/officer/applications/6"))
    assert "No other active officer is available." in html and 'name="officer_id"' not in html


def test_the_form_has_a_confirm_dialog_and_a_csrf_token(admin):
    html = text(admin.get("/officer/applications/6"))
    assert "confirm('Reassign LN-0006 to '" in html and 'name="csrf_token"' in html


def test_the_reassign_button_is_blue_outline_and_the_page_has_no_yellow_button(admin):
    html = text(admin.get("/officer/applications/6"))
    assert 'class="btn btn-outline-primary w-100"' in html
    assert enabled_yellow_buttons(html) == []


@pytest.mark.parametrize("who", ["priya", "rahul"])
def test_officers_do_not_see_the_reassign_form(request, who):
    assert "Reassign application" not in text(request.getfixturevalue(who).get("/officer/applications/6"))


# ---------- helpers of the service ----------

def test_pending_loan_count_counts_only_under_review_and_approved(app):
    with app.app_context():
        priya = User.query.filter_by(email="officer1@microloan.com").one()  # LN-0001 Closed, LN-0003 Rejected, LN-0006 Under Review
        rahul = User.query.filter_by(email="officer2@microloan.com").one()  # LN-0002 Repaying, LN-0005 Approved
        assert loan_service.pending_loan_count(priya) == 1
        assert loan_service.pending_loan_count(rahul) == 1


def test_active_officers_are_listed_a_to_z_and_can_exclude_one(app, user_id):
    with app.app_context():
        assert [o.name for o in loan_service.active_officers()] == ["Priya Sharma", "Rahul Verma"]
        assert [o.name for o in loan_service.active_officers(exclude_id=user_id("officer1@microloan.com"))] == ["Rahul Verma"]


# ---------- deactivating an officer warns about stuck loans (FR-32) ----------

def toggle(admin, user_id):
    return post(admin, f"/admin/users/{user_id}/toggle", follow_redirects=True)


def test_deactivating_an_officer_with_one_pending_loan_warns_with_the_count(admin, user_id):
    html = text(toggle(admin, user_id("officer1@microloan.com")))
    assert "Priya Sharma is now deactivated. They still hold 1 loan that needs reassigning" in html
    assert "alert-warning" in html


def test_the_warning_uses_the_plural_for_two_loans(admin, user_id):
    reassign(admin, 6, user_id("officer2@microloan.com"))  # Rahul now holds LN-0005 and LN-0006
    html = text(toggle(admin, user_id("officer2@microloan.com")))
    assert "They still hold 2 loans that need reassigning" in html


def test_no_warning_when_the_officer_holds_nothing_pending(admin, priya, user_id):
    action(priya, 6, "reject", remarks="no")
    html = text(toggle(admin, user_id("officer1@microloan.com")))
    assert "Priya Sharma is now deactivated." in html and "They still hold" not in html and "alert-success" in html


def test_reactivating_gives_the_plain_message(admin, user_id):
    toggle(admin, user_id("officer1@microloan.com"))
    html = text(toggle(admin, user_id("officer1@microloan.com")))
    assert "Priya Sharma is now active." in html and "They still hold" not in html


def test_deactivating_a_borrower_gives_no_reassign_warning(admin, user_id):
    html = text(toggle(admin, user_id("aman@example.com")))
    assert "Aman Gupta is now deactivated." in html and "reassigning" not in html


def test_an_admin_cannot_deactivate_themselves(admin, user_id):
    assert "You cannot deactivate your own account." in text(toggle(admin, user_id("admin@microloan.com")))


def test_after_the_warning_the_loans_can_be_moved_to_an_active_officer(admin, state, user_id):
    toggle(admin, user_id("officer1@microloan.com"))
    reassign(admin, 6, user_id("officer2@microloan.com"))
    assert state(6)[1] == "Rahul Verma"
