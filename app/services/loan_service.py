"""Business rules and status changes (CLAUDE.md §6, §7). Routes call these; rules live only here."""
import os
import uuid
from datetime import datetime

from flask import current_app
from werkzeug.utils import secure_filename

from app import db
from app.models import ACTIVE_STATUSES, Document, Loan, LoanSetting, User
from app.services.emi import calculate_emi, max_affordable_amount
from app.utils.formatters import inr

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
