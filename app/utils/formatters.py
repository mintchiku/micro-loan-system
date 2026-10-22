"""Jinja filters for money and dates (CLAUDE.md §9)."""


def inr(value):
    """Format a number in Indian style with the rupee sign, e.g. 100000 -> ₹1,00,000.00."""
    if value is None:
        return "-"
    sign = "-" if value < 0 else ""
    rupees, paise = f"{abs(value):.2f}".split(".")
    last_three = rupees[-3:]  # the last 3 digits form one group
    rest = rupees[:-3]
    groups = []
    while len(rest) > 2:  # the remaining digits are grouped in pairs: 1,00,000
        groups.insert(0, rest[-2:])
        rest = rest[:-2]
    if rest:
        groups.insert(0, rest)
    return f"{sign}₹{','.join(groups + [last_three])}.{paise}"


def format_date(value):
    """Show a date or datetime like 22 Oct 2026."""
    if value is None:
        return "-"
    return value.strftime("%d %b %Y")
