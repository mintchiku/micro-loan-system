"""WSGI entry point for PythonAnywhere: the web app imports `application` from here."""
import os
import sys

from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)  # so `import app` and `import config` work
load_dotenv(os.path.join(BASE_DIR, ".env"))  # SECRET_KEY must be set before config.py is imported

from app import create_app  # noqa: E402

application = create_app()
