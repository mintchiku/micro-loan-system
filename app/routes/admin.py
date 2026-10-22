"""Admin pages: dashboard, users, create officer, loan settings, reports."""
from datetime import date

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user

from app import db
from app.models import User
from app.services import loan_service
from app.services.loan_service import LoanError
from app.utils.decorators import role_required
from app.utils.validators import SETTING_FIELDS, validate_settings_form, validate_user_form

admin_bp = Blueprint("admin", __name__)

# Pie chart colours: same hue families as the status badges (§9), stepped apart so neighbouring slices
# stay distinguishable (checked with the dataviz palette validator)
STATUS_COLORS = {
    "Applied": "#B4BED3", "Under Review": "#0C86B0", "Approved": "#1D4FBF", "Disbursed": "#F5B800",
    "Repaying": "#8C5300", "Closed": "#6FD3AA", "Rejected": "#9E1F33", "Cancelled": "#2B3447",
}


@admin_bp.route("/dashboard")
@role_required("admin")
def dashboard():
    """Admin home: totals for users, loans and money."""
    return render_template("admin/dashboard.html", totals=loan_service.admin_totals())


@admin_bp.route("/users")
@role_required("admin")
def users():
    """All users with role filter and search by name or email."""
    role = request.args.get("role", "")
    if role not in ("", "borrower", "officer", "admin"):
        role = ""
    text = request.args.get("q", "")
    return render_template("admin/users.html", users=loan_service.search_users(role, text), role=role, q=text)


@admin_bp.route("/users/new-officer", methods=["GET", "POST"])
@role_required("admin")
def new_officer():
    """Create a loan officer account (same checks as registration, no income)."""
    values, errors = {}, {}
    if request.method == "POST":
        values, errors = validate_user_form(request.form, with_income=False)
        if not errors:
            officer, errors = loan_service.create_user(values, request.form["password"], role="officer")
            if officer:
                flash(f"Officer account created for {officer.name}.", "success")
                return redirect(url_for("admin.users", role="officer"))
    return render_template("admin/new_officer.html", values=values, errors=errors)


@admin_bp.route("/users/<int:user_id>/toggle", methods=["POST"])
@role_required("admin")
def toggle_user(user_id):
    """Activate or deactivate a user."""
    user = db.get_or_404(User, user_id)
    try:
        loan_service.toggle_user_active(user, current_user)
        message = f"{user.name} is now {'active' if user.is_active else 'deactivated'}."
        stuck = loan_service.pending_loan_count(user) if user.role == "officer" and not user.is_active else 0
        if stuck:  # a deactivated officer's loans cannot move until an admin reassigns them
            flash(f"{message} They still hold {stuck} loan{'s' if stuck != 1 else ''} that "
                  f"{'needs' if stuck == 1 else 'need'} reassigning: open each application and choose another officer.",
                  "warning")
        else:
            flash(message, "success")
    except LoanError as error:
        flash(str(error), "danger")
    return redirect(url_for("admin.users"))


@admin_bp.route("/settings", methods=["GET", "POST"])
@role_required("admin")
def settings():
    """Edit the loan settings; changes only affect new applications."""
    current = loan_service.get_settings()
    errors = {}
    if request.method == "POST":
        values, numbers, errors = validate_settings_form(request.form)
        if not errors:
            loan_service.update_settings(numbers)
            flash("Loan settings saved. They apply to new applications only.", "success")
            return redirect(url_for("admin.settings"))
    else:
        # show the saved values without trailing ".0" (12.0 -> 12)
        values = {field: f"{getattr(current, field):g}" for field in SETTING_FIELDS}
    return render_template("admin/settings.html", values=values, errors=errors, settings=current)


@admin_bp.route("/reports")
@role_required("admin")
def reports():
    """Charts (loans by status, disbursed per month) and the overdue installments table."""
    totals = loan_service.admin_totals()
    status_chart = {
        "labels": list(totals["loans_by_status"].keys()),
        "values": list(totals["loans_by_status"].values()),
        "colors": [STATUS_COLORS[s] for s in totals["loans_by_status"]],
        "shares": loan_service.percent_shares(list(totals["loans_by_status"].values())),  # adds up to 100.0
    }
    return render_template("admin/reports.html", status_chart=status_chart,
                           month_chart=loan_service.disbursed_per_month(),
                           overdue=loan_service.overdue_installments(), today=date.today())
