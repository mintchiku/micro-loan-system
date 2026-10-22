"""Entry point: python run.py, then open http://127.0.0.1:5000"""
from app import create_app

app = create_app()

if __name__ == "__main__":
    # debug=True reloads on code changes and shows errors; for local use only
    app.run(debug=True)
