# MicroLoan: Project Handoff Gist (A to Z)

> **Purpose.** Everything a fresh Claude thread needs to understand, run, log in to, inspect and continue this project
> without re-discovering anything. Written 23 Oct 2026. For depth on any topic, the long reference is
> `WEBSITE_COMPLETE_TECHNICAL_DOCUMENTATION.md` (same folder); the design rules and the owner's working rules are in
> `CLAUDE.md`; the build log is `PROGRESS.md`.
>
> **Security note.** The passwords below are **demo-only** accounts created by `seed.py` (they are also in `README.md` and
> `seed.py`). If this file is ever committed to a public repository, remove the credentials section first.

---

## 1. One-paragraph summary

**MicroLoan** is a Flask web app (Python 3.13, SQLite, Bootstrap 5) built as a Software Engineering course project
(NMIMS Hyderabad, B.Tech CS & Data Science). **Borrowers** self-register, apply for a small loan (₹5,000 to ₹1,00,000 by
default, 3 to 24 months) with one document, and repay it in monthly installments. **Loan officers** pick up, approve or
reject, and disburse applications (disbursal auto-creates the EMI schedule). **Admins** manage users, create officers,
edit loan limits and the interest rate, and view totals and charts. Payments are **simulated** (a Pay button). It is
server-rendered (no JSON API, no JS framework). It has been built in 8 phases, audited, and then re-skinned with a
**yellow-and-blue theme** (the redesign is **uncommitted**).

---

## 2. Access details: how to open it and log in

### 2.1 The "link"

| Item | Value |
|---|---|
| URL | **http://127.0.0.1:5000** |
| Reachable from | **Only the owner's own Windows PC**, while the server is running. `127.0.0.1` means "this computer"; it is **not** a public link and a cloud-hosted Claude thread cannot open it |
| Server status when this was written | Running (HTTP 200 on `/login`), started in the background by Claude Code with `venv\Scripts\python.exe run.py` (Flask dev server, `debug=True`, auto-reloads on code changes). It stops when that session or the terminal ends |
| Start it yourself | `cd C:\Users\utsav\Desktop\Projects\micro-loan-system` then `.\venv\Scripts\Activate.ps1` then `python run.py` |
| Needs internet | Yes, for Bootstrap, Bootstrap Icons and Chart.js (CDN). Without internet the pages are unstyled |
| Project folder | `C:\Users\utsav\Desktop\Projects\micro-loan-system` |

A Claude thread can inspect the site only if it runs **on that machine** (for example Claude Code in VS Code on the same PC)
or has a browser tool connected to that PC. Otherwise it can only read the source files and this document.

### 2.2 Demo accounts (all active)

| Role | Name | Email (login id) | Password | Lands on |
|---|---|---|---|---|
| **Admin** | Admin User | `admin@microloan.com` | `Admin@123` | `/admin/dashboard` |
| **Loan officer 1** | Priya Sharma | `officer1@microloan.com` | `Officer@123` | `/officer/dashboard` |
| **Loan officer 2** | Rahul Verma | `officer2@microloan.com` | `Officer@123` | `/officer/dashboard` |
| **Borrower** | Aman Gupta | `aman@example.com` | `Borrower@123` | `/borrower/dashboard` |
| **Borrower** | Sneha Iyer | `sneha@example.com` | `Borrower@123` | `/borrower/dashboard` |
| **Borrower** | Rohan Das | `rohan@example.com` | `Borrower@123` | `/borrower/dashboard` |
| **Borrower** | Kavya Reddy | `kavya@example.com` | `Borrower@123` | `/borrower/dashboard` |

Log in at `/login` (one form for all roles). Borrower incomes: Aman ₹45,000, Sneha ₹60,000, Rohan ₹30,000, Kavya ₹80,000.

### 2.3 What the live demo database contains right now

| Fact | Detail |
|---|---|
| Users | 8: the 7 above plus **one extra borrower** (id 8) that was registered through the website after seeding. **Its password is not known to Claude.** Do not assume it |
| Loans | 8: LN-0001 to LN-0007 (seeded) plus **LN-0008** (that extra borrower's application, ₹60,000, 8 months, status *Applied*, unassigned) |
| Documents | 1 (LN-0008's upload, in `uploads/`). Seeded loans have no document |
| Settings | 12% a year, ₹5,000 to ₹1,00,000, 3 to 24 months, EMI limit 50% of income |

**Seeded loans** (dates are relative to the day `seed.py` was last run):

| Loan | Borrower | Amount | Months | Status | Notes |
|---|---|---|---|---|---|
| LN-0001 | Sneha | ₹20,000 | 4 | **Closed** | all 4 installments paid; officer Priya |
| LN-0002 | Aman | ₹30,000 | 6 | **Repaying** | 3 paid, installment 4 **overdue**; EMI ₹5,176.45; officer Rahul |
| LN-0003 | Rohan | ₹40,000 | 12 | **Rejected** | has remarks; officer Priya |
| LN-0004 | Kavya | ₹15,000 | 6 | **Cancelled** | |
| LN-0005 | Kavya | ₹60,000 | 12 | **Approved** | officer Rahul, ready to disburse |
| LN-0006 | Sneha | ₹25,000 | 9 | **Under Review** | officer Priya |
| LN-0007 | Rohan | ₹35,000 | 12 | **Applied** | unassigned |

A borrower with an **active** loan cannot apply again, and all four seeded borrowers have one (or just closed one), so to
see the **Apply form** use a borrower with no active loan: **Sneha is blocked (LN-0006)**, Aman is blocked (LN-0002), Rohan
(LN-0007) and Kavya (LN-0005) are blocked too. Register a **new borrower** to see the form.

### 2.4 Safe vs. destructive actions

- Viewing pages (GET) is always safe.
- Any POST (apply, pick up, approve, pay, toggle user, change settings) **changes the live demo data**.
- `python seed.py` **deletes everything** (after a y/n prompt) and reloads the 7 users and 7 loans. That would also delete the
  extra borrower and LN-0008. Never run it without asking the owner.
- To experiment safely, use a **temporary database** (recipe in section 12.2).

---

## 3. Tech stack and size

| Layer | Choice (exact) |
|---|---|
| Language | Python 3.13.5 on Windows 11 (PowerShell and Git Bash both available; Node 24 is installed) |
| Web | Flask 3.1.3, Blueprints, Jinja2 3.1.6 |
| Database | SQLite file `instance/microloan.db` via Flask-SQLAlchemy 3.1.1 (SQLAlchemy 2.1.6) |
| Auth | Flask-Login 0.6.3, Werkzeug 3.1.9 password hashing (scrypt) |
| Config | python-dotenv 1.2.4 (`.env` is **absent**; `SECRET_KEY` falls back to the dev default `dev-only-change-me` in `config.py`) |
| UI | Bootstrap 5.3.3 + Bootstrap Icons 1.11.3 (CDN), custom `app/static/css/style.css`, plain JS `app/static/js/main.js` |
| Charts | Chart.js 4.4.4 (CDN), admin reports page only |
| Forms | Plain HTML forms, server-side validation, hand-written CSRF token |

`requirements.txt` has exactly four packages: Flask, Flask-SQLAlchemy, Flask-Login, python-dotenv. **Do not add libraries
without asking** (owner rule).

Size: about 1,400 lines of Python in 18 files, 20 templates (about 1,700 lines), about 400 lines of CSS, about 100 lines of JS.
22 HTTP routes, 5 tables, 3 roles, 8 loan statuses.

---

## 4. Folder structure

```
micro-loan-system/
├── CLAUDE.md                  Blueprint + the owner's rules for Claude (READ FIRST)
├── PROGRESS.md                Build log: plan, checks, decisions per phase (+ redesign entry)
├── README.md                  Setup, demo logins, demo script, folder tree
├── WEBSITE_COMPLETE_TECHNICAL_DOCUMENTATION.md   3281-line reference with 32 diagrams and a 31-slide plan
├── PROJECT_HANDOFF_GIST.md    This file
├── docs/                      SE documents: SRS, diagrams (28 as PNG and SVG), CRC cards, 13 wireframes, 24 prototype screenshots
├── PROMPTS.md                 The phase prompts (git-ignored, not part of the app)
├── requirements.txt  .env.example  .gitignore
├── run.py                     python run.py -> dev server on 127.0.0.1:5000
├── seed.py                    Resets DB + loads demo data (asks y/n)
├── config.py                  SECRET_KEY, DB URI, UPLOAD_FOLDER, MAX_CONTENT_LENGTH = 3 MB
├── app/
│   ├── __init__.py            create_app(), CSRF before_request, 403/404/413/500 handlers, filters
│   ├── models.py              User, Loan, Repayment, Document, LoanSetting
│   ├── routes/                main.py  auth.py  borrower.py  officer.py  admin.py
│   ├── services/              loan_service.py (ALL rules + state machine)  emi.py (maths)
│   ├── utils/                 decorators.py  validators.py  formatters.py
│   ├── templates/             base.html, macros.html, main/ auth/ borrower/ officer/ admin/ errors/
│   └── static/                css/style.css, js/main.js
├── instance/microloan.db      SQLite (git-ignored)      uploads/  (git-ignored)      venv/ (git-ignored)
```

---

## 5. Roles and permissions

| Action | Borrower | Officer | Admin |
|---|:-:|:-:|:-:|
| Register (public, always creates a borrower) / login / logout | yes | login | login |
| Apply for a loan | yes | no | no |
| Cancel own loan (only while *Applied*) | yes | no | no |
| View own loans and schedule, pay installments | yes | no | no |
| View all applications | no | yes | yes (**read-only**) |
| Pick up an application | no | yes (any officer) | no |
| Approve / reject (remarks required) / disburse | no | **only the officer who picked it up** | no |
| View a document | owner only | yes | yes |
| Reassign an application (Under Review / Approved) to another active officer | no | no | yes |
| Create officers, activate/deactivate users, change loan settings, reports | no | no | yes |

Admins are created only by `seed.py`. Wrong role gives a 403 page; another borrower's loan or document gives 404.

---

## 6. Data model (5 tables)

| Table | Key columns | Notes |
|---|---|---|
| `user` | id, name, email (unique, lower-case), phone, password_hash, role, monthly_income, is_active, created_at | one table for all roles |
| `loan` | id (shown `LN-0001`), borrower_id, officer_id (null until pick-up), amount, tenure_months, **interest_rate (copied from settings at apply time)**, emi_amount, purpose, status, remarks, applied_on, reviewed_on, disbursed_on, closed_on | the central table |
| `repayment` | id, loan_id, installment_no, due_date, amount, status (Pending/Paid), paid_on | one row per installment; created at disbursal |
| `document` | id, loan_id, original_name, stored_name (uuid + ext), uploaded_on | one per loan (enforced in code, not by a DB constraint) |
| `loan_setting` | id (always 1), interest_rate 12, min/max_amount 5000/100000, min/max_tenure 3/24, max_emi_to_income 50, updated_at | single global row |

Overdue is **computed** (`Repayment.is_overdue()`: Pending and due date before today), never stored. SQLite foreign keys are not
enforced (no PRAGMA). Money is `Float` rounded to 2 decimals. No migrations: `db.create_all()` at start-up.

---

## 7. Loan lifecycle and business rules

```
Applied --borrower--> Cancelled
Applied --any officer picks up--> Under Review --assigned officer--> Approved --assigned officer--> Disbursed
Under Review --assigned officer, remarks required--> Rejected
Disbursed --first installment paid (system)--> Repaying --last installment paid (system)--> Closed
Final states: Cancelled, Rejected, Closed
```

`ALLOWED_TRANSITIONS` and `change_status(loan, new_status, actor)` in `app/services/loan_service.py` are the **only** way a
status changes. Anything else raises `LoanError` (a clear message shown to the user). Routes never set `loan.status`.

| Rule | Meaning |
|---|---|
| R1/R2 | Amount and tenure (whole months) within the admin's limits |
| R3 | One active loan at a time (Applied, Under Review, Approved, Disbursed, Repaying) |
| R4 | EMI at most 50% of monthly income (admin setting); the error shows the largest affordable amount |
| R5 | EMI = P·r·(1+r)^n / ((1+r)^n − 1), r = rate/12/100 (0% gives P/n), rounded to 2 decimals; the last installment absorbs rounding so the total is exactly EMI x n. Example: ₹50,000, 12 months, 12% gives **₹4,442.44** (total ₹53,309.28) |
| R6 | The interest rate is locked per loan; later setting changes only affect new applications |
| R7 | Schedule is created only at disbursal; installment *i* is due on the disbursal day plus *i* months (month-end safe: 31 Jan + 1 month = 28 Feb) |
| R8 | Only the earliest Pending installment can be paid |
| R9 | Overdue = Pending and past due; red badge; no late fee |
| R10 | One document per application; PDF/JPG/PNG; at most 2 MB; renamed with a uuid; the file's first bytes must match its type; stored in `uploads/`, served only via `/documents/<id>` |
| R11 | After pick-up only the assigned officer can approve, reject or disburse (enforced in `change_status`). An admin can reassign an Under Review / Approved loan to another active officer (`reassign_loan`); the status does not change |

Every service function that writes does **one** `db.session.commit()` inside `try/except` with rollback (disbursal saves the status and
all installments together).

---

## 8. How a request flows (architecture)

Server-rendered monolith: **templates (view) -> routes (thin controllers) -> services (rules) -> models -> SQLite**.

For a POST: browser sends the form + `csrf_token` + signed session cookie -> `check_csrf` (`app/__init__.py`, `before_request`) -> Flask-Login
`load_user` (returns nothing for a deactivated user) -> `@role_required(...)` (login redirect or 403) -> view (ownership check, 404) -> **one**
service function -> commit -> `flash()` -> redirect (Post/Redirect/Get) -> the GET page renders through `base.html`.

Routes **do not return JSON**. Chart data is placed in the page with `|tojson`. The only client-side logic is the live EMI preview, a "busy"
state on submit buttons, and Chart.js.

### 8.1 The 22 routes

| URL | Methods | Access | Notes |
|---|---|---|---|
| `/` | GET | public | landing page; limits and example EMI come from live settings |
| `/register`, `/login` | GET, POST | public | logged-in users are redirected to their dashboard |
| `/logout` | POST | login | CSRF token required; the navbar Logout is a small form (a plain GET gives 405) |
| `/documents/<id>` | GET | borrower (owner), officer, admin | sends the file from `uploads/` |
| `/borrower/dashboard` | GET | borrower | |
| `/borrower/apply` | GET, POST | borrower | form + live EMI preview |
| `/borrower/loans` | GET | borrower | |
| `/borrower/loans/<id>` | GET | borrower (owner) | step tracker, summary, schedule |
| `/borrower/loans/<id>/pay` | POST | borrower (owner) | form field `repayment_id` |
| `/borrower/loans/<id>/cancel` | POST | borrower (owner) | |
| `/officer/dashboard` | GET | officer | |
| `/officer/applications` | GET | officer, admin | filter tabs + search (`?status=&q=`) |
| `/officer/applications/<id>` | GET | officer, admin | admin sees it read-only |
| `/officer/applications/<id>/<action>` | POST | officer | action is `pickup`, `approve`, `reject` or `disburse` |
| `/officer/applications/<id>/reassign` | POST | admin | form field `officer_id`; only Under Review / Approved; status unchanged |
| `/admin/dashboard`, `/admin/users`, `/admin/reports` | GET | admin | users has `?role=&q=` |
| `/admin/users/new-officer` | GET, POST | admin | |
| `/admin/users/<id>/toggle` | POST | admin | cannot deactivate yourself |
| `/admin/settings` | GET, POST | admin | |

---

## 9. The look and feel: the yellow-and-blue theme

The owner asked for a redesign inspired by a bank website's layout, applying the **Laws of UX** (lawsofux.com), with **yellow and blue**
as primary colours, using Claude Design. It is implemented in `app/static/css/style.css` (tokens at the top) and
`app/templates/macros.html`, and documented in `CLAUDE.md` section 9a. **No bank branding is used**; only layout patterns.

### 9.1 The one rule

> **Blue is the voice. Yellow is the finger.** Blue carries structure (navigation, headings, links, tables). Yellow marks the **one**
> next action on a screen. Roughly 60% neutral, 30% blue, 10% yellow.

- **At most one enabled yellow button (`btn-primary`) per page.** Approve (green) and Reject (red outline) keep their own colours because the colour is the meaning.
- Secondary actions are blue outline (`btn-outline-primary`). Yellow text is never used on white; yellow always carries navy text.

### 9.2 Design tokens

| Token | Value | Use |
|---|---|---|
| Blue 700 (primary) | `#0B3FA0` | links, active nav, headings accents, hero/auth backgrounds, progress fill |
| Navy 900 | `#081B44` | footer, utility strip, text on yellow |
| Blue 800 | `#0A2E78` | wordmark, hover |
| Blue 100 / 50 | `#E4ECFB` / `#F2F6FD` | icon tiles, table heads |
| Yellow 500 | `#FFC629` | the next action, current step, focus halo, progress tip |
| Yellow 600 | `#F0AE00` | hover / pressed |
| Yellow 100 | `#FFF1BF` | soft highlights, Disbursed/Repaying badge |
| Ink / Muted | `#0E1A33` / `#55627D` | body / secondary text (6.1:1 on white) |
| Canvas / Border | `#F5F7FB` / `#DCE2EE` | page background / card outline |
| Success / Danger / Info | `#0F7B55` / `#BE2A3E` / `#0A7EA4` | Closed, Approve / Rejected, Overdue / Under Review |

Fonts: **system stack only** (Segoe UI on Windows), no web-font download. Radii 10px (controls), 16px (cards). Buttons at least 44px tall.

### 9.3 Status badges (CLAUDE.md section 9 mapping, unchanged)

Applied = secondary (grey), Under Review = info (cyan), Approved = primary (blue), Disbursed and Repaying = warning (soft yellow),
Closed = success (green), Rejected = danger (red), Cancelled = dark, **Overdue = solid red (the loudest)**, Paid = success, Pending = secondary.
Implemented as soft pills with a dot via CSS on the Bootstrap `text-bg-*` classes; one macro `status_badge(status)`.

### 9.4 Layout and components (bank-style)

- **Utility strip** (navy) above a white **header**: logo mark (yellow square with ₹) + wordmark, role-based menu with a **yellow underline** on the current page, user chip + Logout.
- Menus (max five items, by design): Borrower: Dashboard, Apply for loan, My loans. Officer: Dashboard, Applications. Admin: Dashboard, Users, Applications, Settings, Reports.
- **Landing page:** hero (blue) with headline "Small loans. Clear terms. No surprises.", an **example EMI card computed from the live settings**, facts strip, 3 steps, 4 feature tiles, loan-lifecycle chips, yellow call-to-action band, full footer.
- **Login / Register:** split screen (blue panel with benefits + white form card).
- **Dashboards:** summary tiles, active-loan card with "Next installment", an overdue alert, progress bar with a yellow tip, quick links, recent payments.
- **Loan details:** breadcrumb, **step tracker** (Applied, Under Review, Approved, Disbursed, Repaying, Closed; shorter for Rejected/Cancelled; vertical on phones), officer remarks, fact cards, repayment summary, schedule with the single yellow **Pay** button on the earliest Pending row; a "Loan fully repaid" banner when Closed.
- **Officer review:** facts on the left, **decision card on the right** (Pick up / Approve + Reject / Disburse), affordability meter (EMI vs the income limit), status history timeline.
- **Admin:** stat tiles, users table (tabs + search + activate/deactivate), settings form with a "new applications only" note, **reports** (pie chart by status with a counted legend + "View as table", bar chart of disbursals for 6 months, overdue table).
- Macros in `macros.html`: `csrf_field`, `input_field` (₹ prefix, kept values, field errors), `status_badge`, `breadcrumb`, `empty_state`, `progress_bar`, `loan_stepper`, `schedule_table`. `base.html` offers blocks `title`, `page` (edge-to-edge pages override it), `content`, `scripts`.
- Filters: `inr` (`₹1,00,000.00`), `inr_short` (`₹5,000`), `date` (`22 Oct 2026`). US spelling **"installment"** everywhere.

### 9.5 Laws of UX applied (and where)

Von Restorff (rare yellow), Hick (at most 5 menu items), Fitts (44px targets, actions next to what they act on; Pay inside its row), Jakob (familiar banking layout, breadcrumbs), Common Region and Proximity (bordered fact cards), Miller and Chunking (short cards, Indian digit grouping), Goal-Gradient (progress bar), Zeigarnik (step tracker shows steps still ahead), Peak-End (repaid banner), Doherty (instant EMI preview, busy state on submit), Tesler (the system does the maths), Aesthetic-Usability (one token set).

### 9.6 Accessibility and responsiveness

All 30 text/background pairs reach WCAG 4.5:1; yellow focus halo on inputs; icons `aria-hidden`; charts have text alternatives; `prefers-reduced-motion` respected. On phones: step tracker runs top to bottom; each schedule row becomes a two-line card (the Pay button never leaves the screen); the "No." and "Paid on" columns hide. Pie colours were run through a palette validator (normal-vision rule passes; red/green separation is in the allowed band because the legend and a table view carry identity).

### 9.7 The Claude Design canvas

A private design canvas (the visual spec made before the code): **https://claude.ai/artifact/ReY6dKrjqNxLjpdVUiS2mJ** with 6 boards (Style guide, Home, Sign in, Borrower dashboard, Loan details, Officer review). It is **private to the owner's claude.ai account**; another thread can read it only with the Artifact tool on the same account. It can drift from the code; **the code is the truth**.

---

## 10. Security summary

Passwords: salted scrypt hash. CSRF: random per-session token on every POST form, checked for every POST. Role checks on every protected route plus ownership checks (404) plus the state machine re-check. XSS: Jinja auto-escape (a `<script>` in a field renders as text). SQL: ORM only. Uploads: extension whitelist, 2 MB, uuid name, outside `static/`, protected route. Login ignores `?next=`. **Known gaps:** no rate limiting, no HTTPS, session cookie `SameSite` not set, upload content not scanned, dev server with `debug=True`.

---

## 11. Verification status (be honest about it)

- **Automated tests: yes.** `tests/` holds **1,371 pytest tests in 17 modules** (1,370 pass, 1 is a documented known gap marked as an expected failure; about 65 seconds). Run `pip install -r requirements-dev.txt` then `python -m pytest`. Every test uses a temporary copy of a freshly seeded database and a temporary upload folder, never `instance/microloan.db` or `uploads/`. They cover the EMI maths, all 384 (from, to, actor) status combinations, every route against every role, rules R1 to R11, CSRF on all 11 POST routes, rollback when a commit fails and every fix of the first audit. A mutation check on a copy of the project broke the app in 14 ways and the suite caught all 14. Not tested automatically: the browser JavaScript and the layout (screenshots).
- **Visual check:** 16 pages at 1360px and 4 at 390px were screenshotted with headless Edge and reviewed; two phone bugs were found and fixed (tracker overflow, clipped Pay button).
- The 32 Mermaid diagrams in the technical document were rendered and checked in Mermaid 10.9.3 and 11.4.0 (the 28 diagrams of `docs/` too).
- `python app/services/emi.py` is a small extra self-test of the EMI maths.

### 11.1 Known issues found in the final audit (all six fixed in session 2, Part 2)

1. ~~Amounts with more than 2 decimals are accepted.~~ **Fixed:** apply form and loan settings reject them ("Use at most 2 decimal places.").
2. ~~Uploaded files are checked by extension and size only.~~ **Fixed:** the first bytes must match PDF / PNG / JPEG (`check_document`).
3. ~~A deactivated officer's loans are stuck.~~ **Fixed:** admin reassignment (`reassign_loan`), plus a warning with the count when such an officer is deactivated.
4. ~~Two simultaneous sign-ups with the same email could show the 500 page.~~ **Fixed:** `create_user` catches `IntegrityError` and returns the same form error.
5. ~~Session cookie `SameSite` is not set.~~ **Fixed:** `SESSION_COOKIE_SAMESITE = "Lax"` and `SESSION_COOKIE_HTTPONLY = True` in `config.py`.
6. ~~`GET /logout` changes state.~~ **Fixed:** logout is POST only, with the CSRF token.

---

## 12. How to inspect it (recipes)

### 12.1 With a real browser tool
Open `http://127.0.0.1:5000/login`, sign in with a demo account above, and follow the visual tour: Aman (`/borrower/dashboard`, then
LN-0002 for the overdue installment, tracker and Pay button), Sneha (LN-0001 closed, success banner), officer1 (`/officer/applications/6`),
admin (`/admin/reports` for the charts). Resize to about 390px to see the phone layout.

### 12.2 With the Flask test client (no server needed; use a **temporary** database)

```powershell
cd C:\Users\utsav\Desktop\Projects\micro-loan-system
$env:PYTHONIOENCODING = "utf-8"      # the console cannot print the rupee sign otherwise
@'
import sys, os, tempfile
sys.path.insert(0, ".")
from config import Config
tmp = tempfile.mkdtemp()
class T(Config):
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(tmp, "t.db").replace("\\", "/")
    UPLOAD_FOLDER = os.path.join(tmp, "up")
    TESTING = True
from app import create_app, db
import seed
app = create_app(T)
with app.app_context():
    seed.reset_database(); users = seed.seed_users(); seed.seed_loans(users); db.session.commit()
c = app.test_client()
with c.session_transaction() as s: s["csrf_token"] = "t"          # known CSRF token for POSTs
c.post("/login", data={"email": "aman@example.com", "password": "Borrower@123", "csrf_token": "t"})
html = c.get("/borrower/loans/2").data.decode()
print(c.get("/borrower/dashboard").status_code, "Overdue" in html)
'@ | .\venv\Scripts\python.exe -
```

### 12.3 With curl (against the live server; read-only)

```bash
curl -s -c jar.txt http://127.0.0.1:5000/login | grep csrf_token          # the token is in a hidden input
curl -s -b jar.txt -c jar.txt -d "email=aman@example.com&password=Borrower@123&csrf_token=<TOKEN>" http://127.0.0.1:5000/login -i
curl -s -b jar.txt http://127.0.0.1:5000/borrower/dashboard
```

(In Git Bash on Windows prefix commands that contain URL paths with `MSYS_NO_PATHCONV=1` if arguments start with `/`.)

### 12.4 Screenshots
Headless Edge works without extra installs: `"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --headless=new --screenshot=out.png --window-size=1360,1400 http://127.0.0.1:5000/`
(public pages only; logged-in pages need cookies, so drive Edge over its DevTools port with a short Node script, or use a browser tool).

---

## 13. Git and repository state

- **9 commits** on `main`, one per phase (`a8e8af6` Phase 1 to `051bbbc` Phase 9). Commit messages end with a `Co-Authored-By` line for the current Claude model.
- **Uncommitted:** 31 modified files = the whole yellow-and-blue redesign (CSS, base/macros/all templates, a few routes/services: `main.index` passes settings and a sample loan, `officer.application_detail` passes settings, `inr_short` filter, new pie colours, `main.js` busy state), **plus** the CLAUDE.md section 9a, README "Design" section and PROGRESS entry. Suggested message: `UI redesign: yellow and blue theme`.
- **Untracked:** `WEBSITE_COMPLETE_TECHNICAL_DOCUMENTATION.md`, `PROJECT_HANDOFF_GIST.md`, and tooling items `.agents/` and `skills-lock.json` (not part of the app, not created by the app code).
- `.gitignore`: `venv/`, `instance/`, `uploads/`, `.env`, `__pycache__/`, `PROMPTS.md`, `.claude/`.
- `.claude/settings.json` registers a Claude Code plugin ("ponytail": a "simplest solution" mode) for this workspace; it is tooling, git-ignored.

---

## 14. The owner's working rules (from `CLAUDE.md` section 15 and this project's history)

1. **Read `CLAUDE.md` first.** It is the single source of truth; if code and it disagree, **ask before changing either**.
2. Work **one phase/task at a time**; give a short plan (files to create or change) before coding; afterwards list what changed, how to run/test, and a suggested commit message.
3. **Do not add libraries, pages, tables or features outside the blueprint without asking.** (The 9a visual theme section was added with the owner's request.)
4. Keep code **simple and commented** so a second-year student can explain it in a viva: short functions, a one-line docstring on every function, `snake_case`, no clever tricks.
5. **Never delete the database or `uploads/`** except through `seed.py`, and say so first.
6. Windows PowerShell commands; Python 3.13; virtual environment `venv`.
7. Use `db.session.commit()` once per action inside try/except with rollback; business rules only in `services/loan_service.py`; routes stay thin.
8. Be **honest in reports**: say what was verified and how, what was not, and mark guesses. The owner values accuracy, a polished satisfying result, and visible proof (screenshots, test counts).
9. Commit or push **only when asked** (a recent session rule). The owner previously asked for per-phase commits during the original build.

---

## 15. Gotchas already learned (save yourself the time)

- **Jinja dict keys vs methods:** `status_chart.values` returns the dict method; use `status_chart["values"]`.
- **Server caches templates when `debug=False`:** the throwaway servers used for screenshots needed a restart after template edits; the real `run.py` (debug) auto-reloads.
- **Seed dates are relative to the run day**, so "overdue" and month labels shift each day; loan ids and statuses do not.
- **Windows console encoding:** set `PYTHONIOENCODING=utf-8` before printing the rupee sign from Python.
- **Git Bash path conversion** rewrites arguments that start with `/`; set `MSYS_NO_PATHCONV=1` for URL arguments.
- **CDN dependency:** pages look unstyled offline; charts need Chart.js.
- **Only one yellow button per page** is a hard design rule: adding a second `btn-primary` breaks it (a UI check script caught two such cases during the redesign).
- **Test-markup coupling:** the old check scripts matched literal markup (for example `display-6`, "Next due"); when changing templates, assert behaviour, not exact HTML.
- `check_csrf` rejects any POST without the session token, so scripts must send `csrf_token`.

---

## 16. Open items and decisions waiting for the owner

1. ~~Which of the six known issues (11.1) to fix.~~ All six are fixed (session 2, Part 2).
2. **Commit** the redesign (31 files) and the two documentation files? (Nothing has been committed since Phase 9.)
3. ~~Move the test scripts into the repo as `tests/` (pytest).~~ Done in session 2, Part 4 (`python -m pytest`).
4. Presentation: use `WEBSITE_COMPLETE_TECHNICAL_DOCUMENTATION.md` (31-slide plan, 32 diagrams, 20 viva questions) to build the PowerPoint; fill in team and guide names (not in the repo).
5. Whether to ever deploy (the blueprint says local only; deployment is out of scope).
6. Decide what to do with the extra demo data (the owner's own borrower account and LN-0008) the next time `seed.py` is run.

---

## 17. Starter message to paste into the new Claude thread

> I'm continuing a Flask project in `C:\Users\utsav\Desktop\Projects\micro-loan-system` (MicroLoan: borrowers apply for small loans,
> officers review/disburse, admins manage settings and reports; yellow-and-blue theme). Please read `PROJECT_HANDOFF_GIST.md` first,
> then `CLAUDE.md` (my rules: one task at a time, plan first, no new libraries/pages without asking, simple commented code, never delete the
> DB except via seed.py, Windows PowerShell). The site runs at http://127.0.0.1:5000 when you start it with `python run.py` from the activated
> `venv`; demo logins are in section 2.2 of the gist. Do not run `seed.py` or submit POST forms against my live data without asking
> (use the temporary-database recipe in section 12.2). The redesign is uncommitted; do not commit unless I ask. Today I want you to: [WRITE YOUR TASK HERE].
