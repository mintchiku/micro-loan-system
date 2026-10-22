"""Business rules and status changes (CLAUDE.md §6, §7). Routes call these; rules live only here."""
import os
import re
import uuid
from datetime import date, datetime

from flask import current_app
from werkzeug.utils import secure_filename

from app import db
from app.models import ACTIVE_STATUSES, Document, Loan, LoanSetting, Repayment, User
from app.services.emi import add_months, build_schedule, calculate_emi, max_affordable_amount
from app.utils.formatters import inr

# All loan statuses in lifecycle order (used for reports)
STATUS_ORDER = ["Applied", "Under Review", "Approved", "Disbursed", "Repaying", "Closed", "Rejected", "Cancelled"]

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
MAX_DOCUMENT_BYTES = 2 * 1024 * 1024  # 2 MB

# The loan state machine: (from status, to status) -> who may make that change (§6)
ALLOWED_TRANSITIONS = {
    ("Applied", "Cancelled"): "borrower",
    ("Applied", "Under Review"): "officer",
    ("Under Review", "Approved"): "officer",
    ("Under Review", "Rejected"): "officer",
    ("Approved", "Disbursed"): "officer",
    ("Disbursed", "Repaying"): "system",
    ("Repaying", "Closed"): "system",
}


class LoanError(Exception):
    """Raised when an action breaks a rule; the message is shown to the user."""


# ---------- State machine ----------

def change_status(loan, new_status, actor):
    """Move a loan to new_status if the transition table allows it for this actor (a User or "system")."""
    allowed_role = ALLOWED_TRANSITIONS.get((loan.status, new_status))
    if allowed_role is None:
        raise LoanError(f"{loan.display_id()} cannot move from {loan.status} to {new_status}.")

    actor_role = "system" if actor == "system" else actor.role
    if actor_role != allowed_role:
        raise LoanError(f"Only the {allowed_role} can move a loan from {loan.status} to {new_status}.")
    if allowed_role == "borrower" and loan.borrower_id != actor.id:
        raise LoanError("You can only change your own loans.")
    # Rule 11: once picked up, only the assigned officer can act on the loan
    if allowed_role == "officer" and loan.status != "Applied" and loan.officer_id != actor.id:
        raise LoanError("Only the officer who picked up this application can do this.")

    loan.status = new_status


# ---------- Settings and lookups ----------

def get_settings():
    """Return the single LoanSetting row (id = 1)."""
    return db.session.get(LoanSetting, 1)


def sample_loan(settings):
    """Example loan for the landing page, built from the current settings so it is never out of date."""
    amount = min(max(50000, settings.min_amount), settings.max_amount)  # keep the example inside the limits
    tenure = min(max(12, settings.min_tenure), settings.max_tenure)
    emi = calculate_emi(amount, settings.interest_rate, tenure)
    total = round(emi * tenure, 2)
    return {"amount": amount, "tenure": tenure, "rate": settings.interest_rate,
            "emi": emi, "total": total, "interest": round(total - amount, 2)}


def get_active_loan(borrower):
    """Return the borrower's current active loan, or None."""
    return (Loan.query.filter(Loan.borrower_id == borrower.id, Loan.status.in_(ACTIVE_STATUSES))
            .order_by(Loan.applied_on.desc()).first())


# ---------- Users ----------

def create_user(values, password, role):
    """Create and save a new borrower (self-registration) or officer (created by admin)."""
    user = User(
        name=values["name"],
        email=values["email"],
        phone=values["phone"],
        role=role,
        # only borrowers have an income; it is needed for the affordability rule
        monthly_income=float(values["monthly_income"]) if role == "borrower" else None,
    )
    user.set_password(password)
    try:
        db.session.add(user)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return user


# ---------- Applying for a loan (rules 1, 2, 3, 4, 6, 10) ----------

def check_document(file):
    """Rule 10: one PDF/JPG/PNG file up to 2 MB. Returns an error message or None."""
    if file is None or file.filename == "":
        return "Please upload a supporting document (PDF, JPG or PNG)."
    extension = os.path.splitext(file.filename)[1].lower()
    if extension not in ALLOWED_EXTENSIONS:
        return "Only PDF, JPG or PNG files are allowed."
    file.stream.seek(0, os.SEEK_END)  # jump to the end to measure the size
    size = file.stream.tell()
    file.stream.seek(0)  # rewind so the file can be saved later
    if size == 0:
        return "The file is empty."
    if size > MAX_DOCUMENT_BYTES:
        return "The file is larger than 2 MB."
    return None


def check_affordability(borrower, amount, tenure, settings):
    """Rule 4: EMI must be within max_emi_to_income % of income. Returns an error message or None."""
    emi = calculate_emi(amount, settings.interest_rate, tenure)
    max_emi = (borrower.monthly_income or 0) * settings.max_emi_to_income / 100
    if emi <= max_emi:
        return None
    max_amount = min(max_affordable_amount(max_emi, settings.interest_rate, tenure), settings.max_amount)
    message = (f"The EMI of {inr(emi)} is more than {settings.max_emi_to_income:g}% of your monthly "
               f"income (limit {inr(max_emi)}). For {tenure} months you can borrow at most {inr(max_amount)}.")
    if max_amount < settings.min_amount:
        message += " That is below the minimum loan amount; try a longer tenure."
    return message


def check_application(borrower, amount, tenure, purpose, file, settings):
    """Check rules 1-4 and 10. Returns {field: message}; empty when the application is valid."""
    if borrower.has_active_loan():  # rule 3
        return {"form": "You already have an active loan. You can apply again once it is "
                        "closed, rejected or cancelled."}

    errors = {}
    if amount is None:
        errors["amount"] = "Enter the loan amount."
    elif not settings.min_amount <= amount <= settings.max_amount:  # rule 1
        errors["amount"] = f"Amount must be between {inr(settings.min_amount)} and {inr(settings.max_amount)}."

    if tenure is None:
        errors["tenure_months"] = "Enter the tenure in whole months."
    elif not settings.min_tenure <= tenure <= settings.max_tenure:  # rule 2
        errors["tenure_months"] = f"Tenure must be between {settings.min_tenure} and {settings.max_tenure} months."

    if not purpose:
        errors["purpose"] = "Purpose is required."
    elif len(purpose) > 200:
        errors["purpose"] = "Purpose must be at most 200 characters."

    document_error = check_document(file)
    if document_error:
        errors["document"] = document_error

    # Rule 4 is only checked once amount and tenure themselves are valid
    if "amount" not in errors and "tenure_months" not in errors:
        affordability_error = check_affordability(borrower, amount, tenure, settings)
        if affordability_error:
            errors["amount"] = affordability_error
    return errors


def apply_for_loan(borrower, amount, tenure, purpose, file):
    """Validate and save a new Applied loan with its document. Returns (loan, errors)."""
    settings = get_settings()
    errors = check_application(borrower, amount, tenure, purpose, file, settings)
    if errors:
        return None, errors

    loan = Loan(
        borrower_id=borrower.id,
        amount=amount,
        tenure_months=tenure,
        interest_rate=settings.interest_rate,  # rule 6: rate is locked at apply time
        emi_amount=calculate_emi(amount, settings.interest_rate, tenure),
        purpose=purpose,
        status="Applied",
        applied_on=datetime.now(),
    )
    extension = os.path.splitext(file.filename)[1].lower()
    stored_name = uuid.uuid4().hex + extension  # random name: no clashes, no user-chosen paths
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], stored_name)
    original_name = (secure_filename(file.filename) or "document" + extension)[:200]

    try:
        file.save(path)
        loan.document = Document(original_name=original_name, stored_name=stored_name,
                                 uploaded_on=datetime.now())
        db.session.add(loan)
        db.session.commit()
    except Exception:
        db.session.rollback()
        if os.path.exists(path):
            os.remove(path)  # the loan was not saved, so remove the file we just wrote
        raise
    return loan, {}


def cancel_loan(loan, borrower):
    """Borrower cancels their own application (only allowed while Applied)."""
    try:
        change_status(loan, "Cancelled", borrower)
        db.session.commit()
    except Exception:
        db.session.rollback()  # NFR9: nothing is half-saved
        raise


# ---------- Officer review workflow (rule 11 is enforced inside change_status) ----------

def search_loans(status="", text=""):
    """Loans for the applications list, filtered by status and by borrower name or loan ID."""
    query = Loan.query.join(User, Loan.borrower_id == User.id)
    if status:
        query = query.filter(Loan.status == status)
    text = text.strip()
    if text:
        id_match = re.fullmatch(r"(?:LN-?)?(\d+)", text, re.IGNORECASE)  # "LN-0007", "ln7" or "7"
        if id_match:
            query = query.filter(Loan.id == int(id_match.group(1)))
        else:
            query = query.filter(User.name.ilike(f"%{text}%"))
    return query.order_by(Loan.applied_on.desc()).all()


def officer_summary(officer):
    """Counts and pending-work list for the officer dashboard."""
    my_pending = (Loan.query.filter(Loan.officer_id == officer.id,
                                    Loan.status.in_(("Under Review", "Approved")))
                  .order_by(Loan.applied_on).all())
    return {
        "new_count": Loan.query.filter_by(status="Applied").count(),
        "review_count": sum(1 for loan in my_pending if loan.status == "Under Review"),
        "approved_count": sum(1 for loan in my_pending if loan.status == "Approved"),
        "my_pending": my_pending,
    }


def pick_up_loan(loan, officer):
    """Officer takes an Applied loan for review; from now on only they can act on it."""
    try:
        change_status(loan, "Under Review", officer)
        loan.officer_id = officer.id
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise


def approve_loan(loan, officer, remarks=""):
    """Assigned officer approves the loan (remarks optional)."""
    if len(remarks) > 300:
        raise LoanError("Remarks must be at most 300 characters.")
    try:
        change_status(loan, "Approved", officer)
        loan.reviewed_on = datetime.now()
        loan.remarks = remarks or None
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise


def reject_loan(loan, officer, remarks):
    """Assigned officer rejects the loan; a reason (remarks) is required."""
    if not remarks:
        raise LoanError("Please enter remarks explaining why the application is rejected.")
    if len(remarks) > 300:
        raise LoanError("Remarks must be at most 300 characters.")
    try:
        change_status(loan, "Rejected", officer)
        loan.reviewed_on = datetime.now()
        loan.remarks = remarks
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise


def disburse_loan(loan, officer):
    """Assigned officer pays out the loan; the EMI schedule is generated now (rule 7)."""
    try:
        change_status(loan, "Disbursed", officer)
        loan.disbursed_on = date.today()
        for row in build_schedule(loan, loan.disbursed_on):
            loan.repayments.append(Repayment(installment_no=row["installment_no"], due_date=row["due_date"],
                                             amount=row["amount"], status="Pending"))
        db.session.commit()  # status change and all installments are saved together
    except Exception:
        db.session.rollback()
        raise


# ---------- Repayments (rules 8 and 9) ----------

def pay_installment(loan, borrower, repayment_id):
    """Simulated payment of the earliest Pending installment; moves the loan to Repaying / Closed."""
    if loan.borrower_id != borrower.id:
        raise LoanError("You can only pay your own loans.")
    if loan.status not in ("Disbursed", "Repaying"):
        raise LoanError("This loan has no installments to pay.")
    next_due = loan.next_due_installment()
    if next_due is None or next_due.id != repayment_id:  # rule 8: strictly in order
        raise LoanError("Only the earliest pending installment can be paid.")

    try:
        next_due.status = "Paid"
        next_due.paid_on = date.today()
        if loan.status == "Disbursed":  # first payment
            change_status(loan, "Repaying", "system")
        if loan.next_due_installment() is None:  # that was the last one
            change_status(loan, "Closed", "system")
            loan.closed_on = date.today()
        db.session.commit()  # payment and status change are saved together
    except Exception:
        db.session.rollback()
        raise
    return next_due


def borrower_summary(borrower):
    """Active loan, next installment, overdue count and recent payments for the borrower dashboard."""
    active_loan = get_active_loan(borrower)
    recent_payments = (Repayment.query.join(Loan)
                       .filter(Loan.borrower_id == borrower.id, Repayment.status == "Paid")
                       .order_by(Repayment.paid_on.desc(), Repayment.id.desc()).limit(5).all())
    return {
        "active_loan": active_loan,
        "next_due": active_loan.next_due_installment() if active_loan else None,
        "overdue_count": sum(1 for r in active_loan.repayments if r.is_overdue()) if active_loan else 0,
        "recent_payments": recent_payments,
    }


# ---------- Admin: users and settings ----------

def search_users(role="", text=""):
    """Users for the admin list, filtered by role and by name or email."""
    query = User.query
    if role:
        query = query.filter(User.role == role)
    text = text.strip()
    if text:
        query = query.filter(User.name.ilike(f"%{text}%") | User.email.ilike(f"%{text}%"))
    return query.order_by(User.role, User.name).all()


def toggle_user_active(user, admin):
    """Activate or deactivate a user. An admin cannot deactivate themselves."""
    if user.id == admin.id:
        raise LoanError("You cannot deactivate your own account.")
    try:
        user.is_active = not user.is_active
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise


def update_settings(numbers):
    """Save new loan settings. Existing loans keep their own rate (rule 6)."""
    settings = get_settings()
    try:
        for field, value in numbers.items():
            setattr(settings, field, value)
        settings.updated_at = datetime.now()
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return settings


# ---------- Admin: dashboard totals and reports ----------

def overdue_installments():
    """All Pending installments whose due date has passed, oldest first."""
    return (Repayment.query.filter(Repayment.status == "Pending", Repayment.due_date < date.today())
            .order_by(Repayment.due_date).all())


def admin_totals():
    """Numbers for the admin dashboard: users, loans by status and money totals."""
    loans = Loan.query.all()
    repayments = Repayment.query.all()
    loans_by_status = {status: 0 for status in STATUS_ORDER}
    for loan in loans:
        loans_by_status[loan.status] += 1
    users_by_role = {role: User.query.filter_by(role=role).count() for role in ("borrower", "officer", "admin")}
    return {
        "users_by_role": users_by_role,
        "total_users": sum(users_by_role.values()),
        "loans_by_status": loans_by_status,
        "total_loans": len(loans),
        "disbursed": round(sum(loan.amount for loan in loans if loan.disbursed_on), 2),
        "collected": round(sum(r.amount for r in repayments if r.status == "Paid"), 2),
        "outstanding": round(sum(r.amount for r in repayments if r.status == "Pending"), 2),
        "overdue_count": sum(1 for r in repayments if r.is_overdue()),
    }


def disbursed_per_month(months=6):
    """Amount disbursed in each of the last `months` months (oldest first), for the bar chart."""
    first_of_this_month = date.today().replace(day=1)
    month_starts = [add_months(first_of_this_month, -i) for i in range(months - 1, -1, -1)]
    totals = {(m.year, m.month): 0 for m in month_starts}
    for loan in Loan.query.filter(Loan.disbursed_on.isnot(None)).all():
        key = (loan.disbursed_on.year, loan.disbursed_on.month)
        if key in totals:
            totals[key] += loan.amount
    return {
        "labels": [m.strftime("%b %Y") for m in month_starts],
        "values": [round(totals[(m.year, m.month)], 2) for m in month_starts],
    }
