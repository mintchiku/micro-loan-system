"""Reset the database and load demo data. Run: python seed.py"""
from datetime import date, datetime, timedelta

from app import create_app, db
from app.models import Loan, LoanSetting, Repayment, User
from app.services.emi import add_months, build_schedule, calculate_emi

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


def make_loan(borrower, officer, amount, tenure, purpose, status, applied_on, **dates):
    """Build one demo Loan (EMI at 12 %); optional reviewed_on, remarks, disbursed_on, closed_on."""
    return Loan(
        borrower=borrower, officer=officer, amount=amount, tenure_months=tenure, interest_rate=12.0,
        emi_amount=calculate_emi(amount, 12.0, tenure), purpose=purpose, status=status,
        applied_on=applied_on, **dates,
    )


def add_schedule(loan, paid_count):
    """Create the installments of a disbursed loan; the first `paid_count` are paid on their due date."""
    for row in build_schedule(loan, loan.disbursed_on):
        paid = row["installment_no"] <= paid_count
        loan.repayments.append(Repayment(
            installment_no=row["installment_no"], due_date=row["due_date"], amount=row["amount"],
            status="Paid" if paid else "Pending", paid_on=row["due_date"] if paid else None,
        ))


def seed_loans(users):
    """Create demo loans covering every status; no borrower has more than one active loan (rule 3)."""
    now = datetime.now()
    today = date.today()
    aman, sneha = users["aman@example.com"], users["sneha@example.com"]
    rohan, kavya = users["rohan@example.com"], users["kavya@example.com"]
    priya, rahul = users["officer1@microloan.com"], users["officer2@microloan.com"]

    # Closed: Sneha, 4 months, disbursed 5 months ago, every installment paid on time
    closed_disbursed = add_months(today, -5)
    closed = make_loan(sneha, priya, 20000, 4, "Buy sewing machine", "Closed",
                       now - timedelta(days=158), reviewed_on=now - timedelta(days=156),
                       remarks="Documents verified.", disbursed_on=closed_disbursed,
                       closed_on=add_months(closed_disbursed, 4))
    add_schedule(closed, paid_count=4)

    # Repaying: Aman, 6 months, disbursed 4 months + 10 days ago: 3 paid, installment 4 is overdue
    repaying_disbursed = add_months(today, -4) - timedelta(days=10)
    repaying = make_loan(aman, rahul, 30000, 6, "Stock for grocery shop", "Repaying",
                         now - timedelta(days=138), reviewed_on=now - timedelta(days=136),
                         remarks="Approved after income check.", disbursed_on=repaying_disbursed)
    add_schedule(repaying, paid_count=3)

    # Rejected and Cancelled: older loans that are finished, so the borrowers could apply again
    rejected = make_loan(rohan, priya, 40000, 12, "Two-wheeler purchase", "Rejected",
                         now - timedelta(days=40), reviewed_on=now - timedelta(days=38),
                         remarks="Supporting document is not readable. Please apply again with a clear copy.")
    cancelled = make_loan(kavya, None, 15000, 6, "Laptop for studies", "Cancelled",
                          now - timedelta(days=30))

    # One loan in each of the three open review stages (one per borrower)
    approved = make_loan(kavya, rahul, 60000, 12, "Expand tailoring business", "Approved",
                         now - timedelta(days=3), reviewed_on=now - timedelta(days=1),
                         remarks="Income verified. Ready for disbursal.")
    under_review = make_loan(sneha, priya, 25000, 9, "Medical expenses", "Under Review",
                             now - timedelta(days=2))
    applied = make_loan(rohan, None, 35000, 12, "Buy a second-hand auto-rickshaw", "Applied",
                        now - timedelta(hours=5))

    loans = [closed, repaying, rejected, cancelled, approved, under_review, applied]
    for loan in sorted(loans, key=lambda item: item.applied_on):  # oldest first, so LN-0001 is the oldest
        db.session.add(loan)
    return loans


def print_summary(loans):
    """Print a table of the accounts and the demo loans that were created."""
    print(f"\n{'Role':<10}{'Name':<15}{'Email':<26}Password")
    print("-" * 64)
    for name, email, password, role, _phone, _income in DEMO_USERS:
        print(f"{role:<10}{name:<15}{email:<26}{password}")
    print(f"\n{'Loan':<9}{'Borrower':<13}{'Amount':>9}  {'Months':<7}Status")
    print("-" * 50)
    for loan in sorted(loans, key=lambda item: item.id):
        print(f"{loan.display_id():<9}{loan.borrower.name.split()[0]:<13}{loan.amount:>9,.0f}  "
              f"{loan.tenure_months:<7}{loan.status}")


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
            loans = seed_loans(users)
            db.session.commit()  # everything is saved together
        except Exception:
            db.session.rollback()
            raise
        print("Database reset and demo data loaded.")
        print_summary(loans)  # inside the app context: it reads the loans from the database


if __name__ == "__main__":
    main()
