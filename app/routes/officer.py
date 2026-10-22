"""Loan officer pages: dashboard, applications list, application detail and review actions."""
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user

from app import db
from app.models import Loan
from app.services import loan_service
from app.services.loan_service import LoanError
from app.utils.decorators import role_required

officer_bp = Blueprint("officer", __name__)

# Status filter tabs on the applications list ("" = all)
STATUS_TABS = [""] + loan_service.STATUS_ORDER


@officer_bp.route("/dashboard")
@role_required("officer")
def dashboard():
    """Officer home: work counts and my pending applications."""
    summary = loan_service.officer_summary(current_user)
    return render_template("officer/dashboard.html", summary=summary)


@officer_bp.route("/applications")
@role_required("officer", "admin")  # admin may look (read-only)
def applications():
    """All applications, with status tabs and search by borrower name or loan ID."""
    status = request.args.get("status", "")
    if status not in STATUS_TABS:
        status = ""
    text = request.args.get("q", "")
    loans = loan_service.search_loans(status, text)
    return render_template("officer/applications.html", loans=loans, status=status, q=text,
                           tabs=STATUS_TABS)


@officer_bp.route("/applications/<int:loan_id>")
@role_required("officer", "admin")
def application_detail(loan_id):
    """Borrower + loan details, document, history, actions and (after disbursal) the schedule."""
    loan = db.get_or_404(Loan, loan_id)
    return render_template("officer/application_detail.html", loan=loan)


@officer_bp.route("/applications/<int:loan_id>/<action>", methods=["POST"])
@role_required("officer")  # only officers can change a loan
def application_action(loan_id, action):
    """Pick up, approve, reject or disburse; every change goes through loan_service.change_status()."""
    loan = db.get_or_404(Loan, loan_id)
    remarks = request.form.get("remarks", "").strip()
    try:
        if action == "pickup":
            loan_service.pick_up_loan(loan, current_user)
            flash(f"You picked up {loan.display_id()} for review.", "success")
        elif action == "approve":
            loan_service.approve_loan(loan, current_user, remarks)
            flash(f"{loan.display_id()} approved. You can now disburse it.", "success")
        elif action == "reject":
            loan_service.reject_loan(loan, current_user, remarks)
            flash(f"{loan.display_id()} rejected.", "info")
        elif action == "disburse":
            loan_service.disburse_loan(loan, current_user)
            flash(f"{loan.display_id()} disbursed. {loan.tenure_months} installments were created.", "success")
        else:
            abort(404)  # unknown action in the URL
    except LoanError as error:
        flash(str(error), "danger")
    return redirect(url_for("officer.application_detail", loan_id=loan.id))
