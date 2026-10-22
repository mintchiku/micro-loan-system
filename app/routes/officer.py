"""Officer pages."""
from flask import Blueprint, render_template

from app.utils.decorators import role_required

officer_bp = Blueprint("officer", __name__)


@officer_bp.route("/dashboard")
@role_required("officer")
def dashboard():
    """Officer home page (placeholder until a later phase)."""
    return render_template("officer/dashboard.html")
