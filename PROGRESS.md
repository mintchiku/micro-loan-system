# Build Progress — Micro-Loan Management System

This file logs each phase: the plan, what was built, how it was checked, and any decisions.
`CLAUDE.md` is the blueprint; `PROMPTS.md` has the phase instructions.

| Phase | Status |
|---|---|
| 0. Kickoff | Done |
| 1. Skeleton | Done |
| 2. Auth | Not started |
| 3. Seed (users) | Not started |
| 4. Apply | Not started |
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
