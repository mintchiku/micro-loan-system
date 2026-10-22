"""Form validation helpers and the CSRF token helper."""
import math
import re
import secrets

from flask import session

from app.models import User

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")  # something@something.something
PHONE_RE = re.compile(r"^\d{10}$")  # exactly 10 digits


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


def to_int(text):
    """Convert text to a whole number, or return None if it is not one."""
    try:
        return int(str(text).strip())
    except (TypeError, ValueError):
        return None


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
        errors["email"] = "This email is already registered."

    if not PHONE_RE.match(values["phone"]):
        errors["phone"] = "Phone must be exactly 10 digits."

    if with_income:
        income = to_float(values["monthly_income"])
        if income is None or income <= 0:
            errors["monthly_income"] = "Monthly income must be a number greater than 0."

    has_letter = any(ch.isalpha() for ch in password)
    has_digit = any(ch.isdigit() for ch in password)
    if len(password) < 8 or not has_letter or not has_digit:
        errors["password"] = "Password must be at least 8 characters and contain a letter and a number."
    if password != confirm_password:
        errors["confirm_password"] = "Passwords do not match."

    return values, errors
