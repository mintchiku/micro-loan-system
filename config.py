"""App configuration. Secrets come from the .env file (see .env.example)."""
import os

from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))  # reads SECRET_KEY from .env if the file exists


class Config:
    """Settings used by create_app()."""

    # Safe default for local development only; set a real value in .env
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")

    # SQLite database file inside the instance/ folder
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(BASE_DIR, "instance", "microloan.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Uploaded loan documents live outside static/ so they are not publicly reachable
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")

    # Hard cap for a whole request (file + form fields). The 2 MB file rule is checked in code.
    MAX_CONTENT_LENGTH = 3 * 1024 * 1024
