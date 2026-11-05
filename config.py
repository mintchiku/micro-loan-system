"""App configuration. Secrets come from the .env file (see .env.example)."""
import os

from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))  # reads SECRET_KEY from .env if the file exists


class Config:
    """Settings used by create_app()."""

    # The secret must come from .env (or the environment). Only with FLASK_DEBUG=1 is a throw-away dev key allowed.
    SECRET_KEY = os.environ.get("SECRET_KEY") or ("dev-only-change-me" if os.environ.get("FLASK_DEBUG") == "1" else None)
    if not SECRET_KEY:
        raise RuntimeError("SECRET_KEY is missing: create a .env file next to config.py (see .env.example)")

    # SQLite database file inside the instance/ folder (absolute: works from any start directory)
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(BASE_DIR, "instance", "microloan.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Uploaded loan documents live outside static/ so they are not publicly reachable
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")

    # SameSite=Lax: the browser does not send the session cookie with cross-site POST requests (extra CSRF defence).
    SESSION_COOKIE_SAMESITE = "Lax"
    # HttpOnly: JavaScript cannot read the session cookie, which limits the damage of a script-injection bug.
    # (Secure is left off because the local development server uses plain http.)
    SESSION_COOKIE_HTTPONLY = True

    # Hard cap for a whole request (file + form fields). The 2 MB file rule is checked in code.
    MAX_CONTENT_LENGTH = 3 * 1024 * 1024
