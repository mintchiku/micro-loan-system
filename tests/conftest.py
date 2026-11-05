"""Fixtures: every test gets its own app on a temporary copy of a freshly seeded database.

The real database (instance/microloan.db) and the real uploads/ folder are never used: the app is built with a
temporary database file and a temporary upload folder, and a safety fixture refuses to run otherwise.
"""
import os
import shutil
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

os.environ.setdefault("SECRET_KEY", "test-secret-key")  # config.py refuses to load without one

import seed  # noqa: E402  (the demo-data functions are reused to build the test database)
import support  # noqa: E402
from app import create_app, db  # noqa: E402
from app.models import Loan, User  # noqa: E402
from config import Config  # noqa: E402

LIVE_DB = os.path.join(ROOT, "instance", "microloan.db")
LIVE_UPLOADS = os.path.join(ROOT, "uploads")


def make_config(db_path, upload_dir):
    """A Config that points at a temporary database file and upload folder."""
    class TestConfig(Config):
        SQLALCHEMY_DATABASE_URI = "sqlite:///" + db_path
        UPLOAD_FOLDER = upload_dir
        TESTING = True
    return TestConfig


@pytest.fixture(scope="session")
def seeded_template(tmp_path_factory):
    """Build and seed one database file per test session; tests work on copies of it."""
    folder = tmp_path_factory.mktemp("template")
    db_path = str(folder / "template.db")
    app = create_app(make_config(db_path, str(folder / "uploads")))
    with app.app_context():
        seed.reset_database()
        users = seed.seed_users()
        seed.seed_loans(users)
        db.session.commit()
        db.session.remove()
        db.engine.dispose()
    return db_path


@pytest.fixture
def app(seeded_template, tmp_path):
    """A fresh app (own database copy, own upload folder) for one test."""
    db_path = str(tmp_path / "test.db")
    upload_dir = str(tmp_path / "uploads")
    assert os.path.abspath(db_path) != os.path.abspath(LIVE_DB), "tests must never use the live database"
    assert os.path.abspath(upload_dir) != os.path.abspath(LIVE_UPLOADS), "tests must never use the live uploads folder"
    shutil.copy(seeded_template, db_path)
    flask_app = create_app(make_config(db_path, upload_dir))
    assert flask_app.config["SQLALCHEMY_DATABASE_URI"].endswith("test.db")
    yield flask_app
    with flask_app.app_context():
        db.session.remove()
        db.engine.dispose()  # release the file so pytest can delete the temporary folder on Windows


@pytest.fixture
def anon(app):
    """A visitor who is not logged in."""
    return support.new_client(app)


@pytest.fixture
def login(app):
    """login("aman@example.com") returns a new client that is logged in.

    It puts the user id into the session the way Flask-Login does, which is much faster than hashing a password
    for every test. The real login route (password check, messages, redirects) is tested in test_auth.py.
    """
    def _login(email, password=None):
        client = support.new_client(app)
        with app.app_context():
            user_id = User.query.filter_by(email=email).one().id
        with client.session_transaction() as session:
            session["_user_id"] = str(user_id)
            session["_fresh"] = True
        return client
    return _login


@pytest.fixture
def login_with_password(app):
    """Like login, but through the real POST /login with the password (used where the password check matters)."""
    def _login(email, password=None):
        client = support.new_client(app)
        response = support.post(client, "/login", {"email": email, "password": password or support.PASSWORDS[email]})
        assert response.status_code == 302, f"login of {email} failed"
        return client
    return _login


@pytest.fixture
def admin(login):
    return login("admin@microloan.com")


@pytest.fixture
def priya(login):
    """Officer 1 (holds LN-0006, Under Review)."""
    return login("officer1@microloan.com")


@pytest.fixture
def rahul(login):
    """Officer 2 (holds LN-0002 Repaying and LN-0005 Approved)."""
    return login("officer2@microloan.com")


@pytest.fixture
def aman(login):
    """Borrower with the Repaying loan LN-0002 (installment 4 overdue)."""
    return login("aman@example.com")


@pytest.fixture
def sneha(login):
    """Borrower with LN-0001 (Closed) and LN-0006 (Under Review)."""
    return login("sneha@example.com")


@pytest.fixture
def newbie(app, login):
    """A borrower without any loan (income 80,000), logged in."""
    from app.services import loan_service
    with app.app_context():
        user, errors = loan_service.create_user(
            {"name": "New Borrower", "email": "newbie@example.com", "phone": "9000000099", "monthly_income": "80000"},
            "Passw0rd1", "borrower")
        assert user is not None, errors
    return login("newbie@example.com", "Passw0rd1")


def in_app(app, function):
    """Run `function()` inside an application context and return its result."""
    with app.app_context():
        return function()


@pytest.fixture
def state(app):
    """state(loan_id) -> (status, officer name or None, officer_id) read from the database."""
    def _state(loan_id):
        with app.app_context():
            loan = db.session.get(Loan, loan_id)
            return loan.status, (loan.officer.name if loan.officer else None), loan.officer_id
    return _state


@pytest.fixture
def user_id(app):
    """user_id("aman@example.com") -> database id."""
    def _id(email):
        with app.app_context():
            return User.query.filter_by(email=email).one().id
    return _id


@pytest.fixture
def give_loan(app):
    """give_loan("newbie@example.com", "Approved") adds a loan in that status for the borrower and returns its id."""
    from datetime import datetime
    from app.services.emi import calculate_emi

    def _give(email, status, amount=10000, tenure=6, **fields):
        with app.app_context():
            borrower = User.query.filter_by(email=email).one()
            loan = Loan(borrower_id=borrower.id, amount=amount, tenure_months=tenure, interest_rate=12.0,
                        emi_amount=calculate_emi(amount, 12.0, tenure), purpose="Test loan", status=status,
                        applied_on=datetime.now(), **fields)
            db.session.add(loan)
            db.session.commit()
            return loan.id
    return _give


@pytest.fixture
def borrower_with_income(app, login):
    """borrower_with_income(income) creates a borrower without a loan and returns (client, user id)."""
    from app.services import loan_service
    counter = {"n": 0}

    def _make(income):
        counter["n"] += 1
        email = f"income{counter['n']}@example.com"
        with app.app_context():
            user, errors = loan_service.create_user(
                {"name": "Income Test", "email": email, "phone": "9000000088", "monthly_income": str(income)}, "Passw0rd1", "borrower")
            assert user is not None, errors
            return login(email), user.id
    return _make
