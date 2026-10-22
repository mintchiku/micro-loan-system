"""Register, login and logout."""
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.models import User
from app.services import loan_service
from app.utils.decorators import dashboard_url
from app.utils.validators import validate_user_form

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """Public sign-up. The new account is ALWAYS a borrower."""
    if current_user.is_authenticated:
        return redirect(dashboard_url(current_user))

    values, errors = {}, {}
    if request.method == "POST":
        values, errors = validate_user_form(request.form, with_income=True)
        if not errors:
            user, errors = loan_service.create_user(values, request.form["password"], role="borrower")
            if user:  # on a failure (for example a duplicate email) the form is shown again with the message
                login_user(user)
                flash(f"Welcome, {user.name}! Your account has been created.", "success")
                return redirect(url_for("borrower.dashboard"))
    return render_template("auth/register.html", values=values, errors=errors)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Log in with email + password, then go to the dashboard for the user's role."""
    if current_user.is_authenticated:
        return redirect(dashboard_url(current_user))

    email, error = "", None
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        user = User.query.filter_by(email=email).first()
        if user is None or not user.check_password(request.form.get("password", "")):
            error = "Invalid email or password."
        elif not user.is_active:
            error = "Your account has been deactivated. Please contact the admin."
        else:
            login_user(user)
            flash(f"Welcome back, {user.name}!", "success")
            return redirect(dashboard_url(user))
    return render_template("auth/login.html", email=email, error=error)


@auth_bp.route("/logout", methods=["POST"])  # POST only: a link or an image tag cannot log someone out
@login_required
def logout():
    """Log out and go back to the landing page."""
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.index"))
