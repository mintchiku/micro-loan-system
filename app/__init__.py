"""Application factory: creates the Flask app and connects all the pieces."""
import os

from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy

from config import Config

db = SQLAlchemy()
login_manager = LoginManager()


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

    # Create tables on first run and make sure the single settings row exists
    from app.models import LoanSetting

    with app.app_context():
        db.create_all()
        if db.session.get(LoanSetting, 1) is None:
            db.session.add(LoanSetting(id=1))
            db.session.commit()

    return app
