"""EMI maths: monthly instalment, affordability and repayment schedule (CLAUDE.md §7 rules 5 and 7)."""
import calendar
import math
from datetime import date


def calculate_emi(principal, annual_rate, months):
    """Return the monthly EMI on a reducing balance, rounded to 2 decimals."""
    r = annual_rate / 12 / 100  # monthly interest rate as a fraction (12 % -> 0.01)
    if r == 0:
        return round(principal / months, 2)
    growth = (1 + r) ** months
    return round(principal * r * growth / (growth - 1), 2)


def max_affordable_amount(max_emi, annual_rate, months):
    """Largest principal (whole rupees) whose EMI stays within max_emi: the EMI formula solved for P."""
    r = annual_rate / 12 / 100
    if r == 0:
        principal = max_emi * months
    else:
        growth = (1 + r) ** months
        principal = max_emi * (growth - 1) / (r * growth)
    return math.floor(principal)  # round down so the EMI never goes over the limit


def add_months(start, months):
    """Same day `months` later; if that day does not exist, use the last day of that month."""
    month_index = start.month - 1 + months  # months counted from January of the start year
    year = start.year + month_index // 12
    month = month_index % 12 + 1
    last_day = calendar.monthrange(year, month)[1]  # e.g. 28 or 29 for February
    return date(year, month, min(start.day, last_day))


def build_schedule(loan, disbursed_on):
    """Return the installments (number, due date, amount) for a loan disbursed on `disbursed_on`."""
    n = loan.tenure_months
    total = round(loan.emi_amount * n, 2)  # what the borrower must pay in total
    schedule = []
    for i in range(1, n + 1):
        if i < n:
            amount = loan.emi_amount
        else:
            # last installment absorbs any rounding drift so the total is exactly EMI x n
            amount = round(total - loan.emi_amount * (n - 1), 2)
        schedule.append({"installment_no": i, "due_date": add_months(disbursed_on, i), "amount": amount})
    return schedule


if __name__ == "__main__":
    # Self-test: python app/services/emi.py
    from types import SimpleNamespace

    emi = calculate_emi(50000, 12, 12)
    print(f"EMI for Rs 50,000 at 12% for 12 months: {emi} (expected about 4442.44)")
    print(f"EMI at 0% (Rs 12,000 / 12 months): {calculate_emi(12000, 0, 12)} (expected 1000.0)")
    print(f"Max affordable with EMI Rs 4442.44: {max_affordable_amount(4442.44, 12, 12)} (expected about 50000)")
    print(f"31 Jan 2026 + 1 month: {add_months(date(2026, 1, 31), 1)} (expected 2026-02-28)")
    rows = build_schedule(SimpleNamespace(emi_amount=emi, tenure_months=12), date(2026, 1, 31))
    print(f"Schedule: {len(rows)} rows, first due {rows[0]['due_date']}, last due {rows[-1]['due_date']}")
    print(f"Schedule total {round(sum(r['amount'] for r in rows), 2)} = EMI x 12 = {round(emi * 12, 2)}")
