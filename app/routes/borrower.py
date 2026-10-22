"""Borrower pages."""
from flask import Blueprint, render_template

from app.utils.decorators import role_required

borrower_bp = Blueprint("borrower", __name__)


@borrower_bp.route("/dashboard")
@role_required("borrower")
def dashboard():
    """Borrower home page (placeholder until a later phase)."""
    return render_template("borrower/dashboard.html")
