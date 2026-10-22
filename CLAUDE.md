# Micro-Loan Management System — Project Blueprint

> Software Engineering course project (NMIMS Hyderabad, B.Tech CS & Data Science).
> This file is the single source of truth for the code AND the design documents.
> If code and this file disagree, ask before changing either.

---

## 1. What we are building

A web application where **borrowers** apply for small loans, **loan officers** review,
approve and disburse them, and **admins** manage users, loan settings and reports.
Repayments are tracked through an auto-generated EMI schedule. Payments are **simulated**
(a "Pay" button), no real money or payment gateway.

### Goals (in priority order)
1. Works end to end in a live demo (apply → review → approve → disburse → repay → close).
2. Code is simple enough for a 2nd-year student to explain line by line in a viva.
3. Code matches the design diagrams (classes, states, flows) exactly.
4. Looks clean and consistent (Bootstrap), not fancy.

### In scope
- Borrower self-registration, login/logout for all roles
- Loan application with one supporting document upload
- Officer review workflow with remarks
- EMI calculation and repayment schedule
- Simulated repayments, overdue detection, auto-closing of loans
- Admin: user management, officer creation, loan settings, reports with charts
- Seed data for demo

### Out of scope (do NOT build)
- Real payments, KYC APIs, credit bureau checks, SMS/email sending
- Password reset by email, OTP, 2FA
- REST API / mobile app / React frontend
- Deployment to the cloud (local run is enough)
- Partial payments, prepayment, loan restructuring, multiple currencies

---

## 2. Tech stack (keep exactly this)

| Layer | Choice |
|---|---|
| Language | Python 3.13 (Windows, PowerShell) |
| Web framework | Flask 3.x with Blueprints |
| Database | SQLite (single file `instance/microloan.db`) via Flask-SQLAlchemy |
| Auth | Flask-Login + `werkzeug.security` password hashing |
| Templates | Jinja2 |
| UI | Bootstrap 5 + Bootstrap Icons (CDN) |
| Charts | Chart.js (CDN), admin reports only |
| Forms | Plain HTML forms + server-side validation (no Flask-WTF), CSRF via a simple session token helper |

`requirements.txt`:
```
Flask>=3.0
Flask-SQLAlchemy>=3.1
Flask-Login>=0.6.3
python-dotenv>=1.0
```

No other libraries without asking first.

For development only, `requirements-dev.txt` adds `pytest` (the test suite in `tests/`); it is not part of `requirements.txt`.

---

## 3. Folder structure

```
micro-loan-system/
├── CLAUDE.md
├── README.md                 # how to install, run, seed, demo logins
├── requirements.txt
├── requirements-dev.txt       # development only: adds pytest
├── pytest.ini
├── tests/                    # pytest suite (temporary database, never the live one)
├── docs/                     # SE documents: SRS, diagrams, CRC cards, wireframes, prototype
├── .gitignore                # venv/, instance/, __pycache__/, uploads/, .env
├── .env.example              # SECRET_KEY=change-me
├── run.py                    # entry point: python run.py
├── seed.py                   # resets DB and loads demo data
├── config.py                 # Config class (SECRET_KEY, DB URI, UPLOAD_FOLDER, MAX_CONTENT_LENGTH)
├── app/
│   ├── __init__.py           # create_app(), register blueprints, init db + login manager
│   ├── models.py             # User, Loan, Repayment, Document, LoanSetting
│   ├── services/
│   │   ├── emi.py            # calculate_emi(), build_schedule()
│   │   └── loan_service.py   # state transitions + business rules (ONE place for rules)
│   ├── utils/
│   │   ├── decorators.py     # @role_required("officer")
│   │   └── validators.py     # form validation helpers
│   ├── routes/
│   │   ├── main.py           # landing, about
│   │   ├── auth.py           # register, login, logout
│   │   ├── borrower.py
│   │   ├── officer.py
│   │   └── admin.py
│   ├── templates/
│   │   ├── base.html         # navbar changes by role, flash messages, footer
│   │   ├── main/  auth/  borrower/  officer/  admin/  errors/
│   └── static/
│       ├── css/style.css
│       └── js/main.js        # small helpers only (e.g., live EMI preview)
├── uploads/                  # loan documents (NOT inside static, served via protected route)
└── instance/                 # SQLite DB lives here (auto-created)
```

Routes must stay thin: validate input → call a service function → render/redirect.
All business rules and status changes live in `services/loan_service.py`.

---

## 4. Users and roles

| Role | How the account is created | Main job |
|---|---|---|
| **Borrower** | Self-registers on the site | Apply for loans, track status, repay |
| **Loan Officer** | Created by Admin only | Review, approve/reject, disburse |
| **Admin** | Created by `seed.py` only | Manage users, settings, view reports |

- Public registration always creates a **borrower**. Nobody can pick their own role.
- Deactivated users (`is_active = False`) cannot log in.
- After login, each role is redirected to its own dashboard.
- Accessing another role's page → 403 page.

### Permission matrix

| Action | Borrower | Officer | Admin |
|---|:-:|:-:|:-:|
| Register / login / logout | ✅ | login only | login only |
| Apply for loan | ✅ | ❌ | ❌ |
| Cancel own loan (only while *Applied*) | ✅ | ❌ | ❌ |
| View own loans, schedule, pay EMI | ✅ | ❌ | ❌ |
| View all applications | ❌ | ✅ | ✅ (read-only) |
| Pick up application for review | ❌ | ✅ | ❌ |
| Approve / reject (with remarks) | ❌ | ✅ (own reviews) | ❌ |
| Disburse approved loan | ❌ | ✅ (own reviews) | ❌ |
| Reassign application (Under Review / Approved) to another active officer | ❌ | ❌ | ✅ |
| View uploaded document | owner | ✅ | ✅ |
| Create officer, activate/deactivate users | ❌ | ❌ | ✅ |
| Change loan settings | ❌ | ❌ | ✅ |
| View reports | ❌ | ❌ | ✅ |

---

## 5. Data model (5 tables)

Use these exact names; the class diagram and CRC cards are drawn from them.

### `User`
| Field | Type | Notes |
|---|---|---|
| id | int PK | |
| name | str(100) | required |
| email | str(120) | unique, lowercase, required |
| phone | str(10) | 10 digits |
| password_hash | str(256) | never store plain password |
| role | str(20) | `borrower` / `officer` / `admin` |
| monthly_income | float, nullable | required for borrowers |
| is_active | bool | default True |
| created_at | datetime | default now |

Methods: `set_password()`, `check_password()`, `has_active_loan()`.
Relationships: borrower → many `Loan` (as borrower), officer → many `Loan` (as reviewer).

### `Loan`
| Field | Type | Notes |
|---|---|---|
| id | int PK | shown to users as `LN-0001` |
| borrower_id | FK User | |
| officer_id | FK User, nullable | set when an officer picks it up; an admin can change it (reassignment) |
| amount | float | principal in ₹ |
| tenure_months | int | |
| interest_rate | float | annual %, **copied from settings at apply time** |
| emi_amount | float | calculated at apply time, rounded to 2 decimals |
| purpose | str(200) | |
| status | str(20) | see state machine |
| remarks | str(300), nullable | officer's reason (required on reject) |
| applied_on | datetime | |
| reviewed_on | datetime, nullable | approve/reject time |
| disbursed_on | date, nullable | |
| closed_on | date, nullable | |

Methods: `total_payable()`, `amount_paid()`, `outstanding()`, `next_due_installment()`, `display_id()`.

### `Repayment` (one row per EMI installment)
| Field | Type | Notes |
|---|---|---|
| id | int PK | |
| loan_id | FK Loan | |
| installment_no | int | 1..n |
| due_date | date | disbursed_on + installment_no months |
| amount | float | EMI (last one adjusted for rounding) |
| status | str(20) | `Pending` / `Paid` |
| paid_on | date, nullable | |

Method: `is_overdue()` → status == Pending AND due_date < today (computed, not stored).

### `Document`
| Field | Type | Notes |
|---|---|---|
| id | int PK | |
| loan_id | FK Loan | |
| original_name | str(200) | |
| stored_name | str(200) | uuid + extension, saved in `uploads/` |
| uploaded_on | datetime | |

### `LoanSetting` (single row, id = 1)
| Field | Default |
|---|---|
| interest_rate | 12.0 (% per year) |
| min_amount | 5,000 |
| max_amount | 1,00,000 |
| min_tenure | 3 months |
| max_tenure | 24 months |
| max_emi_to_income | 50 (%) |
| updated_at | datetime |

---

## 6. Loan lifecycle (state machine)

```
                 borrower cancels
   ┌──────────┐ ───────────────────► Cancelled
   │ Applied  │
   └────┬─────┘
        │ officer picks up
        ▼
   ┌──────────────┐  officer rejects (remarks required)
   │ Under Review │ ─────────────────────────────────► Rejected
   └────┬─────────┘
        │ officer approves
        ▼
   ┌──────────┐
   │ Approved │
   └────┬─────┘
        │ officer disburses → EMI schedule generated
        ▼
   ┌───────────┐
   │ Disbursed │
   └────┬──────┘
        │ first installment paid
        ▼
   ┌───────────┐
   │ Repaying  │
   └────┬──────┘
        │ last installment paid
        ▼
      Closed
```

Final states: **Cancelled, Rejected, Closed**.

### Transition table (enforce in `loan_service.py`, reject anything else)

| From | To | Who | Extra rule |
|---|---|---|---|
| Applied | Cancelled | owning borrower | — |
| Applied | Under Review | any officer | sets `officer_id` |
| Under Review | Approved | assigned officer | sets `reviewed_on` |
| Under Review | Rejected | assigned officer | remarks required, sets `reviewed_on` |
| Approved | Disbursed | assigned officer | sets `disbursed_on`, builds schedule |
| Disbursed | Repaying | system | on first payment |
| Repaying | Closed | system | when all installments Paid, sets `closed_on` |

Implement as a dict `ALLOWED_TRANSITIONS` and one function `change_status(loan, new_status, actor)`
that checks the table and raises a clear error otherwise.

**Reassignment is not a transition.** An admin can hand a loan that is *Under Review* or *Approved*
to a different active officer with `reassign_loan(loan, new_officer, admin)`. Only `officer_id` changes;
the status stays the same, so the table above is untouched. It is refused for every other status, for
the officer who already holds the loan, and for inactive or non-officer accounts. When an admin
deactivates an officer who still holds such loans, the page warns how many need reassigning.

---

## 7. Business rules

1. **Amount** must be between `min_amount` and `max_amount`, with at most 2 decimal places
   (the same limit applies to the minimum and maximum amount in the loan settings).
2. **Tenure** must be between `min_tenure` and `max_tenure` (whole months).
3. **One active loan at a time.** A borrower with any loan in Applied / Under Review /
   Approved / Disbursed / Repaying cannot apply again.
4. **Affordability:** EMI must be ≤ `max_emi_to_income`% of the borrower's monthly income.
   If not, block the application and show the max affordable amount.
5. **EMI formula** (reducing balance):
   `EMI = P × r × (1 + r)^n / ((1 + r)^n − 1)` where `r = annual_rate / 12 / 100`, `n = tenure`.
   If rate is 0, `EMI = P / n`. Round to 2 decimals; adjust the last installment so the total
   equals `EMI × n` exactly (no paisa drift).
6. **Interest rate is locked** at apply time (settings changes affect only new loans).
7. **Schedule** is generated only at disbursal: installment i due on `disbursed_on + i months`
   (if the day doesn't exist, use the last day of that month).
8. **Payments in order:** only the earliest Pending installment can be paid.
9. **Overdue** = Pending and past due date. Shown with a red badge. No late fee (out of scope).
10. **Documents:** one file per application, PDF/JPG/PNG only, max 2 MB, renamed with uuid.
    The first bytes of the file must match its type (`%PDF`, PNG signature, JPEG signature),
    so a text file renamed to `.pdf` is rejected.
11. **Officer ownership:** once an officer picks up an application, only that officer can
    approve, reject or disburse it. The only way to change the owner is an **admin
    reassignment** (see the note under the transition table); the new officer then owns it.

---

## 8. Pages and routes

| # | Page | Route | Method | Role |
|---|---|---|---|---|
| 1 | Landing page | `/` | GET | public |
| 2 | Register (borrower) | `/register` | GET/POST | public |
| 3 | Login | `/login` | GET/POST | public |
| 4 | Logout (small form in the navbar, CSRF token) | `/logout` | POST | logged in |
| 5 | Borrower dashboard | `/borrower/dashboard` | GET | borrower |
| 6 | Apply for loan (live EMI preview) | `/borrower/apply` | GET/POST | borrower |
| 7 | My loans | `/borrower/loans` | GET | borrower |
| 8 | Loan details + EMI schedule | `/borrower/loans/<id>` | GET | borrower (owner) |
| 9 | Pay installment | `/borrower/loans/<id>/pay` | POST | borrower (owner) |
| 10 | Cancel application | `/borrower/loans/<id>/cancel` | POST | borrower (owner) |
| 11 | Officer dashboard | `/officer/dashboard` | GET | officer |
| 12 | Applications list (filter by status) | `/officer/applications` | GET | officer |
| 13 | Application detail | `/officer/applications/<id>` | GET | officer |
| 14 | Pick up / approve / reject / disburse | `/officer/applications/<id>/<action>` | POST | officer |
| 14a | Reassign application to another active officer (status unchanged) | `/officer/applications/<id>/reassign` | POST | admin |
| 15 | Admin dashboard | `/admin/dashboard` | GET | admin |
| 16 | Manage users | `/admin/users` | GET | admin |
| 17 | Create officer | `/admin/users/new-officer` | GET/POST | admin |
| 18 | Activate/deactivate user | `/admin/users/<id>/toggle` | POST | admin |
| 19 | Loan settings | `/admin/settings` | GET/POST | admin |
| 20 | Reports | `/admin/reports` | GET | admin |
| 21 | View document | `/documents/<id>` | GET | owner / officer / admin |
| 22 | Error pages | 403, 404, 500 | — | — |

Every state-changing action is a **POST** (never a GET link), including logout.
Row 14a keeps its letter so the page numbers used elsewhere (wireframes, §14) stay the same.

### Dashboard contents
- **Borrower:** active loan card (status badge, amount, EMI, next due date, outstanding),
  "Apply for loan" button (disabled if an active loan exists), recent payments.
- **Officer:** counts (new applications, under my review, approved awaiting disbursal),
  table of my pending work.
- **Admin:** totals (users, loans by status, ₹ disbursed, ₹ collected, ₹ outstanding,
  overdue installments) and links to reports.

### Reports page (admin)
- Pie chart: loans by status
- Bar chart: amount disbursed per month (last 6 months)
- Table: overdue installments (borrower, loan, due date, amount)

---

## 9. UI guidelines

- One `base.html` with a navbar whose links depend on role; flash messages under the navbar.
- Status badge colors (use everywhere, same mapping):
  Applied = secondary, Under Review = info, Approved = primary, Rejected = danger,
  Cancelled = dark, Disbursed = warning, Repaying = warning, Closed = success, Overdue = danger.
- Money formatted in Indian style: `₹1,00,000.00` (write a Jinja filter `inr`).
- Dates shown as `22 Oct 2026`.
- Every form shows field-level errors and keeps entered values on error.
- Confirm dialogs (`confirm()`) before cancel, reject, disburse, pay, reassign.
- Mobile-friendly via Bootstrap grid; tables wrapped in `.table-responsive`.
- Empty states: friendly message instead of an empty table.

### 9a. Visual theme (yellow and blue)

Still Bootstrap 5 with no new libraries; the look lives in `static/css/style.css` (design tokens at the top)
and the shared pieces in `templates/macros.html`. The status badge colour mapping above does not change.

- **Rule of thumb:** blue is the voice (navigation, headings, links, tables), yellow is the finger (the ONE
  next action on a screen). About 60% neutral, 30% blue, 10% yellow.
- **Tokens:** primary blue `#0B3FA0`, navy `#081B44`, yellow `#FFC629` (always with navy text, never white),
  canvas `#F5F7FB`, muted text `#55627D`. Fonts: system stack only (no web-font download).
- **One enabled yellow button per page** (`btn-primary`). Approve/Reject keep green/red because the colour is the
  meaning. Secondary actions are blue outline (`btn-outline-primary`).
- **Layout (bank-style):** thin utility strip, white header with the current page underlined in yellow, breadcrumbs
  on inner pages, cards with 16px radius, summary tiles on dashboards, multi-column footer on the landing page.
- **Laws of UX applied** (lawsofux.com): Von Restorff (rare yellow), Hick's (at most 5 menu items per role),
  Fitts's (buttons at least 44px tall, actions next to what they act on), Jakob's (familiar banking layout),
  Common Region / Proximity (facts grouped in bordered cards), Miller's / Chunking (short cards, Indian digit
  grouping), Goal-Gradient (installment progress bar with a yellow tip), Zeigarnik (loan step tracker shows the
  steps still ahead), Peak-End (success banner on a fully repaid loan), Doherty (instant EMI preview, busy state on
  submit), Tesler (the system does the maths), Aesthetic-Usability (one token set).
- **Accessibility:** text pairs meet WCAG 4.5:1, focus is a yellow halo, icons are `aria-hidden`, tables and charts
  have a text alternative, `prefers-reduced-motion` is respected.
- **Phones:** the step tracker runs top to bottom and each schedule row becomes a two-line card so Pay is always
  visible.
- **Charts:** pie colours are stepped apart (checked with a palette validator); the pie needs a legend with counts
  and a "View as table" fallback.

---

## 10. Non-functional requirements (what the code must respect)

| ID | Category | Requirement |
|---|---|---|
| NFR1 | Security | Passwords hashed (werkzeug, pbkdf2/scrypt); never logged or displayed |
| NFR2 | Security | Role checks on every protected route via `@role_required` |
| NFR3 | Security | Users can only see their own loans/documents (ownership check) |
| NFR4 | Security | CSRF token on every POST form; SECRET_KEY from `.env` |
| NFR5 | Security | Uploads restricted by type and size; files not publicly reachable |
| NFR6 | Performance | Pages load in < 2 s locally with seed data |
| NFR7 | Usability | Any core task reachable in ≤ 3 clicks from the dashboard |
| NFR8 | Reliability | Invalid state transitions are impossible (central transition table) |
| NFR9 | Data integrity | DB changes for one action committed together (rollback on error) |
| NFR10 | Maintainability | Business logic in services, not in routes or templates |
| NFR11 | Portability | Runs on Windows/Mac/Linux with only Python + `pip install -r requirements.txt` |
| NFR12 | Accuracy | EMI totals match the formula to the paisa |

---

## 11. Seed data (`python seed.py`)

Drops and recreates all tables, then creates:

| Role | Name | Email | Password |
|---|---|---|---|
| Admin | Admin User | admin@microloan.com | Admin@123 |
| Officer | Priya Sharma | officer1@microloan.com | Officer@123 |
| Officer | Rahul Verma | officer2@microloan.com | Officer@123 |
| Borrower | Aman Gupta | aman@example.com | Borrower@123 |
| Borrower | Sneha Iyer | sneha@example.com | Borrower@123 |
| Borrower | Rohan Das | rohan@example.com | Borrower@123 |
| Borrower | Kavya Reddy | kavya@example.com | Borrower@123 |

Plus loans that cover **every status** (one Applied, one Under Review, one Approved,
one Repaying with 1 overdue installment, one Closed, one Rejected, one Cancelled across
different borrowers, respecting the one-active-loan rule), and the default `LoanSetting` row.
These are demo values; put them in README too.

---

## 12. Build phases (one at a time, commit after each)

| Phase | Deliverable | Done when… |
|---|---|---|
| 1. Skeleton | venv, requirements, config, app factory, models, base template, landing page, README | `python run.py` shows landing page; DB file created |
| 2. Auth | register (borrower), login, logout, role redirect, `@role_required`, 403/404 pages | each seeded role lands on its own dashboard; cross-role URL gives 403 |
| 3. Seed | `seed.py` with users + settings (loans added later in phase 7) | can log in as all roles |
| 4. Apply | apply form with live EMI preview (JS), all rules from §7, document upload, My Loans, cancel | rules 1–4 and 10 block bad applications with clear messages |
| 5. Officer | list/filter, detail, pick up, approve, reject (remarks), disburse → schedule | transitions follow §6 exactly; schedule rows correct |
| 6. Repay | schedule view, pay next installment, overdue badges, auto Repaying/Closed | paying all installments closes the loan |
| 7. Admin | users, create officer, toggle active, settings, reports with Chart.js; finish seed loans | charts show seeded data; settings affect new loans only |
| 8. Polish | validation, flash messages, empty states, `inr` filter, consistent badges, README | full demo script below runs with no errors |

---

## 13. Demo script (must work end to end)

1. Register a new borrower → apply for ₹50,000 / 12 months → see EMI ≈ ₹4,442.44 at 12%.
2. Try applying again → blocked (active loan exists).
3. Log in as officer → pick up → approve → disburse → 12 installments generated.
4. Log in as borrower → pay installment 1 → status becomes Repaying.
5. Log in as admin → change interest rate to 14% → reports reflect the new loan.
6. Show the seeded Repaying loan with an overdue installment and the Closed loan.

---

## 14. How code maps to the SE documents (keep consistent)

| Document / Diagram | Source in this project |
|---|---|
| Functional requirements | §1 scope, §4 permissions, §7 rules, §8 pages |
| Non-functional requirements | §10 |
| Use case diagram | Actors = Borrower, Loan Officer, Admin (+ System for overdue/closing); use cases = rows of §4 matrix |
| Activity diagram | "Apply for loan" flow with decision nodes from §7 rules 1–4 |
| Swimlane diagram | Full loan lifecycle with four lanes Borrower, System, Loan Officer, Admin (apply → validate → review → approve/reject → admin reassignment → disburse → schedule → repay → close), plus a smaller "Pay an installment" swimlane (Borrower, System) |
| Class diagram | §5 models + `EMICalculator`/`LoanService` service classes, with relationships |
| CRC cards | User, Loan, Repayment, Document, LoanSetting, LoanService, EMICalculator |
| DFD Level 0 | System ↔ Borrower, Officer, Admin |
| DFD Level 1 | Processes: 1 Manage Accounts, 2 Apply Loan, 3 Review Loan, 4 Disburse & Schedule, 5 Process Repayment, 6 Generate Reports; stores: Users, Loans, Repayments, Documents, Settings |
| State diagram | §6 Loan lifecycle (optionally Repayment: Pending → Paid, with Overdue as a condition) |
| Sequence diagram | Apply for loan: Borrower → UI → borrower route → LoanService → EMICalculator → DB |
| Wireframes / prototype | One per page in §8 (at minimum pages 1, 2, 3, 5, 6, 8, 11, 13, 15, 19, 20) |

If a feature is added or changed in code, list the diagrams that must be updated.

The finished documents are in `docs/` (SRS, diagrams as PNG and SVG, CRC cards, wireframes, prototype screenshots);
`docs/README.md` maps each file to the assignment items.

---

## 15. Coding conventions for Claude Code

- Work **one phase at a time**; don't start the next phase unless asked.
- Before writing code for a phase, give a short plan (files to create/change).
- Keep functions short; add a one-line docstring to every function and a brief comment
  on any non-obvious line. Student must be able to explain everything.
- Use `snake_case` for Python, `kebab-case` for CSS classes, templates named after routes.
- No hard-coded secrets; read from `.env` with a safe dev default.
- Use `db.session.commit()` once per action inside try/except with rollback.
- After each phase: list what changed, how to run/test it, and a suggested git commit message.
- Windows PowerShell commands:
  - create venv: `python -m venv venv`
  - activate: `.\venv\Scripts\Activate.ps1`
    (if blocked: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`)
  - install: `pip install -r requirements.txt`
  - seed: `python seed.py`   run: `python run.py` → http://127.0.0.1:5000
- Never delete the database or uploads without saying so first (seed.py is the only reset).
- Don't add libraries, features, or pages outside this blueprint without asking.
