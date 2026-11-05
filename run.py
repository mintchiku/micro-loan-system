"""Entry point: python run.py, then open http://127.0.0.1:5000"""
import os

from dotenv import load_dotenv

load_dotenv()  # read .env before config.py is imported

from app import create_app  # noqa: E402

app = create_app()

if __name__ == "__main__":
    # debug reloads on code changes and shows errors; only when FLASK_DEBUG=1 (default off)
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
