# Software Requirements Specification: MicroLoan Management System

| | |
|---|---|
| **Project** | Micro-Loan Management System (Software Engineering course project, NMIMS Hyderabad, B.Tech CS & Data Science) |
| **Document** | Software Requirements Specification, written in the style of IEEE 830 / ISO 29148 |
| **Version** | 1.0, 23 Oct 2026 |
| **Describes** | The running application (22 routes, 5 tables, 3 roles, 8 loan statuses). If this document and the code disagree, `CLAUDE.md` (the project blueprint) is checked first and the difference is raised before anything is changed. |
| **Companion files** | [02_diagrams.md](02_diagrams.md) (use case, activity, swimlane, class, CRC, DFD, state, sequence), [03_wireframes_and_prototype.md](03_wireframes_and_prototype.md) (screens) |

**How to read the IDs.** `FR-xx` is a functional requirement, `NFR-xx` a non-functional one, `R1` to `R11` are the business
rules of the blueprint, "Part 1" and "Part 2" mark requirements added or tightened after the first audit. Every requirement
is traced to code, to a diagram and to an automated test in section 8.

---

## 1. Introduction

### 1.1 Purpose

This document states **what** the MicroLoan system must do and **how well**, so that the code, the diagrams, the tests and
the demonstration can all be checked against one list. It is written for the course examiner, the project team and any
future maintainer.

### 1.2 Scope

MicroLoan is a web application for small personal loans. **Borrowers** register and apply; **loan officers** review, approve
or reject, and disburse; **admins** manage users, loan settings and reports. Repayment is tracked through an automatically
generated EMI schedule. Payments are **simulated** by a Pay button.

**In scope:** borrower self-registration; login and logout for all roles; loan application with one supporting document;
officer review workflow with remarks; EMI calculation and schedule; simulated repayments with overdue detection and
automatic closing; admin user management, officer creation, loan settings and reports with charts; admin reassignment of an
application to another officer; demo data.

**Out of scope (not built, by decision):** real payments or a payment gateway, KYC or credit-bureau checks, SMS or email,
password reset, OTP and two-factor login, a REST API, a mobile app or React front end, cloud deployment, partial payments,
prepayment, restructuring, late fees and multiple currencies.

### 1.3 Definitions, acronyms and abbreviations

| Term | Meaning |
|---|---|
| EMI | Equated monthly installment: the fixed monthly amount that repays a loan with interest |
| Reducing balance | Interest is charged on the unpaid balance, which is why the EMI formula uses the compound factor |
| Installment | One row of the repayment schedule (table `Repayment`) |
| Active loan | A loan in Applied, Under Review, Approved, Disbursed or Repaying |
| Final status | Closed, Rejected or Cancelled: nothing can change any more |
| Disburse | The officer releases the money; the schedule is created |
| Reassign | An admin hands an Under Review or Approved application to a different active officer |
| CSRF | Cross-site request forgery; blocked with a secret token in every POST form |
| Blueprint | `CLAUDE.md`, the single source of truth for the project |
| MoSCoW | Priority labels: Must, Should, Could |

### 1.4 References

1. `CLAUDE.md`: project blueprint (sections 1 to 15).
2. `README.md`: install, run, seed and demo logins.
3. `PROGRESS.md`: build log with the checks made at each phase.
4. `WEBSITE_COMPLETE_TECHNICAL_DOCUMENTATION.md`: full technical description of the code.
5. [02_diagrams.md](02_diagrams.md), [03_wireframes_and_prototype.md](03_wireframes_and_prototype.md).
6. IEEE Std 830-1998, *Recommended Practice for Software Requirements Specifications* (structure followed here).

### 1.5 Overview of this document

Section 2 describes the product in general. Section 3 lists the interfaces. Section 4 holds the functional requirements by
module. Section 5 lists the business rules, section 6 the data, section 7 the non-functional requirements. Section 8 is the
traceability matrix. Section 9 records what changed after the first audit. Appendix A shows the click paths behind NFR-08.

---

## 2. Overall description

### 2.1 Product perspective

MicroLoan is a self-contained, server-rendered web application. It has no external services: no payment gateway, no email
server, no API. A browser talks to one Flask server; the server reads and writes one SQLite file.

```
Browser  <--HTTP-->  Flask app (routes -> services -> models)  <-->  SQLite file (instance/microloan.db)
                                                                    uploads/ folder (loan documents)
```

| Layer | Choice |
|---|---|
| Language | Python 3.13 |
| Web framework | Flask 3.x with blueprints (main, auth, borrower, officer, admin) |
| Database | SQLite through Flask-SQLAlchemy |
| Authentication | Flask-Login sessions and `werkzeug.security` password hashes |
| Pages | Jinja2 templates, Bootstrap 5 and Bootstrap Icons, Chart.js for the admin charts (all from a CDN) |
| Forms | Plain HTML forms, server-side validation, hand-written CSRF token |

The code has three layers that the requirements refer to: **routes** (thin: check input, call one function, show the result),
**services** (`loan_service.py` for every business rule and status change, `emi.py` for the arithmetic) and **models** (five
tables).

### 2.2 Product functions (summary)

1. Register, log in and log out; each role gets its own dashboard.
2. Apply for a loan with a live EMI preview, a purpose and one document; the application is checked against rules R1 to R4
   and R10.
3. Review: list and filter applications, pick up, approve, reject with remarks, disburse.
4. Reassign an application to another officer (admin).
5. Repay: schedule, pay installments in order, overdue marks, automatic Repaying and Closed.
6. Administer: users, officers, loan settings.
7. Report: dashboard totals, loans by status, disbursed per month, overdue installments.

### 2.3 User classes and characteristics

| User class | How the account is made | Skills assumed | Main job |
|---|---|---|---|
| **Borrower** | Registers on the site (always this role) | Can fill in a web form | Apply, track, repay |
| **Loan officer** | Created by an admin | Understands loan review | Review, approve or reject, disburse |
| **Admin** | Created by `seed.py` only | Manages the service | Users, settings, reports, reassignment |
| **System** (secondary actor) | Not a person | - | Updates status automatically, works out overdue |

### 2.4 Operating environment

A modern desktop or phone browser (the page is responsive down to 390 px width) and a machine with Python 3.13 and the
packages in `requirements.txt`. The pages need internet access for Bootstrap and Chart.js (CDN). Developed and tested on
Windows 11 with PowerShell.

### 2.5 Design and implementation constraints

- Keep exactly the stack above; no further libraries without permission.
- Business rules and status changes only in `app/services/loan_service.py`; routes stay thin.
- Every state-changing action is a POST (including logout); the database commit happens once per action, inside
  try/except with rollback.
- Money is stored as floating-point numbers rounded to 2 decimals (known limitation).
- The code must stay simple enough for a second-year student to explain line by line.

### 2.6 Assumptions and dependencies

- One server process and one user at a time is enough (local demonstration); there is no locking for simultaneous
  requests beyond the database's unique index on email.
- The clock of the server is the clock of the system (dates have no time zone).
- Bootstrap, Bootstrap Icons and Chart.js stay available on their CDN.
- The demo data are created by `seed.py`; the live database is never reset by anything else.

### 2.7 Out of scope

See section 1.2. Nothing in this document requires those features.

---

## 3. External interface requirements

### 3.1 User interface

- One base layout with a role-dependent navigation bar; flash messages below it; the same status badge colours on every page.
- Design: **blue** for structure, **yellow** for the one next action on a page (at most one enabled yellow button per page);
  system fonts; text contrast of at least 4.5 to 1 (NFR-14).
- Every form shows a message under each wrong field and keeps the typed values (FR-02, FR-11, FR-43).
- Phone layout: stacked cards, vertical status tracker, no sideways scrolling (NFR-15).
- Screens: [03_wireframes_and_prototype.md](03_wireframes_and_prototype.md).

### 3.2 Software interfaces

| Interface | Use |
|---|---|
| SQLite database file `instance/microloan.db` | All persistent data, through Flask-SQLAlchemy |
| `uploads/` folder | Loan documents, outside `static/`, served only by `GET /documents/<id>` |
| CDN: Bootstrap 5.3, Bootstrap Icons, Chart.js 4 | Styling, icons, charts |

### 3.3 Communication interfaces

HTTP between browser and server (plain HTTP on `127.0.0.1` for the demonstration). The session is a signed cookie with
`SameSite=Lax` and `HttpOnly`. Forms are submitted with POST and carry a `csrf_token`; the server answers a successful POST
with a redirect to a GET page.

### 3.4 Hardware interfaces

None.

---

## 4. Functional requirements

Each requirement has an ID, a title, the statement ("The system shall ..."), the actor, a priority (Must, Should, Could),
and the source in the code (route and function, with the line where it starts in the current code). A tag such as *R3* names
the business rule in section 5; *Part 2a* names a change made after the first audit (section 9).

### 4.1 Accounts and access (FR-01 to FR-09)

| ID | Title | Requirement | Actor | Priority | Source (route and function) |
|---|---|---|---|---|---|
| **FR-01** | Borrower self-registration | The system shall let a visitor register as a borrower by giving name, email, phone, monthly income and a password. The new account shall always have the role borrower, whatever the form contains, and the new borrower shall be signed in. | Visitor | Must | `GET/POST /register` · `auth.register` (auth.py:14) → `loan_service.create_user` (loan_service.py:84) |
| **FR-02** | Registration validation | The system shall check the registration form on the server: name required (at most 100 characters); email in a valid form (at most 120); phone exactly 10 digits; monthly income a number greater than 0; password at least 8 characters with a letter and a digit, and a matching confirmation. It shall show a message under each wrong field and keep the other values the visitor typed. | Visitor, Admin (create officer) | Must | `validators.validate_user_form` (validators.py:109) |
| **FR-03** | Unique email *(Part 2d)* | The system shall keep emails unique, ignoring upper or lower case. A duplicate shall show "This email is already registered." as a field error, also when two sign-ups with the same email arrive at the same moment and the database unique index rejects the second one (no 500 page, nothing half-saved). | Visitor, Admin | Must | `validate_user_form` (validators.py:109), `create_user` catches `IntegrityError` (loan_service.py:98) |
| **FR-04** | Login | The system shall let a registered user log in with email and password. A wrong email or password shall give the same message, "Invalid email or password.", so it does not reveal which one was wrong. | All users | Must | `GET/POST /login` · `auth.login` (auth.py:32) |
| **FR-05** | Role-based redirect | The system shall send each user to the dashboard of their role after login (borrower, officer or admin). A user who is already logged in and opens `/login` or `/register` shall be redirected to their dashboard. | All users | Must | `auth.login`, `decorators.dashboard_url` (decorators.py:26) |
| **FR-06** | Deactivated accounts are blocked | The system shall refuse login to an account whose `is_active` is false ("Your account has been deactivated. Please contact the admin."). A user who is deactivated while signed in shall be signed out on the next request. | All users | Must | `auth.login` (auth.py:32), `models.load_user` (models.py:132) |
| **FR-07** | Logout as POST *(Part 2f)* | The system shall log a user out only through a POST request that carries the CSRF token (the navbar Logout button is a small form). A plain GET to `/logout` shall answer 405 and keep the session. After logout the user shall see the landing page with a message. | All users | Must | `POST /logout` · `auth.logout` (auth.py:54) |
| **FR-08** | Role-based access | The system shall check the role on every protected page. A visitor who is not logged in shall be sent to the login page; a user of the wrong role shall see the 403 page. | All users | Must | `decorators.role_required` (decorators.py:10) |
| **FR-09** | Ownership | The system shall let a borrower see, pay or cancel only their own loans and open only their own documents. Another borrower's loan or document shall answer 404. | Borrower | Must | `borrower.loan_detail` (borrower.py:64), `borrower.pay` (borrower.py:72), `borrower.cancel` (borrower.py:87), `main.view_document` (main.py:22) |

### 4.2 Loan application (FR-10 to FR-21)

| ID | Title | Requirement | Actor | Priority | Source (route and function) |
|---|---|---|---|---|---|
| **FR-10** | Apply form with live EMI preview *(R5)* | The system shall give a borrower a form for amount, tenure in months, purpose and one document. While the borrower types, the page shall show the EMI preview without calling the server. | Borrower | Must | `GET/POST /borrower/apply` · `borrower.apply` (borrower.py:33), `static/js/main.js` |
| **FR-11** | Amount limits and decimals (R1) *(R1, Part 2a)* | The system shall accept an amount only between the minimum and the maximum amount in the loan settings, with at most 2 decimal places. A third decimal (for example 10000.999) shall be refused with "Use at most 2 decimal places."; 10000.99 and 10000.990 shall be accepted. | Borrower | Must | `loan_service.check_application` (loan_service.py:158), `validators.has_too_many_decimals` (validators.py:45) |
| **FR-12** | Tenure limits (R2) *(R2)* | The system shall accept a tenure only as a whole number of months between the minimum and the maximum tenure in the loan settings. | Borrower | Must | `check_application` (loan_service.py:158) |
| **FR-13** | One active loan at a time (R3) *(R3)* | The system shall refuse a new application while the borrower has a loan in Applied, Under Review, Approved, Disbursed or Repaying. Loans that are Closed, Rejected or Cancelled shall not block. | Borrower | Must | `check_application` (loan_service.py:158), `User.has_active_loan` (models.py:38) |
| **FR-14** | Affordability (R4) *(R4)* | The system shall refuse an application whose EMI is more than the allowed percentage of the borrower's monthly income and shall show the largest amount the borrower can afford for that tenure. This check shall run only when the amount and the tenure are themselves valid. | Borrower | Must | `check_affordability` (loan_service.py:144), `emi.max_affordable_amount` (emi.py:16) |
| **FR-15** | EMI calculation (R5) *(R5)* | The system shall calculate the EMI with the reducing-balance formula EMI = P x r x (1 + r)^n / ((1 + r)^n - 1), where r = annual rate / 12 / 100 and n = tenure; at a rate of 0 the EMI shall be P / n. The EMI shall be rounded to 2 decimals (for example 50,000 for 12 months at 12% gives 4,442.44). | System | Must | `emi.calculate_emi` (emi.py:7) |
| **FR-16** | Interest rate locked (R6) *(R6)* | The system shall copy the interest rate from the loan settings into the loan when the application is saved. A later change of the setting shall not change existing loans. | System | Must | `loan_service.apply_for_loan` (loan_service.py:194) |
| **FR-17** | Supporting document (R10) *(R10, Part 2b)* | The system shall require exactly one supporting file per application. It shall accept only PDF, JPG or PNG, not empty and at most 2 MB, and the first bytes of the file shall match its type (PDF, PNG or JPEG signature), so a text file renamed to .pdf is refused. The file shall be saved with a random uuid name outside `static/`, the original name kept only for display, and removed again if the loan cannot be saved. | Borrower | Must | `check_document` (loan_service.py:110), `detect_file_type` (loan_service.py:133), `apply_for_loan` (loan_service.py:194) |
| **FR-18** | Purpose | The system shall require a purpose of at most 200 characters. | Borrower | Must | `check_application` (loan_service.py:158) |
| **FR-19** | Cancel own application | The system shall let the owning borrower cancel an application, but only while its status is Applied. | Borrower | Must | `POST /borrower/loans/<id>/cancel` · `borrower.cancel` (borrower.py:87) → `loan_service.cancel_loan` (loan_service.py:230) |
| **FR-20** | My loans and loan details | The system shall list the borrower's loans and show, for one loan, a status tracker, the amounts, the officer's remarks and (once disbursed) the EMI schedule. | Borrower | Must | `borrower.loans` (borrower.py:56), `borrower.loan_detail` (borrower.py:64) |
| **FR-21** | Apply button state *(Part 1a)* | While the borrower has an active loan, the "Apply for loan" action on the dashboard and on My loans shall look and behave the same: a disabled button with the text "Available again once your current loan is closed." No enabled yellow action shall lead to a page that is blocked for the user. | Borrower | Should | `macros.apply_button` (macros.html), `borrower.dashboard` (borrower.py:25), `borrower.loans` (borrower.py:56) |

### 4.3 Review, disbursal and reassignment (FR-22 to FR-33)

| ID | Title | Requirement | Actor | Priority | Source (route and function) |
|---|---|---|---|---|---|
| **FR-22** | Applications list | The system shall list applications with a filter by status and a search by borrower name or loan id (LN-0007, ln7 and 7 all find loan 7). Officers and the admin may open the list. | Officer, Admin | Must | `GET /officer/applications` · `officer.applications` (officer.py:28) → `loan_service.search_loans` (loan_service.py:242) |
| **FR-23** | Application detail | The system shall show an application with the borrower's details, the loan facts, how close the EMI is to the affordability limit, a link to the document, the schedule (once disbursed), the status history and the remarks. | Officer, Admin | Must | `GET /officer/applications/<id>` · `officer.application_detail` (officer.py:41) |
| **FR-24** | Pick up *(R11)* | The system shall let any officer pick up an Applied application. The status shall become Under Review and the officer shall be saved on the loan. | Officer | Must | `POST /officer/applications/<id>/pickup` · `officer.application_action` (officer.py:69) → `pick_up_loan` (loan_service.py:270) |
| **FR-25** | Approve *(R11)* | The system shall let the assigned officer approve an Under Review application (optional remarks). The status shall become Approved and the review date shall be saved. | Officer | Must | `application_action` (officer.py:69) → `approve_loan` (loan_service.py:281) |
| **FR-26** | Reject with remarks *(R11)* | The system shall let the assigned officer reject an Under Review application only when remarks (at most 300 characters) are entered. The status shall become Rejected and the review date and remarks shall be saved. | Officer | Must | `application_action` (officer.py:69) → `reject_loan` (loan_service.py:295) |
| **FR-27** | Officer ownership (R11) *(R11)* | After an officer has picked an application up, only that officer shall be able to approve, reject or disburse it. Other officers shall see a notice that it is assigned to someone else, and the server shall refuse their request anyway. | Officer | Must | `change_status` (loan_service.py:41), `application_detail.html` |
| **FR-28** | Disburse *(R7, R11)* | The system shall let the assigned officer disburse an Approved loan after a confirm dialog. The status shall become Disbursed, the disbursal date shall be today and the EMI schedule shall be created, all saved in one commit. | Officer | Must | `application_action` (officer.py:69) → `disburse_loan` (loan_service.py:311) |
| **FR-29** | One state machine | The system shall change a loan's status only through one transition table and one function. Any change not in the table shall be refused with a clear message, and nothing shall be saved. | System | Must | `ALLOWED_TRANSITIONS`, `change_status` (loan_service.py:41) |
| **FR-30** | Admin reassignment *(R11, Part 2c)* | The system shall let an admin hand an Under Review or Approved application to another active loan officer. Only the officer shall change; the status stays the same. It shall be refused for every other status, for the officer who already holds the loan, and for inactive or non-officer accounts. It shall be saved in one commit with rollback on error. Afterwards the new officer, and not the old one, shall be able to approve, reject or disburse. | Admin | Must | `POST /officer/applications/<id>/reassign` · `officer.reassign_application` (officer.py:53) → `loan_service.reassign_loan` (loan_service.py:343) |
| **FR-31** | Reassign form *(Part 2c)* | The system shall show the admin, on an Under Review or Approved application, a "Reassign to" list of the active officers except the current one, with a blue outline button and a confirm dialog. Officers and borrowers shall not see it, and it shall add no enabled yellow button to the admin's page. | Admin | Must | `officer.application_detail` (officer.py:41), `active_officers` (loan_service.py:330), `application_detail.html` |
| **FR-32** | Deactivation notice *(Part 2c)* | When an admin deactivates an officer who still holds Under Review or Approved loans, the system shall show a warning with how many loans need reassigning. With none, it shall show the normal success message. | Admin | Should | `admin.toggle_user` (admin.py:59), `pending_loan_count` (loan_service.py:338) |
| **FR-33** | Admin read-only view | The system shall let the admin open the applications list and each application read-only. The admin shall have no pick-up, approve, reject or disburse action; the only application action of an admin is reassignment (FR-30). | Admin | Must | `officer.applications`, `officer.application_detail`; `application_action` is `role_required("officer")` (officer.py:69) |

### 4.4 Schedule and repayment (FR-34 to FR-39)

| ID | Title | Requirement | Actor | Priority | Source (route and function) |
|---|---|---|---|---|---|
| **FR-34** | EMI schedule at disbursal *(R5, R7)* | The system shall create the schedule only when the loan is disbursed: one installment per month of tenure, installment i due on the disbursal date plus i months (if that day does not exist, the last day of that month), each for the EMI, with the last installment adjusted so that the total is exactly EMI x n. Each row starts as Pending. | System | Must | `emi.build_schedule` (emi.py:36), `emi.add_months` (emi.py:27), `disburse_loan` (loan_service.py:311) |
| **FR-35** | Pay in order (R8) *(R8)* | The system shall let the owning borrower pay only the earliest Pending installment, after a confirm dialog. Payments are simulated; no real money moves. Any other installment shall be refused with a message. | Borrower | Must | `POST /borrower/loans/<id>/pay` · `borrower.pay` (borrower.py:72) → `loan_service.pay_installment` (loan_service.py:363) |
| **FR-36** | Repaying | The system shall change the status from Disbursed to Repaying when the first installment is paid. | System | Must | `pay_installment` (loan_service.py:363) |
| **FR-37** | Automatic closing | The system shall change the status from Repaying to Closed, and save the closed date, when no installment is Pending any more. The borrower may then apply again. | System | Must | `pay_installment` (loan_service.py:363) |
| **FR-38** | Overdue (R9) *(R9)* | The system shall show a Pending installment whose due date is before today with a red Overdue badge. Overdue shall be worked out when the page is drawn, never stored, and there shall be no late fee. | System | Must | `Repayment.is_overdue` (models.py:103), `macros.schedule_table` |
| **FR-39** | Consistent status badges | The system shall show every status with the same badge colour on every page: Applied grey, Under Review light blue, Approved blue, Rejected red, Cancelled dark, Disbursed and Repaying yellow, Closed green, Overdue red. | All users | Should | `macros.status_badge` (macros.html) |

### 4.5 Administration (FR-40 to FR-45)

| ID | Title | Requirement | Actor | Priority | Source (route and function) |
|---|---|---|---|---|---|
| **FR-40** | List and search users | The system shall let the admin list users with a tab per role and a search by name or email. | Admin | Must | `GET /admin/users` · `admin.users` (admin.py:33) → `search_users` (loan_service.py:404) |
| **FR-41** | Activate or deactivate a user | The system shall let the admin activate or deactivate any user except themselves, with a confirm dialog. | Admin | Must | `POST /admin/users/<id>/toggle` · `admin.toggle_user` (admin.py:59) → `toggle_user_active` (loan_service.py:415) |
| **FR-42** | Create officer | The system shall let the admin create a loan officer with name, email, phone and password (no income). The account shall have the role officer and the same validation as registration. | Admin | Must | `GET/POST /admin/users/new-officer` · `admin.new_officer` (admin.py:44) → `create_user` |
| **FR-43** | Loan settings *(Part 2a)* | The system shall let the admin change the loan settings: interest rate 0 to 36 % a year; minimum and maximum amount (greater than 0, maximum greater than minimum, at most 2 decimals); minimum and maximum tenure (whole months, at least 1, maximum greater than minimum); maximum EMI as a share of income, 1 to 100 %. Wrong fields shall show a message and keep the typed values. | Admin | Must | `GET/POST /admin/settings` · `admin.settings` (admin.py:79), `validate_settings_form` (validators.py:67), `update_settings` (loan_service.py:427) |
| **FR-44** | Settings apply to new loans only *(R6)* | The system shall let a settings change affect only applications made afterwards. Existing loans keep the interest rate they were given, and the apply and landing pages shall show the current values. | Admin | Must | `apply_for_loan` (loan_service.py:194), `main.index` (main.py:14) |
| **FR-45** | Admin accounts only by seed | The system shall create admin accounts only through `seed.py`. No page shall let anyone choose or create the admin role. | System | Must | `seed.py`, `auth.register` (always borrower) |

### 4.6 Dashboards and reports (FR-46 to FR-51)

| ID | Title | Requirement | Actor | Priority | Source (route and function) |
|---|---|---|---|---|---|
| **FR-46** | Borrower dashboard | The system shall show the borrower an active loan card (status badge, amount, EMI, next due date, outstanding), the Apply button in its correct state (FR-21) and the recent payments. | Borrower | Must | `borrower.dashboard` (borrower.py:25) → `borrower_summary` (loan_service.py:388) |
| **FR-47** | Officer dashboard | The system shall show the officer counts (new applications, under my review, approved awaiting disbursal) and a table of their pending work. | Officer | Must | `officer.dashboard` (officer.py:20) → `officer_summary` (loan_service.py:257) |
| **FR-48** | Admin dashboard | The system shall show the admin the totals: users, loans by status, rupees disbursed, collected and outstanding, and the number of overdue installments, with links to the reports. | Admin | Must | `admin.dashboard` (admin.py:26) → `admin_totals` (loan_service.py:449) |
| **FR-49** | Loans-by-status chart and table *(Part 1b)* | The system shall show a pie chart of loans by status and, under "View as table", the share of each status with one decimal. The shares shall add up to exactly 100.0 % (the largest status absorbs the rounding). The same helper shall be used wherever a share is shown, and the chart itself shall not change. | Admin | Must | `admin.reports` (admin.py:97), `loan_service.percent_shares` (loan_service.py:469) |
| **FR-50** | Disbursed per month chart | The system shall show a bar chart of the amount disbursed in each of the last 6 months. | Admin | Must | `disbursed_per_month` (loan_service.py:479) |
| **FR-51** | Overdue installments table *(R9)* | The system shall list every overdue installment with borrower, loan, due date and amount. | Admin | Must | `overdue_installments` (loan_service.py:443) |

### 4.7 Documents (FR-52)

| ID | Title | Requirement | Actor | Priority | Source (route and function) |
|---|---|---|---|---|---|
| **FR-52** | View a document *(R10)* | The system shall let the owning borrower, any officer and the admin open a loan's document. A borrower who does not own the loan shall get 404. Files shall be reachable only through this protected route. | Borrower, Officer, Admin | Must | `GET /documents/<id>` · `main.view_document` (main.py:22) |

### 4.8 Presentation and general (FR-53 to FR-58)

| ID | Title | Requirement | Actor | Priority | Source (route and function) |
|---|---|---|---|---|---|
| **FR-53** | Formats | The system shall show money in the Indian style (for example 1,00,000.00 with the rupee sign) and dates as 22 Oct 2026. | All users | Should | `formatters.inr` (formatters.py:4), `format_date` (formatters.py:27) |
| **FR-54** | Confirm dialogs | The system shall ask for confirmation before cancel, reject, disburse, pay and reassign. | Borrower, Officer, Admin | Should | templates `loan_detail.html`, `application_detail.html`, `macros.schedule_table` |
| **FR-55** | Empty states and error pages | The system shall show a friendly message instead of an empty table, and its own pages for 403, 404, 413 (file too large) and 500. | All users | Should | `macros.empty_state`, `register_error_handlers` (app/__init__.py:80) |
| **FR-56** | CSRF token on every POST | The system shall reject every POST that does not carry the session's token: nothing shall change and the user shall be sent back with a message. | All users | Must | `check_csrf` (app/__init__.py:71), `validators.csrf_token_is_valid` (validators.py:27) |
| **FR-57** | Demo data | The system shall provide `seed.py`, which resets the database and loads the demo users, the settings and loans in every status, including one Repaying loan with an overdue installment. | System | Must | `seed.py` |
| **FR-58** | Landing page | The system shall show a public landing page that explains the service, shows the current limits and a sample EMI from the live settings, and links to Register and Login. | Visitor | Should | `GET /` · `main.index` (main.py:14) |


There are 58 functional requirements: all are implemented. Requirements with priority *Must* are needed for the
demonstration script of the blueprint (apply, review, approve, disburse, repay, close).

---

## 5. Business rules

| Rule | Statement | Requirement | Where enforced |
|---|---|---|---|
| **R1** | Amount between the minimum and the maximum, at most 2 decimal places | FR-11 | `check_application` |
| **R2** | Tenure between the minimum and the maximum, whole months | FR-12 | `check_application` |
| **R3** | One active loan at a time | FR-13 | `check_application`, `User.has_active_loan` |
| **R4** | EMI at most the set share of monthly income; show the maximum affordable amount | FR-14 | `check_affordability` |
| **R5** | Reducing-balance EMI, rounded to 2 decimals; last installment adjusted | FR-15, FR-34 | `calculate_emi`, `build_schedule` |
| **R6** | Interest rate locked when the application is made | FR-16, FR-44 | `apply_for_loan` |
| **R7** | Schedule created only at disbursal, due on disbursal date plus i months (month-end safe) | FR-28, FR-34 | `disburse_loan`, `add_months` |
| **R8** | Only the earliest Pending installment can be paid | FR-35 | `pay_installment` |
| **R9** | Overdue = Pending and past the due date (computed, red badge, no late fee) | FR-38, FR-51 | `Repayment.is_overdue` |
| **R10** | One document, PDF/JPG/PNG, at most 2 MB, content matches the type, renamed with a uuid | FR-17, FR-52 | `check_document` |
| **R11** | After pick-up only the assigned officer may approve, reject or disburse; an admin may reassign | FR-24 to FR-28, FR-30 | `change_status`, `reassign_loan` |

---

## 6. Data requirements

Five tables (`app/models.py`). Details are in the class diagram (diagram 3 in `02_diagrams.md`).

| Table | Purpose | Main fields |
|---|---|---|
| `User` | Everyone who can log in | name, email (unique, lower case), phone, password_hash, role, monthly_income, is_active, created_at |
| `Loan` | One application and its life | borrower_id, officer_id, amount, tenure_months, interest_rate (locked), emi_amount, purpose, status, remarks, applied_on, reviewed_on, disbursed_on, closed_on |
| `Repayment` | One EMI installment | loan_id, installment_no, due_date, amount, status (Pending or Paid), paid_on |
| `Document` | The one supporting file of a loan | loan_id, original_name, stored_name, uploaded_on |
| `LoanSetting` | The one settings row (id 1) | interest_rate, min_amount, max_amount, min_tenure, max_tenure, max_emi_to_income, updated_at |

**Loan statuses and allowed changes** (enforced by FR-29; see the state diagram):

| From | To | Who | Extra rule |
|---|---|---|---|
| Applied | Cancelled | the owning borrower | - |
| Applied | Under Review | any officer | saves the officer |
| Under Review | Approved | the assigned officer | saves the review date |
| Under Review | Rejected | the assigned officer | remarks required |
| Approved | Disbursed | the assigned officer | creates the schedule |
| Disbursed | Repaying | system | on the first payment |
| Repaying | Closed | system | when no installment is Pending |

Reassignment (FR-30) is not a status change: it changes only `Loan.officer_id` for a loan that is Under Review or Approved.

---

## 7. Non-functional requirements

Every requirement has a number that can be checked. The last column names the automated test module (section 8 and
`tests/`); "-" means the check is manual.

**Mapping to the blueprint.** `CLAUDE.md` section 10 lists NFR1 to NFR12. In this document they are NFR-01 to NFR-05 (same order), NFR-07 (blueprint NFR6, performance), NFR-08 (NFR7), NFR-09 (NFR8), NFR-10 (NFR9), NFR-11 (NFR10), NFR-12 (NFR11) and NFR-13 (NFR12). NFR-06 (cookie), NFR-14 (visual consistency), NFR-15 (responsiveness) and NFR-16 (testability) are new.

| ID | Category | Requirement | Acceptance criterion (measurable) | How verified | Test |
|---|---|---|---|---|---|
| **NFR-01** | Security | Passwords are stored only as salted hashes and are never shown or logged. | 0 plain-text passwords in the database; `password_hash` is not equal to the typed password; no response page contains a typed password. | Automated: check the stored hash and scan the response bodies of register and login. | test_auth.py |
| **NFR-02** | Security | Every protected route checks the role. | For each of the 22 routes, every role that is not allowed gets 403 (or the login page when not logged in): 100 % of route and role combinations. | Automated: route x role matrix. | test_permissions.py |
| **NFR-03** | Security | Users see only their own loans and documents. | A borrower who asks for another borrower's loan, payment, cancellation or document gets 404 in all cases; 0 leaks. | Automated: two borrowers, cross requests. | test_permissions.py |
| **NFR-04** | Security | A CSRF token is required on every POST. | Each of the 11 POST routes (including logout and reassign) rejects a request without the token and leaves the data unchanged. | Automated: send each POST without a token and compare the database. | test_security.py |
| **NFR-05** | Security | Uploads are restricted by type, content and size, and files are not publicly reachable. | Only PDF, JPG or PNG of at most 2 MB whose first bytes match are saved; a renamed text file is refused; `/static/<stored name>` and `/uploads/<stored name>` answer 404. | Automated: accepted and refused samples, and URL probes. | test_uploads.py |
| **NFR-06** | Security | The session cookie is protected. | The session `Set-Cookie` header contains `SameSite=Lax` and `HttpOnly`; `GET /logout` answers 405. | Automated: read the header after login. | test_security.py |
| **NFR-07** | Performance | Pages load quickly on a local machine with the seed data. | Each of the 20 main pages answers in under 2 seconds (server time, test client). | Automated: time every page. | test_performance.py |
| **NFR-08** | Usability | Any core task is reachable in at most 3 clicks from the dashboard. | The click paths in Appendix A: 3 clicks or fewer for all 12 core tasks. | Manual walk-through of Appendix A, backed by an automated check that the links exist on the dashboards. | test_ui.py |
| **NFR-09** | Reliability | Invalid status changes are impossible. | Of the 384 combinations of (from status, to status, actor) exactly the 8 allowed cases succeed; the other 376 raise `LoanError` and change nothing. | Automated: try all combinations. | test_state_machine.py |
| **NFR-10** | Data integrity | One action is saved in one commit, or not at all. | If the commit fails, the database is unchanged, the user sees an error (not a half-saved loan), and a just-saved upload file is removed. | Automated: force the commit to fail. | test_security.py |
| **NFR-11** | Maintainability | Business rules live in the service layer. | 0 occurrences of `loan.status =` or a loan `commit()` in `app/routes/`; every status change goes through `change_status`. | Automated source scan. | test_architecture.py |
| **NFR-12** | Portability | The system runs with only Python and `pip install -r requirements.txt`. | Fresh virtual environment, install, `python seed.py`, `python run.py`: the landing page opens. Tested on Windows only; Mac and Linux are not verified. | Manual on Windows (README steps). | - |
| **NFR-13** | Accuracy | EMI and schedule totals are exact to the paisa. | For rates 0, 12 and 14 % and tenures 3 to 24, the installments add up to exactly EMI x n; 50,000 for 12 months at 12 % gives 4,442.44. | Automated: loop over rates, tenures and amounts. | test_emi.py |
| **NFR-14** | Visual consistency and accessibility | The yellow-and-blue design follows its rules. | Body text contrast at least 4.5 to 1 (WCAG AA); at most one enabled yellow primary button per page; the same colour for the same status everywhere. | Automated: count the yellow buttons on every page; contrast measured with the dataviz validator and the colour tokens. | test_ui.py |
| **NFR-15** | Responsiveness | The pages work on a phone. | At 390 px width no page scrolls sideways (document width is not more than the window width). **Status: not met on 2 of the 15 pages measured** (Officer dashboard: 594 px wide; My loans: 655 px wide); the other 13 measured exactly 390 px. See section 9. | Measured on the prototype screenshots (`docs/prototype/`, widths read in headless Edge) and checked by eye. | - |
| **NFR-16** | Testability | The automated tests run with one command and never touch the live data. | `pytest` passes completely against a temporary database and a temporary upload folder. | Run before every release. | all tests |

---

## 8. Traceability matrix

Each requirement is traced forward to the route and function that implements it, the diagram that shows it (the numbers
are those of [02_diagrams.md](02_diagrams.md): 1 to 1c use case, 2 and 2b activity, 3 and 3b class, 4 and 4b state, 5 and 5b
swimlane, 6 to 6g data flow, 7 to 7e sequence) and the test module that checks it. The test modules are in `tests/`.

| Requirement | Route and function | Diagram | Test (`tests/`) |
|---|---|---|---|
| Requirement | Route and function | Diagram (`02_diagrams.md`) | Test (`tests/`) |
|---|---|---|---|
| FR-01 Borrower self-registration | `GET/POST /register` · `auth.register` (auth.py:14) → `loan_service.create_user` (loan_service.py:84) | 1a, 7 | test_auth.py |
| FR-02 Registration validation | `validators.validate_user_form` (validators.py:109) | 7 | test_auth.py |
| FR-03 Unique email | `validate_user_form` (validators.py:109), `create_user` catches `IntegrityError` (loan_service.py:98) | 7 | test_auth.py |
| FR-04 Login | `GET/POST /login` · `auth.login` (auth.py:32) | 1, 7 | test_auth.py |
| FR-05 Role-based redirect | `auth.login`, `decorators.dashboard_url` (decorators.py:26) | 7 | test_auth.py |
| FR-06 Deactivated accounts are blocked | `auth.login` (auth.py:32), `models.load_user` (models.py:132) | 1c, 7 | test_auth.py |
| FR-07 Logout as POST | `POST /logout` · `auth.logout` (auth.py:54) | 7 | test_auth.py, test_security.py |
| FR-08 Role-based access | `decorators.role_required` (decorators.py:10) | 1 | test_permissions.py |
| FR-09 Ownership | `borrower.loan_detail` (borrower.py:64), `borrower.pay` (borrower.py:72), `borrower.cancel` (borrower.py:87), `main.view_document` (main.py:22) | 1a | test_permissions.py |
| FR-10 Apply form with live EMI preview | `GET/POST /borrower/apply` · `borrower.apply` (borrower.py:33), `static/js/main.js` | 2, 5, 7b | test_rules.py, test_demo_flow.py |
| FR-11 Amount limits and decimals (R1) | `loan_service.check_application` (loan_service.py:158), `validators.has_too_many_decimals` (validators.py:45) | 2, 7b | test_rules.py |
| FR-12 Tenure limits (R2) | `check_application` (loan_service.py:158) | 2 | test_rules.py |
| FR-13 One active loan at a time (R3) | `check_application` (loan_service.py:158), `User.has_active_loan` (models.py:38) | 2 | test_rules.py |
| FR-14 Affordability (R4) | `check_affordability` (loan_service.py:144), `emi.max_affordable_amount` (emi.py:16) | 2, 6d | test_rules.py |
| FR-15 EMI calculation (R5) | `emi.calculate_emi` (emi.py:7) | 3b, 7b | test_emi.py |
| FR-16 Interest rate locked (R6) | `loan_service.apply_for_loan` (loan_service.py:194) | 2, 7b | test_rules.py |
| FR-17 Supporting document (R10) | `check_document` (loan_service.py:110), `detect_file_type` (loan_service.py:133), `apply_for_loan` (loan_service.py:194) | 2, 7b | test_uploads.py |
| FR-18 Purpose | `check_application` (loan_service.py:158) | 2 | test_rules.py |
| FR-19 Cancel own application | `POST /borrower/loans/<id>/cancel` · `borrower.cancel` (borrower.py:87) → `loan_service.cancel_loan` (loan_service.py:230) | 1a, 4, 5 | test_state_machine.py, test_demo_flow.py |
| FR-20 My loans and loan details | `borrower.loans` (borrower.py:56), `borrower.loan_detail` (borrower.py:64) | 1a | test_demo_flow.py, test_ui.py |
| FR-21 Apply button state | `macros.apply_button` (macros.html), `borrower.dashboard` (borrower.py:25), `borrower.loans` (borrower.py:56) | 1a | test_ui.py |
| FR-22 Applications list | `GET /officer/applications` · `officer.applications` (officer.py:28) → `loan_service.search_loans` (loan_service.py:242) | 1b | test_officer_flow.py |
| FR-23 Application detail | `GET /officer/applications/<id>` · `officer.application_detail` (officer.py:41) | 2b | test_officer_flow.py |
| FR-24 Pick up | `POST /officer/applications/<id>/pickup` · `officer.application_action` (officer.py:69) → `pick_up_loan` (loan_service.py:270) | 1b, 4, 5, 7c | test_officer_flow.py |
| FR-25 Approve | `application_action` (officer.py:69) → `approve_loan` (loan_service.py:281) | 1b, 4, 5, 7c | test_officer_flow.py |
| FR-26 Reject with remarks | `application_action` (officer.py:69) → `reject_loan` (loan_service.py:295) | 1b, 4, 5 | test_officer_flow.py |
| FR-27 Officer ownership (R11) | `change_status` (loan_service.py:41), `application_detail.html` | 2b, 5 | test_state_machine.py, test_officer_flow.py |
| FR-28 Disburse | `application_action` (officer.py:69) → `disburse_loan` (loan_service.py:311) | 1b, 4, 5, 7c | test_officer_flow.py, test_demo_flow.py |
| FR-29 One state machine | `ALLOWED_TRANSITIONS`, `change_status` (loan_service.py:41) | 4, 7c | test_state_machine.py |
| FR-30 Admin reassignment | `POST /officer/applications/<id>/reassign` · `officer.reassign_application` (officer.py:53) → `loan_service.reassign_loan` (loan_service.py:343) | 1c, 2b, 5, 7e | test_reassignment.py |
| FR-31 Reassign form | `officer.application_detail` (officer.py:41), `active_officers` (loan_service.py:330), `application_detail.html` | 1c, 7e | test_reassignment.py |
| FR-32 Deactivation notice | `admin.toggle_user` (admin.py:59), `pending_loan_count` (loan_service.py:338) | 1c | test_reassignment.py |
| FR-33 Admin read-only view | `officer.applications`, `officer.application_detail`; `application_action` is `role_required("officer")` (officer.py:69) | 1c | test_permissions.py |
| FR-34 EMI schedule at disbursal | `emi.build_schedule` (emi.py:36), `emi.add_months` (emi.py:27), `disburse_loan` (loan_service.py:311) | 5, 6f | test_emi.py |
| FR-35 Pay in order (R8) | `POST /borrower/loans/<id>/pay` · `borrower.pay` (borrower.py:72) → `loan_service.pay_installment` (loan_service.py:363) | 1a, 5b, 7d | test_repayment.py |
| FR-36 Repaying | `pay_installment` (loan_service.py:363) | 4, 5b | test_repayment.py |
| FR-37 Automatic closing | `pay_installment` (loan_service.py:363) | 4, 5, 5b | test_repayment.py |
| FR-38 Overdue (R9) | `Repayment.is_overdue` (models.py:103), `macros.schedule_table` | 1a, 4b | test_repayment.py |
| FR-39 Consistent status badges | `macros.status_badge` (macros.html) | - | test_ui.py |
| FR-40 List and search users | `GET /admin/users` · `admin.users` (admin.py:33) → `search_users` (loan_service.py:404) | 1c | test_admin.py |
| FR-41 Activate or deactivate a user | `POST /admin/users/<id>/toggle` · `admin.toggle_user` (admin.py:59) → `toggle_user_active` (loan_service.py:415) | 1c | test_admin.py |
| FR-42 Create officer | `GET/POST /admin/users/new-officer` · `admin.new_officer` (admin.py:44) → `create_user` | 1c | test_admin.py |
| FR-43 Loan settings | `GET/POST /admin/settings` · `admin.settings` (admin.py:79), `validate_settings_form` (validators.py:67), `update_settings` (loan_service.py:427) | 1c | test_admin.py, test_rules.py |
| FR-44 Settings apply to new loans only | `apply_for_loan` (loan_service.py:194), `main.index` (main.py:14) | 2 | test_rules.py, test_demo_flow.py |
| FR-45 Admin accounts only by seed | `seed.py`, `auth.register` (always borrower) | 1 | test_seed.py, test_auth.py |
| FR-46 Borrower dashboard | `borrower.dashboard` (borrower.py:25) → `borrower_summary` (loan_service.py:388) | 1a | test_ui.py |
| FR-47 Officer dashboard | `officer.dashboard` (officer.py:20) → `officer_summary` (loan_service.py:257) | 1b | test_officer_flow.py |
| FR-48 Admin dashboard | `admin.dashboard` (admin.py:26) → `admin_totals` (loan_service.py:449) | 1c | test_reports.py |
| FR-49 Loans-by-status chart and table | `admin.reports` (admin.py:97), `loan_service.percent_shares` (loan_service.py:469) | 1c | test_reports.py |
| FR-50 Disbursed per month chart | `disbursed_per_month` (loan_service.py:479) | 1c | test_reports.py |
| FR-51 Overdue installments table | `overdue_installments` (loan_service.py:443) | 1c | test_reports.py |
| FR-52 View a document | `GET /documents/<id>` · `main.view_document` (main.py:22) | 1, 7b | test_uploads.py, test_permissions.py |
| FR-53 Formats | `formatters.inr` (formatters.py:4), `format_date` (formatters.py:27) | - | test_ui.py |
| FR-54 Confirm dialogs | templates `loan_detail.html`, `application_detail.html`, `macros.schedule_table` | 5b | test_ui.py |
| FR-55 Empty states and error pages | `macros.empty_state`, `register_error_handlers` (app/__init__.py:80) | - | test_ui.py, test_security.py |
| FR-56 CSRF token on every POST | `check_csrf` (app/__init__.py:71), `validators.csrf_token_is_valid` (validators.py:27) | 7 | test_security.py |
| FR-57 Demo data | `seed.py` | - | test_seed.py |
| FR-58 Landing page | `GET /` · `main.index` (main.py:14) | 1 | test_ui.py |
| NFR-01 Security: Passwords are stored only as salted hashes and are never shown or logged | `User.set_password` (models.py:30), `check_password` (models.py:34) | 3 | test_auth.py |
| NFR-02 Security: Every protected route checks the role | `role_required` (decorators.py:10) | 1 | test_permissions.py |
| NFR-03 Security: Users see only their own loans and documents | ownership checks in `borrower.py`, `main.view_document` | 1a, 7e | test_permissions.py |
| NFR-04 Security: A CSRF token is required on every POST | `check_csrf` (app/__init__.py:71) | 7 | test_security.py |
| NFR-05 Security: Uploads are restricted by type, content and size, and files are not publicly reachable | `check_document` (loan_service.py:110), `config.py` (MAX_CONTENT_LENGTH) | 2, 7b | test_uploads.py |
| NFR-06 Security: The session cookie is protected | `config.py` (SESSION_COOKIE_*) | 7 | test_security.py |
| NFR-07 Performance: Pages load quickly on a local machine with the seed data | all routes | - | test_performance.py |
| NFR-08 Usability: Any core task is reachable in at most 3 clicks from the dashboard | dashboards and navbar (`base.html`) | 1a, 1b, 1c | test_ui.py |
| NFR-09 Reliability: Invalid status changes are impossible | `ALLOWED_TRANSITIONS`, `change_status` (loan_service.py:41) | 4 | test_state_machine.py |
| NFR-10 Data integrity: One action is saved in one commit, or not at all | one `commit()` with `rollback()` in every service function | 7b, 7c, 7d, 7e | test_security.py |
| NFR-11 Maintainability: Business rules live in the service layer | `app/services/loan_service.py` | 3b | test_architecture.py |
| NFR-12 Portability: The system runs with only Python and `pip install -r requirements.txt` | `requirements.txt`, `README.md` | - | - |
| NFR-13 Accuracy: EMI and schedule totals are exact to the paisa | `emi.calculate_emi`, `emi.build_schedule` | 3b | test_emi.py |
| NFR-14 Visual consistency and accessibility: The yellow-and-blue design follows its rules | `static/css/style.css`, `macros.html` | - | test_ui.py |
| NFR-15 Responsiveness: The pages work on a phone | `static/css/style.css` | - | - |
| NFR-16 Testability: The automated tests run with one command and never touch the live data | `tests/` | - | all tests |

**Reverse check.** Every one of the 22 routes appears in the "Route and function" column of at least one requirement:
`/`, `/documents/<id>`, `/register`, `/login`, `/logout`, the six borrower routes, the five officer routes (including
`reassign`) and the six admin routes.

---

## 9. Changes after the first audit (Parts 1 and 2)

| Change | Requirement | What changed |
|---|---|---|
| Part 1a | FR-21 | "Apply for loan" on My loans now looks and behaves like the dashboard's disabled button, with the same helper text |
| Part 1b | FR-49 | The pie chart's "View as table" shows shares with one decimal that add up to exactly 100.0 % |
| Part 2a | FR-11, FR-43 | More than 2 decimal places are refused for the amount and the amount limits |
| Part 2b | FR-17, NFR-05 | The first bytes of an upload must match PDF, PNG or JPEG |
| Part 2c | FR-30, FR-31, FR-32 | Admin reassignment of an application, and a warning when a deactivated officer still holds loans |
| Part 2d | FR-03 | A duplicate email that slips past the check shows the form error, not a 500 page |
| Part 2e | NFR-06 | `SameSite=Lax` and `HttpOnly` session cookie |
| Part 2f | FR-07 | Logout is POST only, with the CSRF token |

**Known issue found while taking the prototype screenshots (not fixed, needs the owner's go-ahead):** at 390 px width the Officer dashboard and the borrower's My loans page are wider than the screen (594 px and 655 px), so the browser widens the layout and the last table columns are cut off until swiped; NFR-15 is therefore **not met on those two pages**. Cause: a visually hidden label inside the scrolling table is absolutely positioned and escapes the table wrapper. Suggested fix: one CSS line, `position: relative` on `.table-responsive`. **A second finding:** the shield icon in the utility bar of `base.html` has no `aria-hidden="true"`, so NFR-14 (accessibility) has one known exception; a strict expected-failure test (`tests/test_ui.py`) records it.

**Known limitations** (honest list): money is stored as floating point; the monthly income is not checked for decimals;
no database migrations; no pagination; simultaneous requests are not tested; SQLite foreign keys are not enforced; the
status history is not stored as rows (only the current status and dates); no rate limiting or account lockout; tested on
Windows only.

---

## Appendix A. Click paths for NFR-08

Counted from the role's dashboard; the last click is the action button.

| Task | Start | Click 1 | Click 2 and 3 | Clicks |
|---|---|---|---|--:|
| Apply for a loan | Borrower dashboard | Apply for loan | Submit | 2 |
| View the EMI schedule | Borrower dashboard | View details on the loan card | - | 1 |
| Pay an installment | Borrower dashboard | View details | Pay | 2 |
| Cancel an application | Borrower dashboard | View details | Cancel | 2 |
| Pick up an application | Officer dashboard | Applications | open the application, then Pick up | 3 |
| Approve or reject | Officer dashboard | the application in My pending work | Approve or Reject | 2 |
| Disburse a loan | Officer dashboard | the application in My pending work | Disburse | 2 |
| Reassign an application | Admin dashboard | Applications | open the application, then Reassign | 3 |
| Create an officer | Admin dashboard | Users | Create officer, then Save | 3 |
| Deactivate a user | Admin dashboard | Users | Deactivate | 2 |
| Change loan settings | Admin dashboard | Settings | Save settings | 2 |
| View reports | Admin dashboard | Reports | - | 1 |

All 12 core tasks need 3 clicks or fewer.
