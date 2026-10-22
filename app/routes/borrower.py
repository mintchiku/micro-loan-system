"""Borrower pages: dashboard, apply, my loans, loan details, cancel."""
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user

from app import db
from app.models import Loan
from app.services import loan_service
from app.services.loan_service import LoanError
from app.utils.decorators import role_required
from app.utils.validators import to_float, to_int

borrower_bp = Blueprint("borrower", __name__)


def get_own_loan_or_404(loan_id):
    """Return the loan if it belongs to the logged-in borrower; otherwise show 404 (NFR3)."""
    loan = db.get_or_404(Loan, loan_id)
    if loan.borrower_id != current_user.id:
        abort(404)  # do not even reveal that someone else's loan exists
    return loan


@borrower_bp.route("/dashboard")
@role_required("borrower")
def dashboard():
    """Borrower home: active loan card and Apply button."""
    active_loan = loan_service.get_active_loan(current_user)
    return render_template("borrower/dashboard.html", active_loan=active_loan)


@borrower_bp.route("/apply", methods=["GET", "POST"])
@role_required("borrower")
def apply():
    """Loan application form with live EMI preview."""
    settings = loan_service.get_settings()
    values, errors = {}, {}
    if request.method == "POST":
        values = {
            "amount": request.form.get("amount", "").strip(),
            "tenure_months": request.form.get("tenure_months", "").strip(),
            "purpose": request.form.get("purpose", "").strip(),
        }
        loan, errors = loan_service.apply_for_loan(
            current_user, to_float(values["amount"]), to_int(values["tenure_months"]),
            values["purpose"], request.files.get("document"),
        )
        if loan:
            flash(f"Application {loan.display_id()} submitted. An officer will review it soon.", "success")
            return redirect(url_for("borrower.loan_detail", loan_id=loan.id))
    return render_template("borrower/apply.html", settings=settings, values=values, errors=errors,
                           has_active_loan=current_user.has_active_loan())


@borrower_bp.route("/loans")
@role_required("borrower")
def loans():
    """List of all the borrower's loans, newest first."""
    my_loans = Loan.query.filter_by(borrower_id=current_user.id).order_by(Loan.applied_on.desc()).all()
    return render_template("borrower/loans.html", loans=my_loans)


@borrower_bp.route("/loans/<int:loan_id>")
@role_required("borrower")
def loan_detail(loan_id):
    """One loan with its status, amounts and officer remarks."""
    loan = get_own_loan_or_404(loan_id)
    return render_template("borrower/loan_detail.html", loan=loan)


@borrower_bp.route("/loans/<int:loan_id>/cancel", methods=["POST"])
@role_required("borrower")
def cancel(loan_id):
    """Cancel an application that is still Applied."""
    loan = get_own_loan_or_404(loan_id)
    try:
        loan_service.cancel_loan(loan, current_user)
        flash(f"Application {loan.display_id()} has been cancelled.", "info")
    except LoanError as error:
        flash(str(error), "danger")
    return redirect(url_for("borrower.loan_detail", loan_id=loan.id))
