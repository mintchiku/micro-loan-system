"""Reset the database and load demo data. Run: python seed.py"""
from app import create_app, db
from app.models import LoanSetting, User

# (name, email, password, role, phone, monthly income)
DEMO_USERS = [
    ("Admin User", "admin@microloan.com", "Admin@123", "admin", "9000000001", None),
    ("Priya Sharma", "officer1@microloan.com", "Officer@123", "officer", "9000000002", None),
    ("Rahul Verma", "officer2@microloan.com", "Officer@123", "officer", "9000000003", None),
    ("Aman Gupta", "aman@example.com", "Borrower@123", "borrower", "9876543210", 45000),
    ("Sneha Iyer", "sneha@example.com", "Borrower@123", "borrower", "9876543211", 60000),
    ("Rohan Das", "rohan@example.com", "Borrower@123", "borrower", "9876543212", 30000),
    ("Kavya Reddy", "kavya@example.com", "Borrower@123", "borrower", "9876543213", 80000),
]


def confirm_reset():
    """Ask in the terminal before deleting data; return True only for 'y'."""
    answer = input("This DELETES all data in the database and loads demo data. Continue? (y/n): ")
    return answer.strip().lower() == "y"


def reset_database():
    """Drop and recreate all tables, then add the default LoanSetting row."""
    db.drop_all()
    db.create_all()
    db.session.add(LoanSetting(id=1))  # model defaults: 12 %, ₹5,000–₹1,00,000, 3–24 months, 50 %


def seed_users():
    """Create the demo accounts and return them in a dict keyed by email."""
    users = {}
    for name, email, password, role, phone, income in DEMO_USERS:
        user = User(name=name, email=email, phone=phone, role=role, monthly_income=income)
        user.set_password(password)  # stored as a hash
        db.session.add(user)
        users[email] = user
    db.session.flush()  # assigns ids without committing yet
    return users


# ---------------------------------------------------------------------------
# PHASE 7: demo loans covering every status will be created here.
# ---------------------------------------------------------------------------
def seed_loans(users):
    """Create demo loans (filled in during Phase 7; does nothing for now)."""
    return []


def print_summary():
    """Print a table of the accounts that were created."""
    print(f"\n{'Role':<10}{'Name':<15}{'Email':<26}Password")
    print("-" * 64)
    for name, email, password, role, _phone, _income in DEMO_USERS:
        print(f"{role:<10}{name:<15}{email:<26}{password}")


def main():
    """Reset the database and load all demo data in one transaction."""
    if not confirm_reset():
        print("Cancelled. Nothing was changed.")
        return
    app = create_app()
    with app.app_context():
        try:
            reset_database()
            users = seed_users()
            seed_loans(users)
            db.session.commit()  # everything is saved together
        except Exception:
            db.session.rollback()
            raise
    print("Database reset and demo data loaded.")
    print_summary()


if __name__ == "__main__":
    main()
