"""Form validation helpers and the CSRF token helper."""
import math
import re
import secrets
from decimal import Decimal, InvalidOperation

from flask import session

from app.models import User

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")  # something@something.something
PHONE_RE = re.compile(r"^\d{10}$")  # exactly 10 digits

DECIMALS_MESSAGE = "Use at most 2 decimal places."  # money has paise: two digits after the point
EMAIL_TAKEN_MESSAGE = "This email is already registered."


# ---------- CSRF (one random token per session, checked on every POST) ----------

def get_csrf_token():
    """Return this session's CSRF token, creating it the first time."""
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(16)
    return session["csrf_token"]


def csrf_token_is_valid(form_token):
    """Return True if the token sent by the form matches the session token."""
    session_token = session.get("csrf_token", "")
    # compare_digest avoids leaking information through timing differences
    return bool(form_token) and bool(session_token) and secrets.compare_digest(form_token, session_token)


# ---------- Small parsing helpers ----------

def to_float(text):
    """Convert text to a float, or return None if it is not a valid number."""
    try:
        number = float(text)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None  # reject "nan" and "inf"


def has_too_many_decimals(value, places=2):
    """True if a number (or the text typed for it) has more than `places` digits after the decimal point."""
    try:
        number = Decimal(str(value).strip()).normalize()  # normalize drops trailing zeros: 10.50 is fine
    except InvalidOperation:
        return False  # not a number at all; the caller reports that separately
    return number.is_finite() and number.as_tuple().exponent < -places


def to_int(text):
    """Convert text to a whole number, or return None if it is not one."""
    try:
        return int(str(text).strip())
    except (TypeError, ValueError):
        return None


# ---------- Loan settings form (admin) ----------

SETTING_FIELDS = ["interest_rate", "min_amount", "max_amount", "min_tenure", "max_tenure", "max_emi_to_income"]


def validate_settings_form(form):
    """Check the loan settings form. Returns (values as typed, parsed numbers, errors)."""
    values = {field: form.get(field, "").strip() for field in SETTING_FIELDS}
    numbers = {
        "interest_rate": to_float(values["interest_rate"]),
        "min_amount": to_float(values["min_amount"]),
        "max_amount": to_float(values["max_amount"]),
        "min_tenure": to_int(values["min_tenure"]),
        "max_tenure": to_int(values["max_tenure"]),
        "max_emi_to_income": to_float(values["max_emi_to_income"]),
    }
    errors = {}

    if numbers["interest_rate"] is None or not 0 <= numbers["interest_rate"] <= 36:
        errors["interest_rate"] = "Interest rate must be between 0 and 36 % per year."

    if numbers["min_amount"] is None or numbers["min_amount"] <= 0:
        errors["min_amount"] = "Minimum amount must be a number greater than 0."
    elif has_too_many_decimals(values["min_amount"]):
        errors["min_amount"] = DECIMALS_MESSAGE
    if numbers["max_amount"] is None or numbers["max_amount"] <= 0:
        errors["max_amount"] = "Maximum amount must be a number greater than 0."
    elif has_too_many_decimals(values["max_amount"]):
        errors["max_amount"] = DECIMALS_MESSAGE
    elif "min_amount" not in errors and numbers["max_amount"] <= numbers["min_amount"]:
        errors["max_amount"] = "Maximum amount must be greater than the minimum amount."

    if numbers["min_tenure"] is None or numbers["min_tenure"] < 1:
        errors["min_tenure"] = "Minimum tenure must be a whole number of months (at least 1)."
    if numbers["max_tenure"] is None or numbers["max_tenure"] < 1:
        errors["max_tenure"] = "Maximum tenure must be a whole number of months (at least 1)."
    elif "min_tenure" not in errors and numbers["max_tenure"] <= numbers["min_tenure"]:
        errors["max_tenure"] = "Maximum tenure must be greater than the minimum tenure."

    if numbers["max_emi_to_income"] is None or not 1 <= numbers["max_emi_to_income"] <= 100:
        errors["max_emi_to_income"] = "EMI-to-income limit must be between 1 and 100 %."

    return values, numbers, errors


# ---------- User forms (borrower registration, create officer) ----------

def validate_user_form(form, with_income=True):
    """Check a registration form. Returns (values, errors); errors is empty when all is fine."""
    values = {
        "name": form.get("name", "").strip(),
        "email": form.get("email", "").strip().lower(),  # emails are stored in lowercase
        "phone": form.get("phone", "").strip(),
        "monthly_income": form.get("monthly_income", "").strip(),
    }
    password = form.get("password", "")
    confirm_password = form.get("confirm_password", "")
    errors = {}

    if not values["name"]:
        errors["name"] = "Name is required."
    elif len(values["name"]) > 100:
        errors["name"] = "Name must be at most 100 characters."

    if not EMAIL_RE.match(values["email"]) or len(values["email"]) > 120:
        errors["email"] = "Enter a valid email address."
    elif User.query.filter_by(email=values["email"]).first():
        errors["email"] = EMAIL_TAKEN_MESSAGE

    if not PHONE_RE.match(values["phone"]):
        errors["phone"] = "Phone must be exactly 10 digits."

    if with_income:
        income = to_float(values["monthly_income"])
        if income is None or income <= 0:
            errors["monthly_income"] = "Monthly income must be a number greater than 0."
        elif has_too_many_decimals(values["monthly_income"]):  # income is money too: at most 2 decimals
            errors["monthly_income"] = DECIMALS_MESSAGE

    has_letter = any(ch.isalpha() for ch in password)
    has_digit = any(ch.isdigit() for ch in password)
    if len(password) < 8 or not has_letter or not has_digit:
        errors["password"] = "Password must be at least 8 characters and contain a letter and a number."
    if password != confirm_password:
        errors["confirm_password"] = "Passwords do not match."

    return values, errors
