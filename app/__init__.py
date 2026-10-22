"""Application factory: creates the Flask app and connects all the pieces."""
import os

from flask import Flask, flash, redirect, render_template, request, url_for
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy

from config import Config

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "auth.login"  # where @role_required sends logged-out users
login_manager.login_message = "Please log in to continue."
login_manager.login_message_category = "warning"


def create_app(config_class=Config):
    """Build and return a configured Flask application."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Make sure instance/ (database) and uploads/ exist
    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)

    # Blueprints are imported here (not at the top) to avoid circular imports
    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    from app.routes.borrower import borrower_bp
    from app.routes.officer import officer_bp
    from app.routes.admin import admin_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(borrower_bp, url_prefix="/borrower")
    app.register_blueprint(officer_bp, url_prefix="/officer")
    app.register_blueprint(admin_bp, url_prefix="/admin")

    # Jinja filters: {{ loan.amount|inr }} and {{ loan.applied_on|date }}
    from app.utils.formatters import format_date, inr

    app.jinja_env.filters["inr"] = inr
    app.jinja_env.filters["date"] = format_date

    register_csrf(app)
    register_error_handlers(app)

    # Create tables on first run and make sure the single settings row exists
    from app.models import LoanSetting

    with app.app_context():
        db.create_all()
        if db.session.get(LoanSetting, 1) is None:
            db.session.add(LoanSetting(id=1))
            db.session.commit()

    return app


def register_csrf(app):
    """Check the CSRF token on every POST and make csrf_token() available in templates."""
    from app.utils.validators import csrf_token_is_valid, get_csrf_token

    app.jinja_env.globals["csrf_token"] = get_csrf_token

    @app.before_request
    def check_csrf():
        """Reject a POST whose form does not carry this session's token."""
        if request.method == "POST" and not csrf_token_is_valid(request.form.get("csrf_token")):
            flash("Your form expired or was invalid. Please try again.", "warning")
            # go back to the page the form was on (only if it is a page of this site)
            back = request.referrer if (request.referrer or "").startswith(request.host_url) else None
            return redirect(back or url_for("main.index"))


def register_error_handlers(app):
    """Show friendly 403 / 404 / 500 pages that use base.html."""

    @app.errorhandler(403)
    def forbidden(error):
        """User is logged in but not allowed to see this page."""
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(error):
        """Page or record does not exist (or is not yours)."""
        return render_template("errors/404.html"), 404

    @app.errorhandler(413)
    def too_large(error):
        """Upload bigger than MAX_CONTENT_LENGTH: go back to the form with a message."""
        flash("The file is too large. The maximum size is 2 MB.", "danger")
        return redirect(request.url)

    @app.errorhandler(500)
    def server_error(error):
        """Unexpected error: undo any half-finished database change."""
        db.session.rollback()
        return render_template("errors/500.html"), 500
