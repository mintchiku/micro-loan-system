"""Admin pages."""
from flask import Blueprint, render_template

from app.utils.decorators import role_required

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/dashboard")
@role_required("admin")
def dashboard():
    """Admin home page (placeholder until a later phase)."""
    return render_template("admin/dashboard.html")
