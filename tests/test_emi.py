"""EMI maths: formula, rounding, affordability, month ends, schedule totals (R5, R7, NFR-13)."""
from datetime import date
from types import SimpleNamespace

import pytest

from app.services.emi import add_months, build_schedule, calculate_emi, max_affordable_amount


@pytest.mark.parametrize("principal, rate, months, expected", [
    (50000, 12, 12, 4442.44),    # the demo-script example
    (12000, 0, 12, 1000.00),     # rate 0 gives principal / months
    (30000, 12, 6, 5176.45),     # seeded loan LN-0002
    (25000, 12, 9, 2918.51),     # seeded loan LN-0006
    (100000, 12, 24, 4707.35),
    (5000, 12, 3, 1700.11),
    (60000, 14, 12, 5387.23),
])
def test_known_emi_values(principal, rate, months, expected):
    assert calculate_emi(principal, rate, months) == expected


@pytest.mark.parametrize("rate", [0, 12, 14, 36])
@pytest.mark.parametrize("months", [3, 6, 12, 24])
def test_loan_is_repaid_by_the_emi(rate, months):
    """Independent check: paying the EMI every month on a reducing balance leaves (almost) nothing."""
    principal = 50000
    emi = calculate_emi(principal, rate, months)
    balance = principal
    for _ in range(months):
        balance = balance * (1 + rate / 1200) - emi
    assert abs(balance) < 0.5  # only the rounding of the EMI to 2 decimals is left


def test_emi_is_rounded_to_two_decimals():
    assert calculate_emi(12345, 13.5, 7) == round(calculate_emi(12345, 13.5, 7), 2)


@pytest.mark.parametrize("max_emi, rate, months", [(15000, 12, 12), (4442.44, 12, 12), (9000, 14, 24), (3000, 0, 10)])
def test_max_affordable_amount_stays_within_the_emi_limit(max_emi, rate, months):
    amount = max_affordable_amount(max_emi, rate, months)
    assert calculate_emi(amount, rate, months) <= max_emi + 0.01
    assert calculate_emi(amount + 1, rate, months) > calculate_emi(amount, rate, months)  # and it is the largest whole rupee


def test_max_affordable_for_the_demo_emi_is_about_50000():
    assert 49990 <= max_affordable_amount(4442.44, 12, 12) <= 50000


@pytest.mark.parametrize("start, months, expected", [
    (date(2026, 1, 31), 1, date(2026, 2, 28)),    # 31 Jan + 1 month: no 31 Feb
    (date(2024, 1, 31), 1, date(2024, 2, 29)),    # leap year
    (date(2026, 3, 31), 1, date(2026, 4, 30)),
    (date(2026, 12, 31), 2, date(2027, 2, 28)),   # year rollover
    (date(2026, 8, 31), 6, date(2027, 2, 28)),
    (date(2026, 10, 22), 12, date(2027, 10, 22)),
    (date(2026, 10, 22), 0, date(2026, 10, 22)),
    (date(2026, 11, 30), 3, date(2027, 2, 28)),
    (date(2026, 5, 15), 24, date(2028, 5, 15)),
])
def test_add_months_is_month_end_safe(start, months, expected):
    assert add_months(start, months) == expected


@pytest.mark.parametrize("rate", [0, 12, 14])
@pytest.mark.parametrize("months", list(range(3, 25)))
@pytest.mark.parametrize("amount", [5000, 33333, 100000])
def test_schedule_adds_up_to_exactly_emi_times_n(amount, months, rate):
    """No paisa drift (NFR-13): the installments add up to exactly EMI x n."""
    loan = SimpleNamespace(emi_amount=calculate_emi(amount, rate, months), tenure_months=months)
    rows = build_schedule(loan, date(2026, 1, 31))
    assert len(rows) == months
    assert round(sum(r["amount"] for r in rows), 2) == round(loan.emi_amount * months, 2)


def test_schedule_rows_are_numbered_and_dated_by_month():
    loan = SimpleNamespace(emi_amount=1000.0, tenure_months=4)
    rows = build_schedule(loan, date(2026, 1, 31))
    assert [r["installment_no"] for r in rows] == [1, 2, 3, 4]
    assert [r["due_date"] for r in rows] == [date(2026, 2, 28), date(2026, 3, 31), date(2026, 4, 30), date(2026, 5, 31)]


def test_only_the_last_installment_is_adjusted():
    loan = SimpleNamespace(emi_amount=calculate_emi(50000, 12, 12), tenure_months=12)
    rows = build_schedule(loan, date(2026, 1, 1))
    assert all(r["amount"] == loan.emi_amount for r in rows[:-1])
    assert abs(rows[-1]["amount"] - loan.emi_amount) < 0.2  # the adjustment is a few paise at most


def test_demo_script_numbers():
    """CLAUDE.md section 13: 50,000 for 12 months at 12 % gives 4,442.44 and a total of 53,309.28."""
    emi = calculate_emi(50000, 12, 12)
    assert emi == 4442.44
    assert round(emi * 12, 2) == 53309.28
