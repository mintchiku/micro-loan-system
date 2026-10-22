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
| 5. Officer | Done |
| 6. Repay | Done |
| 7. Admin + full seed | Done |
| 8. Polish | Done |
| 9. Final audit | Done (report only, no code changed) |

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

---

## Phase 5 — Officer workflow

### Plan
- `loan_service.py`: `search_loans` (status + name / LN-ID search), `officer_summary`,
  `pick_up_loan`, `approve_loan`, `reject_loan` (remarks required), `disburse_loan`
  (sets `disbursed_on`, creates Repayment rows from `build_schedule`) — all through `change_status`
- `routes/officer.py`: dashboard, `/applications` (status tabs + search), `/applications/<id>`,
  POST `/applications/<id>/<action>` with action = `pickup | approve | reject | disburse`
- Templates: `officer/dashboard.html`, `officer/applications.html`,
  `officer/application_detail.html`; `schedule_table` macro; "Applications" navbar link

### Verified (test client, 43/43 checks; Phase 2 and 4 checks re-run: all pass)
- Borrower applies → officer1 picks up (Under Review, `officer_id` set) → approves
  (`reviewed_on`, remarks saved) → disburses (`disbursed_on` = today) → 12 Pending installments,
  due dates = disbursed_on + i months, total = EMI × 12 to the paisa; schedule shown on the page.
- Skipping states (Applied → Approved / Disbursed) and disbursing twice are refused.
- Reject with blank remarks is refused with a message; reject with remarks → Rejected, borrower
  sees the reason and can apply again.
- officer2 sees "Assigned to Priya Officer" and no buttons; officer2's approve / reject / disburse /
  pick-up POSTs (typed URLs) are all refused by `change_status` with a clear error.
- Unknown action → 404, GET on an action URL → 405, borrower or admin POST → 403.
- Admin can open the list and detail pages read-only (no forms).
- Borrower loan page shows the new status, officer name and remarks.

### Decisions
- Admin read-only access reuses `/officer/applications` and `/officer/applications/<id>`
  (`@role_required("officer", "admin")`); the action route is officer-only.
- Approve accepts optional remarks; reject requires them (max 300 characters).
- Approve and Reject share one form (two buttons with `formaction`); confirm dialog on Reject
  and Disburse.
- Search accepts `LN-0007`, `ln7` or `7` as a loan ID, otherwise matches the borrower name.

---

## Phase 6 — Repayments

### Plan
- `loan_service.py`: `pay_installment(loan, borrower, repayment_id)` (only the earliest Pending
  row; Paid + today; Disbursed → Repaying on first payment; Repaying → Closed + `closed_on`
  when none are Pending; one commit with rollback) and `borrower_summary(borrower)`
- `routes/borrower.py`: POST `/borrower/loans/<id>/pay`; dashboard uses `borrower_summary`
- `macros.html`: `schedule_table(loan, pay_url)` adds a Pay button (with confirm) on the
  earliest Pending row only; overdue rows red with an "Overdue" badge
- `borrower/loan_detail.html`: repayment summary (total payable, paid, outstanding, next due,
  X of N paid, progress bar) + schedule
- `borrower/dashboard.html`: next due amount/date, overdue warning, recent payments

### Verified (test client, 29/29; Phases 2, 4, 5 re-run: all pass)
- 3-month loan: only installment 1 has a Pay button; paying installment 3 first is refused
  ("Only the earliest pending installment can be paid"); paying the same row twice is refused.
- First payment → Repaying; last payment → Closed with `closed_on`, outstanding ₹0, paid = total;
  no Pay button afterwards; paying a Closed loan is refused.
- After closing, the borrower sees the Apply form again.
- Another borrower → 404, officer → 403 on the pay URL.
- With due dates moved into the past: `is_overdue()` true for past Pending rows only, red
  "Overdue" badges on the borrower and officer schedules, dashboard warning "2 overdue
  installments"; a paid row is never overdue.

### Test snippet: make a loan overdue without waiting (one-time, not a feature)
Run from the project folder with the venv active; change `LOAN_ID` to the disbursed loan's number
(LN-0005 → 5). It moves every due date of that loan 2 months back.
```powershell
python -c "from app import create_app, db; from app.models import Loan; from app.services.emi import add_months; app = create_app(); app.app_context().push(); LOAN_ID = 1; loan = db.session.get(Loan, LOAN_ID); [setattr(r, 'due_date', add_months(r.due_date, -2)) for r in loan.repayments]; db.session.commit(); print('Moved due dates of', loan.display_id())"
```

### Decisions
- The pay form sends the installment id; the server checks it is the earliest Pending one, so a
  double click or a stale page cannot pay two installments.
- Payment and status changes use the actor `"system"` for Disbursed → Repaying and
  Repaying → Closed, exactly as in the §6 table.

---

## Phase 7 — Admin panel, reports, full seed

### Plan
- `utils/validators.py`: `validate_settings_form` (rate 0–36, max > min for amount and tenure,
  whole-month tenures, EMI % 1–100)
- `loan_service.py`: `search_users`, `toggle_user_active` (not yourself), `update_settings`,
  `admin_totals`, `disbursed_per_month`, `overdue_installments`, `STATUS_ORDER`
- `routes/admin.py`: dashboard, users, new-officer, toggle (POST), settings, reports
- Templates: `admin/dashboard|users|new_officer|settings|reports.html`; admin navbar links
- Reports: Chart.js 4.4.4 from the CDN, data passed with `|tojson`
- `seed.py`: `seed_loans()` with 7 loans + loan table in the printed summary
- Admin loan details: reuses the officer detail page in read-only mode (decision from Phase 5)

### Seeded loans (dates are relative to the day you run seed.py)
| Loan | Borrower | Amount | Months | Status | Notes |
|---|---|---|---|---|---|
| LN-0001 | Sneha | 20,000 | 4 | Closed | disbursed 5 months ago, all 4 paid |
| LN-0002 | Aman | 30,000 | 6 | Repaying | disbursed 4 months + 10 days ago; 3 paid, installment 4 overdue |
| LN-0003 | Rohan | 40,000 | 12 | Rejected | remarks: document not readable |
| LN-0004 | Kavya | 15,000 | 6 | Cancelled | |
| LN-0005 | Kavya | 60,000 | 12 | Approved | officer2, ready to disburse |
| LN-0006 | Sneha | 25,000 | 9 | Under Review | officer1 |
| LN-0007 | Rohan | 35,000 | 12 | Applied | unassigned |

### Verified (test client on the real seed data, 90/90; phases 2, 4, 5, 6 re-run: all pass)
- Seed: all 7 statuses present, no borrower has more than one active loan, the Repaying loan has
  exactly 1 overdue and 3 paid installments, the Closed loan is fully paid, schedule totals are exact.
- Bar chart data: 6 month labels, two non-zero months, total ₹50,000; pie data covers all 8 statuses.
  The inline chart script is valid JavaScript (`node --check`).
- Access: every admin URL is 200 for admin, 403 for officer and borrower, redirect to login when
  logged out; officer/borrower POSTs to admin routes → 403.
- Dashboard totals match the database (users, disbursed, collected, outstanding, overdue = 1).
- Users: role filter, name/email search (case-insensitive), empty state; deactivated user cannot
  log in and an already-open session is logged out; admin cannot deactivate self; confirm dialog.
- Create officer: duplicate email, bad phone/password rejected with values kept; new officer
  logs in to the officer dashboard; public `/register` ignores a posted role.
- Settings: 8 invalid inputs rejected with field errors; valid save to 14 % → existing loans
  stay at 12 %, a new application gets 14 % (EMI ₹4,489.36 for ₹50,000 / 12 months).
- Admin can open any loan read-only (no action forms; POST actions → 403).

### Decisions and notes
- **"Disbursed" is not seeded** (see Phase 0, question 4): only 4 borrowers exist and each may have
  one active loan, so the four active slots are Applied, Under Review, Approved and Repaying.
- Only the 7 loans listed in the blueprint are seeded, so the bar chart has data in two months
  (Closed loan 5 months ago, Repaying loan 4 months ago).
- Seeded loans have no uploaded document (the detail pages show "None"); documents are
  demonstrated by registering a new borrower in the demo script.
- A bug found and fixed while testing: in Jinja `chart.values` returns the dict method, so the
  template uses `chart["values"]`.

---

## Phase 8 — Polish

### What was checked / changed
- Static audit of all 18 Python files and 20 templates: every function and class has a one-line
  docstring (two inner functions in `decorators.py` were missing one — added), no unused imports,
  no `print()` outside `seed.py` and the `emi.py` self-test, no TODO / debug leftovers, every page
  extends `base.html` with its own `<title>`, every POST form contains `csrf_field()`, and all money
  and dates in templates go through `inr` / `date` (the only raw numbers are `data-*` attributes read by
  the live EMI preview JavaScript).
- Landing page: hero, "How it works" (3 steps), new "Why MicroLoan?" features row, footer; no external images.
- Confirm dialogs: cancel application, reject, disburse, pay installment, activate / deactivate user.
- Empty states with a helpful button on: My loans, borrower dashboard, officer dashboard, applications
  list, users list, reports (charts and overdue table), recent payments.
- Flash messages use Bootstrap colours (success, danger, warning, info); the login-required message is a warning.
- Tables are in `.table-responsive`, the navbar collapses on phones, forms use the Bootstrap grid.
- `README.md` rewritten: features, tech stack, setup, seed, run, demo logins, seeded loans, demo script, folder tree.

### Verified
- Page crawl on the seeded data, 61/61: 3 public pages, borrower / officer / admin pages and every
  seeded loan detail page for each role return 200 with a `| MicroLoan` title, the viewport meta tag, and
  no unrendered template text; spot checks of the Repaying, Closed, Cancelled, Approved and Rejected
  borrower views, officer ownership view, document download, 403 / 404 / 500 pages.
- Phases 2, 4, 5, 6, 7 test suites re-run after the changes: all pass.

### Note
- The pages were checked through the Flask test client and HTML assertions, not by eye in a browser.
  Please click through the pages once (especially at phone width) — see the manual-check list in the final report.

---

## Phase 9 — Final audit (report only)

An audit script (outside the project) ran `seed.py`'s functions on a temporary database and checked, with the
Flask test client: the demo script (§13), the permission matrix (§4), every (from, to, actor) transition
(6 actors x 8 x 8 = 384 combinations), business rules 1-11, and NFR1-NFR12. Result: **89/89 checks pass**.
Checks that could be vacuous were given a control (e.g. a token-less POST changes nothing, the same POST with
a token does).

### Issues found (nothing fixed yet; waiting for the owner to choose)
1. **Amounts with more than 2 decimals are accepted** (e.g. 10000.999 is stored as-is). Suggested fix: reject or round to 2 decimals in `check_application`.
2. **Uploaded files are checked by extension and size only**, not by content (a text file named `.pdf` is accepted). Blueprint rule 10 only asks for type by extension, so this is "met", but it is the weakest part of NFR5.
3. **A deactivated officer's Under Review / Approved loans are stuck**: rule 11 means no other officer can act on them and there is no reassign feature (the blueprint has none). Suggest: warn on deactivation, or allow the admin to reassign.
4. **Duplicate email race**: the unique check runs before the insert; two simultaneous registrations could hit the database `IntegrityError` and show the 500 page. Very unlikely in a demo.
5. **Session cookie `SameSite` is not set** (Flask default None). CSRF tokens already protect the POST forms; adding `SESSION_COOKIE_SAMESITE = "Lax"` is a one-line hardening.
6. `GET /logout` changes state (the blueprint's own §8 table specifies GET).

### Blueprint vs. code
- Not in the blueprint but added (all small, needed): `app/templates/macros.html`, `app/utils/formatters.py` (the `inr` / `date` filters), `LoanError`, `STATUS_ORDER`, a 413 handler, `PROGRESS.md`.
- Admin read-only access to applications reuses the officer routes (the blueprint lists no admin application page).
- In the blueprint but not built as written: separate `EMICalculator` / `LoanService` **classes** (built as module functions), an `about` page mentioned in the folder tree, the *Disbursed* status in the seed data (see Phase 7 decisions).

---

## UI redesign: yellow and blue theme (after Phase 9)

Requested: take inspiration from a bank's website UI, apply the Laws of UX, make yellow and blue the primary colours,
and use Claude Design. No routes, models or business rules changed.

### What was built
- **Design canvas** (Claude Design, private): style guide, Home, Sign in, Borrower dashboard, Loan details, Officer
  review. It was the visual spec, then the real templates were built to match.
- `static/css/style.css` rewritten: design tokens, Bootstrap re-skin (buttons, forms, cards, tables, badges, alerts),
  components (stepper, timeline, stat tiles, progress bar), landing and login layouts, phone rules.
- `templates/base.html`: utility strip, header with active-link underline and user chip, flash alerts with icons,
  full footer on the landing page and a slim footer elsewhere. Pages that need edge-to-edge layout override the
  new `page` block.
- `templates/macros.html`: `status_badge` (soft pills), `input_field` with a rupee prefix, `breadcrumb`,
  `empty_state`, `progress_bar`, `loan_stepper`, restyled `schedule_table`.
- Every template restyled (landing, login, register, borrower x4, officer x3, admin x5, errors).
- `static/js/main.js`: busy state on submit (spinner, ignores double clicks), loaded on every page.
- Small code changes: `main.index` passes the current settings so the landing page facts and the example EMI are
  never stale (`loan_service.sample_loan`), `officer.application_detail` passes settings for the affordability
  meter, an `inr_short` filter, and new pie colours in `admin.py`.
- CLAUDE.md section 9a and a README "Design" section document the theme.

### Verified
- All earlier suites re-run (phases 2, 4, 5, 6, 7, 8 and the final audit): all pass. Some checks were keyed to the
  old markup (for example `display-6`, "Next due") and were updated to the same behaviour on the new markup.
- New UI suite, 146 checks: exactly one enabled yellow action per page (and it is the right one), the current nav
  link is marked, at most five menu items per role, HTML tags balanced on every page, step tracker states for every
  seeded status, progress bar width, landing page follows the admin's settings, forms keep their markers, WCAG
  contrast of 30 text/background pairs reaches 4.5:1 (and 3:1 for large text and graphics).
- Real rendering: headless Edge screenshots of 16 pages at 1360px and 4 pages at 390px, reviewed by eye. Two
  phone problems were found and fixed: the step tracker scrolled sideways (now vertical) and the Pay button was
  clipped (schedule rows are now two-line cards on phones).
- Pie palette run through the dataviz validator: the hard normal-vision rule passes; CVD separation is in the
  allowed band because the legend (with counts), the 2px gaps and a table view carry identity. The lightness and
  chroma checks still fail on purpose: "Applied" and "Cancelled" are meant to be neutral.

### Decisions and notes
- **Brand:** no bank name, logo, colours or text is used; only layout patterns. The page text of the bank's site could
  be read but not its colours or fonts, so those come from the brief and the Laws of UX.
- **System fonts only** (Segoe UI on Windows): no new dependency. A web font could be added later if wanted.
- **Pie chart kept** because the blueprint asks for it, although the dataviz guidance prefers at most 6 slices.
- **Yellow badge:** Disbursed and Repaying stay yellow (blueprint maps both to "warning"); they are soft pills, so they
  do not compete with the solid yellow buttons.
- Spelling: "installment" everywhere, as in the blueprint.
