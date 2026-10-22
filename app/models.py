"""Database models: User, Loan, Repayment, Document, LoanSetting (CLAUDE.md §5)."""
from datetime import date, datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app import db, login_manager

# A borrower with a loan in any of these states cannot apply again (§7 rule 3)
ACTIVE_STATUSES = ("Applied", "Under Review", "Approved", "Disbursed", "Repaying")


class User(UserMixin, db.Model):
    """A person who uses the system: borrower, officer or admin."""

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(10))
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="borrower")
    monthly_income = db.Column(db.Float, nullable=True)
    is_active = db.Column(db.Boolean, default=True)  # Flask-Login refuses inactive users
    created_at = db.Column(db.DateTime, default=datetime.now)

    # A borrower has many loans; an officer reviews many loans
    loans = db.relationship("Loan", foreign_keys="Loan.borrower_id", backref="borrower", lazy=True)
    reviewed_loans = db.relationship("Loan", foreign_keys="Loan.officer_id", backref="officer", lazy=True)

    def set_password(self, password):
        """Store a salted hash of the password, never the password itself."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Return True if the password matches the stored hash."""
        return check_password_hash(self.password_hash, password)

    def has_active_loan(self):
        """Return True if this borrower has a loan that is not finished yet."""
        return any(loan.status in ACTIVE_STATUSES for loan in self.loans)


class Loan(db.Model):
    """One loan application and its life from Applied to a final state."""

    id = db.Column(db.Integer, primary_key=True)
    borrower_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    officer_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    amount = db.Column(db.Float, nullable=False)
    tenure_months = db.Column(db.Integer, nullable=False)
    interest_rate = db.Column(db.Float, nullable=False)  # copied from settings at apply time
    emi_amount = db.Column(db.Float, nullable=False)
    purpose = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="Applied")
    remarks = db.Column(db.String(300), nullable=True)
    applied_on = db.Column(db.DateTime, default=datetime.now)
    reviewed_on = db.Column(db.DateTime, nullable=True)
    disbursed_on = db.Column(db.Date, nullable=True)
    closed_on = db.Column(db.Date, nullable=True)

    repayments = db.relationship(
        "Repayment", backref="loan", order_by="Repayment.installment_no",
        cascade="all, delete-orphan", lazy=True,
    )
    # uselist=False: one document per application
    document = db.relationship("Document", backref="loan", uselist=False, cascade="all, delete-orphan")

    def total_payable(self):
        """Total the borrower pays back: EMI x number of months."""
        return round(self.emi_amount * self.tenure_months, 2)

    def amount_paid(self):
        """Sum of all paid installments."""
        return round(sum(r.amount for r in self.repayments if r.status == "Paid"), 2)

    def outstanding(self):
        """Sum of installments still pending (0 before disbursal)."""
        return round(sum(r.amount for r in self.repayments if r.status == "Pending"), 2)

    def next_due_installment(self):
        """Return the earliest Pending installment, or None."""
        for repayment in self.repayments:  # already ordered by installment_no
            if repayment.status == "Pending":
                return repayment
        return None

    def display_id(self):
        """Loan ID shown to users, e.g. LN-0001."""
        return f"LN-{self.id:04d}"


class Repayment(db.Model):
    """One EMI installment of a disbursed loan."""

    id = db.Column(db.Integer, primary_key=True)
    loan_id = db.Column(db.Integer, db.ForeignKey("loan.id"), nullable=False)
    installment_no = db.Column(db.Integer, nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="Pending")
    paid_on = db.Column(db.Date, nullable=True)

    def is_overdue(self):
        """Overdue = still Pending and the due date has passed (computed, not stored)."""
        return self.status == "Pending" and self.due_date < date.today()


class Document(db.Model):
    """The supporting file uploaded with a loan application."""

    id = db.Column(db.Integer, primary_key=True)
    loan_id = db.Column(db.Integer, db.ForeignKey("loan.id"), nullable=False)
    original_name = db.Column(db.String(200), nullable=False)
    stored_name = db.Column(db.String(200), nullable=False)  # uuid + extension, inside uploads/
    uploaded_on = db.Column(db.DateTime, default=datetime.now)


class LoanSetting(db.Model):
    """Loan limits set by the admin. There is only one row (id = 1)."""

    id = db.Column(db.Integer, primary_key=True)
    interest_rate = db.Column(db.Float, nullable=False, default=12.0)  # % per year
    min_amount = db.Column(db.Float, nullable=False, default=5000)
    max_amount = db.Column(db.Float, nullable=False, default=100000)
    min_tenure = db.Column(db.Integer, nullable=False, default=3)  # months
    max_tenure = db.Column(db.Integer, nullable=False, default=24)
    max_emi_to_income = db.Column(db.Float, nullable=False, default=50)  # % of monthly income
    updated_at = db.Column(db.DateTime, default=datetime.now)


@login_manager.user_loader
def load_user(user_id):
    """Tell Flask-Login how to find the logged-in user from the session."""
    return db.session.get(User, int(user_id))
