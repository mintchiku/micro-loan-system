"""Business rules and status changes. Routes call these functions; rules live only here."""
from app import db
from app.models import User


def create_user(values, password, role):
    """Create and save a new borrower (self-registration) or officer (created by admin)."""
    user = User(
        name=values["name"],
        email=values["email"],
        phone=values["phone"],
        role=role,
        # only borrowers have an income; it is needed for the affordability rule
        monthly_income=float(values["monthly_income"]) if role == "borrower" else None,
    )
    user.set_password(password)
    try:
        db.session.add(user)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return user
