# Build Progress — Micro-Loan Management System

This file logs each phase: the plan, what was built, how it was checked, and any decisions.
`CLAUDE.md` is the blueprint; `PROMPTS.md` has the phase instructions.

| Phase | Status |
|---|---|
| 0. Kickoff | Done |
| 1. Skeleton | Done |
| 2. Auth | Done |
| 3. Seed (users) | Done |
| 4. Apply | Done |
| 5. Officer | Not started |
| 6. Repay | Not started |
| 7. Admin + full seed | Not started |
| 8. Polish | Not started |
| 9. Final audit | Not started |

---

## Phase 0 — Kickoff

`git init` done (branch `main`).

### Blueprint summary
- **Roles:** Borrower (self-registers, applies, repays), Loan Officer (created by admin; picks up,
  approves/rejects, disburses), Admin (created by seed only; users, settings, reports).
- **Tables (5):** `User`, `Loan`, `Repayment` (one row per EMI), `Document` (one per loan),
  `LoanSetting` (single row, id = 1).
- **Loan states:** Applied → Under Review → Approved → Disbursed → Repaying → Closed, with
  Applied → Cancelled and Under Review → Rejected. Final: Cancelled, Rejected, Closed.
- **Transitions** live in one `ALLOWED_TRANSITIONS` table + `change_status(loan, new_status, actor)`
  in `services/loan_service.py`; anything else raises an error.
- **Key rules:** amount and tenure within settings limits; one active loan per borrower;
  EMI ≤ 50 % of monthly income (show max affordable amount); reducing-balance EMI rounded to
  paisa; rate locked at apply time; schedule built only at disbursal (month-end safe);
  pay installments strictly in order; overdue = Pending and past due (computed);
  documents PDF/JPG/PNG ≤ 2 MB renamed with uuid; only the officer who picked a loan can act on it.
- **Security:** hashed passwords, `@role_required` on every protected route, ownership checks,
  CSRF token on every POST, uploads outside `static/` behind a protected route.
- **UI:** Bootstrap 5 + Icons, one `base.html`, fixed badge colours, `inr` filter (₹1,00,000.00),
  dates like `22 Oct 2026`, confirm dialogs on cancel/reject/disburse/pay.
- **Phases:** 1 Skeleton → 2 Auth → 3 Seed users → 4 Apply → 5 Officer → 6 Repay →
  7 Admin + full seed → 8 Polish, then a final audit.

### Questions / contradictions found (and the simple choice taken)
1. **Admin "view all applications (read-only)"** is in the permission matrix (§4) but §8 has no
   admin applications page. → Admin is allowed on the officer list/detail routes
   (`/officer/applications`, `/officer/applications/<id>`) with all action buttons hidden;
   the action POST route stays officer-only.
2. **`main.py` mentions an "about" page** but §8 (the page list) does not. → No about page;
   the landing page has a "How it works" section instead.
3. **Logout is a GET** in §8 while "every state-changing action is a POST". → Follow the §8 table
   (GET), since it is listed explicitly.
4. **Seed data and "every status"**: §11 lists 7 loans (no *Disbursed*). With 4 borrowers and the
   one-active-loan rule, only 4 active loans fit (Applied, Under Review, Approved, Repaying).
   → *Disbursed* is not seeded; it appears in the demo (step 3) right after disbursal.
5. **Rule 5 "adjust the last installment"**: if every EMI is already rounded, EMI × n is exact.
   → Installments 1..n-1 = EMI, last = round(EMI × n − sum of the others, 2), which removes any
   floating-point drift and guarantees the total equals EMI × n.
6. **Document required?** §1 says "loan application with one supporting document upload".
   → The document is required on every new application.
7. **2 MB limit vs. MAX_CONTENT_LENGTH**: Flask's limit applies to the whole request (file + fields).
   → `MAX_CONTENT_LENGTH` = 3 MB as a hard safety cap; the 2 MB file rule is checked in code so
   the user gets a normal field error.
8. **`EMICalculator` / `LoanService` classes** in §14 vs. functions in §3. → Code uses
   module-level functions (`emi.py`, `loan_service.py`); in the class diagram each module is
   drawn as a class with these functions as its methods.
9. **PROMPTS.md** says to keep it out of git. → Added to `.gitignore`. `.claude/` (Claude Code
   plugin settings) is also ignored because it is tooling, not project code.

---

## Phase 1 — Skeleton

### Plan
- `requirements.txt`, `venv/` (Python 3.13), `.gitignore`, `.env.example`
- `config.py` (SECRET_KEY from .env, DB path, UPLOAD_FOLDER, MAX_CONTENT_LENGTH), `run.py`
- `app/__init__.py`: `create_app()`, SQLAlchemy + LoginManager, 5 blueprints, `create_all()`,
  default `LoanSetting` row (id = 1)
- `app/models.py`: User, Loan, Repayment, Document, LoanSetting with all fields/methods from §5
- `app/routes/*.py`: `main` (landing page) + empty `auth`, `borrower`, `officer`, `admin` blueprints
- `templates/base.html`, `templates/main/index.html`, `static/css/style.css`, `README.md`

### Verified
- `python run.py` starts with no errors; `GET /` → 200 with the landing page; CSS served.
- `instance/microloan.db` created with tables `user, loan, repayment, document, loan_setting`
  and the settings row `(12.0, 5000, 100000, 3, 24, 50)`.
- `git status` does not list `venv/` or `instance/`.

### Decisions
- Empty `__init__.py` files mark `app/routes`, `app/services`, `app/utils` as packages.
- Login/Register buttons use plain `/login` and `/register` links until Phase 2 adds the routes.
- `Loan.total_payable()` = EMI × tenure (rule 5); `outstanding()` = sum of Pending installments,
  so it is 0 before disbursal.

---

## Phase 2 — Authentication & roles

### Plan
- `app/utils/validators.py`: CSRF token helpers (`get_csrf_token`, `csrf_token_is_valid`),
  `to_float`/`to_int`, `validate_user_form()` (name, email, unique email, 10-digit phone,
  income > 0, password ≥ 8 with letter + number, confirm match)
- `app/utils/decorators.py`: `@role_required(*roles)` (login → else 403), `dashboard_url(user)`
- `app/services/loan_service.py`: `create_user(values, password, role)` (one commit + rollback)
- `app/routes/auth.py`: `/register` (always borrower, auto-login), `/login` (blocks deactivated
  users), `/logout`
- `app/routes/{borrower,officer,admin}.py`: placeholder `/dashboard` pages
- `app/__init__.py`: global CSRF check on every POST, 403/404/500 handlers, login manager settings
- Templates: `macros.html` (`input_field`, `csrf_field`), `auth/login.html`, `auth/register.html`,
  three dashboards, `errors/403|404|500.html`, role-aware navbar in `base.html`

### Verified (Flask test client, temp DB — 27/27 checks passed)
- Register → redirected to `/borrower/dashboard` showing "Welcome, <name>"; email stored
  lowercase; password stored as a hash; a posted `role=admin` is ignored.
- Wrong password → "Invalid email or password"; duplicate email (any case) rejected; every
  field error shown and entered values kept.
- Borrower → `/admin/dashboard` and `/officer/dashboard` give the 403 page; officer/admin also get
  403 on other roles' dashboards; logged-out `/borrower/dashboard` → redirect to `/login`.
- Officer and admin log in and land on their own dashboards; deactivated user is refused.
- POST without a CSRF token is refused; unknown URL shows the 404 page.
- Live server (`python run.py`): `/`, `/login`, `/register` return 200; no server errors.

### Temporary way to create an officer and an admin (before seed.py exists)
Run in PowerShell from the project folder with the venv active:
```powershell
python -c "from app import create_app, db; from app.models import User; app = create_app(); ctx = app.app_context(); ctx.push(); [db.session.add(u) or u.set_password('Test@1234') for u in (User(name='Temp Officer', email='officer@test.com', phone='9000000001', role='officer'), User(name='Temp Admin', email='admin@test.com', phone='9000000002', role='admin'))]; db.session.commit(); print('created')"
```
Then log in as `officer@test.com` / `admin@test.com` with password `Test@1234`.
(No code for this was added to the project; `seed.py` in Phase 3 replaces it.)

### Decisions
- CSRF: one random token per session (`secrets.token_hex`) put in every form by the
  `csrf_field()` macro and checked in one `before_request` hook for all POSTs. A bad token
  flashes "form expired" and goes back to the form page.
- Login ignores `?next=` and always goes to the role dashboard (simple, no open-redirect risk).
- The user loader returns nothing for a deactivated user, so they are logged out on their
  next request too.
- Forms use `novalidate` so the server-side field errors are what the user sees.

---

## Phase 3 — Seed data (users only)

### Plan
- `seed.py`: `confirm_reset()` (y/n), `reset_database()` (drop + create + default LoanSetting),
  `seed_users()` (7 users from §11, hashed passwords, borrower incomes ₹30k–₹80k),
  empty `seed_loans()` marked for Phase 7, `print_summary()`; everything in one commit.
- `README.md`: seed command + demo logins table.

### Verified
- `n` → "Cancelled. Nothing was changed."; `y` → database reset and the accounts table printed.
- All 7 accounts log in through the login form and land on the correct dashboard.
- Settings row = 12 %, ₹5,000–₹1,00,000, 3–24 months, 50 %.
- No temporary test-login code existed in the project (the Phase 2 snippet lived only in this file).

### Decisions
- Borrower incomes: Aman ₹45,000, Sneha ₹60,000, Rohan ₹30,000, Kavya ₹80,000.
- seed.py does not touch `uploads/` (never delete uploads); old files there simply become unused.

---

## Phase 4 — Loan application (borrower side)

### Plan
- `app/services/emi.py`: `calculate_emi`, `max_affordable_amount` (EMI formula solved for P),
  `add_months` (month-end safe), `build_schedule` (last installment absorbs rounding), self-test
- `app/services/loan_service.py`: `ALLOWED_TRANSITIONS`, `LoanError`, `change_status`,
  `get_settings`, `get_active_loan`, `check_document`, `check_affordability`, `check_application`,
  `apply_for_loan` (rate locked, uuid file name, one commit + rollback), `cancel_loan`
- `app/utils/formatters.py`: `inr` (₹1,00,000.00) and `format_date` (22 Oct 2026) filters
- `app/routes/borrower.py`: dashboard, apply, loans, loan detail, cancel (+ ownership helper)
- `app/routes/main.py`: `/documents/<id>` (owner / officer / admin)
- `app/__init__.py`: register filters, 413 handler for oversized uploads
- Templates: `borrower/dashboard|apply|loans|loan_detail.html`, `status_badge` macro, navbar links
- `app/static/js/main.js`: live EMI preview (same formula), limit + affordability hints

### Verified
- `python app/services/emi.py`: EMI 4442.44; 0 % → 1000.0; 31 Jan + 1 month → 28 Feb;
  schedule total = EMI × 12 exactly.
- JS preview checked with Node: EMI 4442.44, max affordable 28,137 (same as Python).
- Test client, 52/52 checks: amount < ₹5,000 / > ₹1,00,000 blocked; tenure 2, 25, 12.5 blocked;
  purpose required; .exe, empty, missing and 2.5 MB files rejected with field errors; > 3 MB
  request handled by the 413 handler; EMI over 50 % of income blocked with "you can borrow at most
  ₹28,137.00"; valid ₹50,000 / 12 m saved as Applied with EMI 4442.44, 12 %, uuid file name in
  `uploads/`; second application blocked and the form is replaced by a message; cancel works only
  while Applied; another borrower gets 404 on the loan page, its document and its cancel URL;
  officer and admin can open the document; uploads are not reachable under `/static`;
  changing the rate to 14 % leaves the existing loan at 12 %.
- Live server: `/`, `/login`, `/static/js/main.js` → 200, no server errors.

### Decisions
- Borrowers get **404** (not 403) for another borrower's loan or document, so they cannot
  learn that it exists.
- The document is required (see Phase 0, question 6). The original file name is cleaned with
  `secure_filename` before it is stored.
- If the database save fails after the file was written, that file is removed again (rollback).
- The affordability message caps the "max affordable amount" at the settings maximum and says
  so if it falls below the minimum amount.
- A request over 3 MB is cut off by Flask (413) and the user is sent back to the form with a
  message. Note: with the Werkzeug development server some browsers show "connection reset"
  for very large files instead of the message; files up to 3 MB always get the normal field error.
