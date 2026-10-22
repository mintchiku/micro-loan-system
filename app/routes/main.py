"""Public landing page and the protected document viewer."""
from flask import Blueprint, abort, current_app, render_template, send_from_directory
from flask_login import current_user

from app import db
from app.models import Document
from app.services import loan_service
from app.utils.decorators import role_required

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    """Landing page that explains the service, using the current loan limits."""
    settings = loan_service.get_settings()
    return render_template("main/index.html", settings=settings, sample=loan_service.sample_loan(settings))


@main_bp.route("/documents/<int:document_id>")
@role_required("borrower", "officer", "admin")
def view_document(document_id):
    """Show an uploaded document to its owner, any officer or the admin (NFR3, NFR5)."""
    document = db.get_or_404(Document, document_id)
    is_owner = document.loan.borrower_id == current_user.id
    if current_user.role == "borrower" and not is_owner:
        abort(404)
    # Files are in uploads/ (not static/), so this route is the only way to reach them
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], document.stored_name,
                               download_name=document.original_name)
