# Micro-Loan Management System

A Flask web application where **borrowers** apply for small loans, **loan officers** review, approve and
disburse them, and **admins** manage users, loan settings and reports. Repayments follow an auto-generated
EMI schedule. Payments are **simulated** (a "Pay" button); no real money is involved.

Software Engineering course project, NMIMS Hyderabad (B.Tech CS & Data Science).

## Features

- Borrower self-registration; login / logout for all three roles; each role lands on its own dashboard
- Loan application with live EMI preview and one supporting document (PDF / JPG / PNG, max 2 MB; the
  file's content must match its type). Money amounts allow at most 2 decimal places
- Business rules: amount and tenure limits, one active loan at a time, EMI-to-income affordability check,
  interest rate locked when the loan is applied for
- Officer workflow: pick up, approve, reject (remarks required), disburse; only the officer who picked up
  a loan can act on it. An admin can reassign an Under Review or Approved application to another
  active officer (the status does not change)
- EMI schedule generated at disbursal; pay installments in order; overdue detection; loan closes automatically
- Admin: user list with filter and search, activate / deactivate, create officers, loan settings,
  dashboard totals, reports with Chart.js (pie chart, monthly bar chart, overdue table)
- Security: hashed passwords, role checks on every protected route, ownership checks, CSRF token on every
  POST form (logout is a POST form too), `SameSite=Lax` and `HttpOnly` session cookie, protected document
  downloads
- Demo data with a loan in every status (`seed.py`)

## Tech stack

| Layer | Choice |
|---|---|
| Language | Python 3.13 |
| Web framework | Flask 3.x with Blueprints |
| Database | SQLite (`instance/microloan.db`) via Flask-SQLAlchemy |
| Auth | Flask-Login + `werkzeug.security` password hashing |
| Templates | Jinja2 |
| UI | Bootstrap 5 + Bootstrap Icons (CDN) |
| Charts | Chart.js (CDN), admin reports only |
| Forms | Plain HTML forms, server-side validation, session-token CSRF helper |

## Setup (Windows PowerShell)

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1          # if blocked: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
pip install -r requirements.txt
copy .env.example .env                # then put your own SECRET_KEY in .env
```

## Seed demo data

```powershell
python seed.py      # asks y/n, then RESETS the database and loads demo users and loans
```

## Run

```powershell
python run.py
```

Open http://127.0.0.1:5000. The SQLite database is created automatically at `instance/microloan.db`.
The CDN links (Bootstrap, Chart.js) need an internet connection.

## Demo logins

| Role | Name | Email | Password |
|---|---|---|---|
| Admin | Admin User | admin@microloan.com | Admin@123 |
| Officer | Priya Sharma | officer1@microloan.com | Officer@123 |
| Officer | Rahul Verma | officer2@microloan.com | Officer@123 |
| Borrower | Aman Gupta | aman@example.com | Borrower@123 |
| Borrower | Sneha Iyer | sneha@example.com | Borrower@123 |
| Borrower | Rohan Das | rohan@example.com | Borrower@123 |
| Borrower | Kavya Reddy | kavya@example.com | Borrower@123 |

### Seeded loans (dates are relative to the day you run `seed.py`)

| Loan | Borrower | Amount | Months | Status |
|---|---|---|---|---|
| LN-0001 | Sneha | ₹20,000 | 4 | Closed (all paid) |
| LN-0002 | Aman | ₹30,000 | 6 | Repaying (3 paid, installment 4 overdue) |
| LN-0003 | Rohan | ₹40,000 | 12 | Rejected |
| LN-0004 | Kavya | ₹15,000 | 6 | Cancelled |
| LN-0005 | Kavya | ₹60,000 | 12 | Approved (officer2, ready to disburse) |
| LN-0006 | Sneha | ₹25,000 | 9 | Under Review (officer1) |
| LN-0007 | Rohan | ₹35,000 | 12 | Applied |

The *Disbursed* status is not seeded because each borrower may have only one active loan; you create it
yourself in the demo script (step 3).

## Demo script

1. Register a new borrower (use a monthly income of at least ₹10,000) and apply for **₹50,000 / 12 months**
   with any PDF, JPG or PNG file. The EMI shown is about **₹4,442.44** at 12 %.
2. Try applying again: it is blocked because an active loan exists.
3. Log in as **officer1@microloan.com**: open the new application, **Pick up**, **Approve**, **Disburse**.
   Twelve installments are generated.
4. Log in as the borrower: **Pay** installment 1. The status becomes *Repaying*.
5. Log in as **admin@microloan.com**: change the interest rate to 14 % under *Settings*; *Reports* now include
   the new loan. Only new applications use 14 %.
6. Show the seeded **Repaying** loan with an overdue installment (log in as aman@example.com) and the **Closed**
   loan (sneha@example.com).

## Design

A yellow-and-blue theme on Bootstrap 5, inspired by the layout patterns of modern bank websites (thin utility strip,
clean header, hero with a primary and a secondary button, summary tiles, multi-column footer) and built on the
[Laws of UX](https://lawsofux.com/). Blue carries structure; yellow marks the one next action on each screen.
The tokens are at the top of `app/static/css/style.css`, and the full rules are in CLAUDE.md section 9a.

## Folder structure

```
micro-loan-system/
├── CLAUDE.md                 # project blueprint (single source of truth)
├── PROGRESS.md               # build log: plan, tests and decisions per phase
├── README.md
├── requirements.txt
├── .env.example              # SECRET_KEY=change-me
├── run.py                    # entry point: python run.py
├── seed.py                   # resets the DB and loads demo data
├── config.py                 # SECRET_KEY, database URI, upload folder, size limit
├── app/
│   ├── __init__.py           # create_app(): blueprints, filters, CSRF check, error pages
│   ├── models.py             # User, Loan, Repayment, Document, LoanSetting
│   ├── services/
│   │   ├── emi.py            # calculate_emi(), build_schedule(), add_months()
│   │   └── loan_service.py   # state transitions and ALL business rules
│   ├── utils/
│   │   ├── decorators.py     # @role_required(...)
│   │   ├── validators.py     # form validation and CSRF token helpers
│   │   └── formatters.py     # Jinja filters: inr (₹1,00,000.00) and date (22 Oct 2026)
│   ├── routes/               # main, auth, borrower, officer, admin (thin: validate, call service, render)
│   ├── templates/            # base.html, macros.html, and one folder per area
│   └── static/               # css/style.css, js/main.js (live EMI preview)
├── uploads/                  # loan documents (not in static/, served by a protected route)
└── instance/                 # SQLite database (auto-created)
```
