"""Dashboard totals and reports: money totals, loans by status, shares that add up to 100.0, monthly bars, overdue table (FR-48 to FR-51)."""
import random
import re
from datetime import date

import pytest

from app import db
from app.models import Loan, Repayment
from app.services import loan_service
from app.services.emi import add_months
from app.services.loan_service import STATUS_ORDER, percent_shares
from support import post, text


# ---------- percent_shares (Part 1b, FR-49) ----------

def tenths(shares):
    return [round(s * 10) for s in shares]


@pytest.mark.parametrize("values, expected", [
    ([1, 1, 1], [33.4, 33.3, 33.3]),        # 33.3 + 33.3 + 33.3 = 99.9, so the first largest row takes the 0.1
    ([2, 1], [66.7, 33.3]),
    ([5], [100.0]),
    ([1, 0], [100.0, 0.0]),
    ([0, 0, 0], [0.0, 0.0, 0.0]),
    ([], []),
    ([3, 1], [75.0, 25.0]),
])
def test_percent_shares_examples(values, expected):
    assert percent_shares(values) == expected


def test_the_seeded_shape_adds_up_to_exactly_100():
    shares = percent_shares([1, 1, 1, 0, 1, 1, 1, 1])  # one loan in seven statuses, none Disbursed
    assert sum(tenths(shares)) == 1000
    assert set(shares) == {0.0, 14.2, 14.3} and shares[3] == 0.0
    assert shares.count(14.2) + shares.count(14.3) == 7


def test_percent_shares_always_add_up_to_100_for_random_lists():
    rng = random.Random(2026)
    for _ in range(500):
        values = [rng.choice([0, 0, 1, 2, 3, 7, 11, 25]) for _ in range(rng.randint(1, 10))]
        shares = percent_shares(values)
        if sum(values) == 0:
            assert shares == [0.0] * len(values)
            continue
        assert sum(tenths(shares)) == 1000, (values, shares)
        assert all(round(s, 1) == s and s >= 0 for s in shares), (values, shares)
        largest = values.index(max(values))
        for i, (s, v) in enumerate(zip(shares, values)):
            true_share = 100 * v / sum(values)
            allowed = 0.05 * len(values) + 0.05 if i == largest else 0.05 + 1e-9  # the largest row takes the rounding remainder
            assert abs(s - true_share) <= allowed, (values, shares, i)


def test_the_largest_row_absorbs_the_rounding():
    values = [1, 1, 1, 5, 1, 1, 1]
    shares = percent_shares(values)
    plain = [round(v * 100 / sum(values), 1) for v in values]
    assert [s for i, s in enumerate(shares) if i != 3] == [s for i, s in enumerate(plain) if i != 3]  # only the largest row is adjusted
    assert sum(tenths(shares)) == 1000


# ---------- totals (FR-48) ----------

def test_admin_totals_match_the_database(app):
    with app.app_context():
        totals = loan_service.admin_totals()
        loans, rows = Loan.query.all(), Repayment.query.all()
        assert totals["total_users"] == 7 and totals["users_by_role"] == {"borrower": 4, "officer": 2, "admin": 1}
        assert totals["total_loans"] == 7
        assert totals["loans_by_status"] == {"Applied": 1, "Under Review": 1, "Approved": 1, "Disbursed": 0, "Repaying": 1,
                                             "Closed": 1, "Rejected": 1, "Cancelled": 1}
        assert list(totals["loans_by_status"]) == STATUS_ORDER
        assert totals["disbursed"] == round(sum(l.amount for l in loans if l.disbursed_on), 2) == 50000.0
        assert totals["collected"] == round(sum(r.amount for r in rows if r.status == "Paid"), 2)
        assert totals["outstanding"] == round(sum(r.amount for r in rows if r.status == "Pending"), 2)
        assert totals["overdue_count"] == 1


def test_the_dashboard_shows_the_totals(admin):
    html = text(admin.get("/admin/dashboard"))
    assert "₹50,000.00" in html and "Loans by status (7 total)" in html
    assert "4 borrowers" in html and "2 officers" in html and "1 admin" in html


def test_totals_move_with_a_payment(app, aman):
    with app.app_context():
        before = loan_service.admin_totals()
        row = Repayment.query.filter_by(loan_id=2, installment_no=4).one()
        row_id, amount = row.id, row.amount
    post(aman, "/borrower/loans/2/pay", {"repayment_id": row_id})
    with app.app_context():
        after = loan_service.admin_totals()
    assert round(after["collected"] - before["collected"], 2) == amount
    assert round(before["outstanding"] - after["outstanding"], 2) == amount
    assert after["overdue_count"] == 0 and before["overdue_count"] == 1


# ---------- the reports page (FR-49, FR-50, FR-51) ----------

def test_the_pie_data_and_the_table_agree(admin):
    html = text(admin.get("/admin/reports"))
    assert '"values": [1, 1, 1, 0, 1, 1, 1, 1]' in html, "the chart itself still shows the counts"
    table = html[html.index("<summary", html.index("Loans by status")):]
    table = table[:table.index("</table>")]
    shares = [float(x) for x in re.findall(r"(\d+\.\d)%</td>", table)]
    assert len(shares) == 8
    assert sum(round(s * 10) for s in shares) == 1000, "the shares in the table add up to exactly 100.0 %"
    assert shares == percent_shares([1, 1, 1, 0, 1, 1, 1, 1])


def test_the_tooltip_uses_the_same_shares_as_the_table(admin):
    html = text(admin.get("/admin/reports"))
    assert "statusData.shares[ctx.dataIndex].toFixed(1)" in html and '"shares": [' in html


def test_the_bar_chart_has_six_months_and_the_disbursed_amounts(app):
    with app.app_context():
        chart = loan_service.disbursed_per_month()
        first = date.today().replace(day=1)
        assert chart["labels"] == [add_months(first, -i).strftime("%b %Y") for i in range(5, -1, -1)]
        assert chart["labels"][-1] == date.today().strftime("%b %Y")
        assert len(chart["values"]) == 6 and round(sum(chart["values"]), 2) == 50000.0


def test_a_loan_disbursed_this_month_lands_in_the_last_bar(app, rahul):
    post(rahul, "/officer/applications/5/disburse")  # 60,000 disbursed today
    with app.app_context():
        chart = loan_service.disbursed_per_month()
        assert chart["values"][-1] == 60000.0


def test_the_overdue_table_lists_the_overdue_installment(app, admin):
    html = text(admin.get("/admin/reports"))
    assert "Aman Gupta" in html and "LN-0002" in html and "4 of 6" in html and "Overdue" in html
    with app.app_context():
        rows = loan_service.overdue_installments()
        assert [(r.loan_id, r.installment_no) for r in rows] == [(2, 4)]


def test_the_overdue_table_is_oldest_first(app):
    with app.app_context():
        for number in (5, 6):  # make installments 5 and 6 overdue too, with older dates
            row = Repayment.query.filter_by(loan_id=2, installment_no=number).one()
            row.due_date = date(2025, 1, number)
        db.session.commit()
        assert [(r.installment_no) for r in loan_service.overdue_installments()] == [5, 6, 4]


def test_no_overdue_installments_gives_the_empty_state(app, admin, aman):
    with app.app_context():
        ids = [r.id for r in Repayment.query.filter_by(loan_id=2, installment_no=4)]
    post(aman, "/borrower/loans/2/pay", {"repayment_id": ids[0]})
    assert "No overdue installments." in text(admin.get("/admin/reports"))


def test_only_the_admin_sees_the_reports(priya, aman, anon):
    assert priya.get("/admin/reports").status_code == 403
    assert aman.get("/admin/reports").status_code == 403
    assert anon.get("/admin/reports").status_code == 302
