# MicroLoan: wireframes and prototype

Part of the software engineering documentation. Requirements are in [01_SRS_requirements.md](01_SRS_requirements.md), diagrams in [02_diagrams.md](02_diagrams.md).

This file has four parts: **navigation maps** (how the pages connect for each role), **wireframes** (the planned layout of the 11 key pages, in grey, with numbered elements), the **prototype** (screenshots of the real running pages) and **from wireframe to prototype** (what the design added, and why, using the Laws of UX).

## How to read the wireframes

- Files are grayscale SVG in `docs/wireframes/` (they scale without loss; open them in a browser to zoom). Desktop wireframes are 1200 px wide; the two phone wireframes are 390 px wide.
- A **black disc with a number** marks an element. The numbers in the list under each wireframe are the same as in the drawing.
- **Dark filled box = the primary action** (it is the yellow button in the finished design, so the wireframe stays grey). **White box with a dark border = secondary action.** **Dashed grey = disabled.** **Dashed dark outline = an error state** (shown so that the messages can be planned).
- Every wireframe lists the page's purpose, who uses it, the numbered elements, the validation and messages, and where the buttons go. The requirement numbers (FR-xx, NFR-xx) point to the SRS.

| # | Page | Wireframe (desktop) | Phone wireframe | Prototype screenshots |
|--:|---|---|---|---|
| 1 | Landing page | [01_landing_desktop.svg](wireframes/01_landing_desktop.svg) | - | [desktop](prototype/01_landing_desktop.png), [phone](prototype/01_landing_phone.png) |
| 2 | Register | [02_register_desktop.svg](wireframes/02_register_desktop.svg) | - | [desktop](prototype/02_register_desktop.png), [phone](prototype/02_register_phone.png) |
| 3 | Login | [03_login_desktop.svg](wireframes/03_login_desktop.svg) | - | [desktop](prototype/03_login_desktop.png), [phone](prototype/03_login_phone.png) |
| 4 | Borrower dashboard | [04_borrower_dashboard_desktop.svg](wireframes/04_borrower_dashboard_desktop.svg) | [04_borrower_dashboard_phone.svg](wireframes/04_borrower_dashboard_phone.svg) | [desktop](prototype/04_borrower_dashboard_desktop.png), [phone](prototype/04_borrower_dashboard_phone.png) |
| 5 | Apply for a loan | [05_apply_desktop.svg](wireframes/05_apply_desktop.svg) | - | [desktop](prototype/05_apply_desktop.png), [phone](prototype/05_apply_phone.png) |
| 6 | Loan details and EMI schedule | [06_loan_details_desktop.svg](wireframes/06_loan_details_desktop.svg) | [06_loan_details_phone.svg](wireframes/06_loan_details_phone.svg) | [desktop](prototype/06_loan_details_desktop.png), [phone](prototype/06_loan_details_phone.png) |
| 7 | Officer dashboard | [07_officer_dashboard_desktop.svg](wireframes/07_officer_dashboard_desktop.svg) | - | [desktop](prototype/07_officer_dashboard_desktop.png), [phone](prototype/07_officer_dashboard_phone.png) |
| 8 | Application detail (officer) | [08_application_detail_desktop.svg](wireframes/08_application_detail_desktop.svg) | - | [desktop](prototype/08_application_detail_desktop.png), [phone](prototype/08_application_detail_phone.png) |
| 9 | Admin dashboard | [09_admin_dashboard_desktop.svg](wireframes/09_admin_dashboard_desktop.svg) | - | [desktop](prototype/09_admin_dashboard_desktop.png), [phone](prototype/09_admin_dashboard_phone.png) |
| 10 | Loan settings | [10_loan_settings_desktop.svg](wireframes/10_loan_settings_desktop.svg) | - | [desktop](prototype/10_loan_settings_desktop.png), [phone](prototype/10_loan_settings_phone.png) |
| 11 | Reports | [11_reports_desktop.svg](wireframes/11_reports_desktop.svg) | - | [desktop](prototype/11_reports_desktop.png), [phone](prototype/11_reports_phone.png) |
| 12 | Application detail, admin view with Reassign (prototype only) | - | - | [desktop](prototype/12_admin_reassign_desktop.png), [phone](prototype/12_admin_reassign_phone.png) |

---

## 1. Navigation maps

One map per role. Boxes are pages, arrows are the buttons or links that lead from one to another; every state-changing action is a POST that returns to a page. Each role reaches any core task in at most 3 clicks from its dashboard (SRS Appendix A).

### Visitor

<!-- diagram: 08_navigation_visitor -->
```mermaid
flowchart LR
  L["Landing page /"] -->|"Apply for loan, Register"| R["Register /register"]
  L -->|"Login"| LG["Login /login"]
  R -->|"Create account (all fields valid)"| BD["Borrower dashboard"]
  R -->|"Login link"| LG
  LG -->|"borrower"| BD
  LG -->|"loan officer"| OD["Officer dashboard"]
  LG -->|"admin"| AD["Admin dashboard"]
  LG -->|"Register link"| R
```

*File: `diagrams/08_navigation_visitor.png` and `.svg`.*

### Borrower

<!-- diagram: 08b_navigation_borrower -->
```mermaid
flowchart LR
  D["Dashboard"] -->|"Apply for loan (only without an active loan)"| A["Apply for a loan"]
  D -->|"View details, See the schedule"| LD["Loan details"]
  D -->|"My loans"| LS["My loans"]
  LS -->|"a loan"| LD
  A -->|"Submit (valid)"| LD
  A -->|"Back"| D
  LD -->|"Pay (earliest pending installment)"| LD
  LD -->|"Cancel (only while Applied)"| LD
  LD -->|"View document"| DOC["Document (new tab)"]
  D -->|"Logout (POST)"| H["Landing page"]
```

*File: `diagrams/08b_navigation_borrower.png` and `.svg`.*

### Loan officer

<!-- diagram: 08c_navigation_officer -->
```mermaid
flowchart LR
  D["Dashboard"] -->|"Open"| AD["Application detail"]
  D -->|"New applications"| AL["Applications list"]
  AL -->|"a row (filter by status, search)"| AD
  AD -->|"Pick up, Approve, Reject, Disburse"| AD
  AD -->|"View document"| DOC["Document (new tab)"]
  AD -->|"Breadcrumb"| AL
  D -->|"Logout (POST)"| H["Landing page"]
```

*File: `diagrams/08c_navigation_officer.png` and `.svg`.*

### Admin

<!-- diagram: 08d_navigation_admin -->
```mermaid
flowchart LR
  D["Dashboard"] --> U["Users"]
  D --> AL["Applications list"]
  D --> S["Loan settings"]
  D --> R["Reports"]
  U -->|"Create officer"| NO["New officer"]
  NO -->|"Save"| U
  U -->|"Activate or deactivate"| U
  AL --> AD["Application detail (read-only)"]
  AD -->|"Reassign"| AD
  AD -->|"View document"| DOC["Document (new tab)"]
  R -->|"loan number"| AD
  S -->|"Save settings"| S
  D -->|"Logout (POST)"| H["Landing page"]
```

*File: `diagrams/08d_navigation_admin.png` and `.svg`.*

---

## 2. Wireframes

### Wireframe 1: Landing page

| Route | User | Requirements |
|---|---|---|
| `GET /` | Visitor (not logged in) | FR-58, FR-01 |

**Purpose.** Explain the service in one scroll and send the visitor to Register or Login. It shows the real limits and a sample EMI taken from the live loan settings, so the page never contradicts the apply form.

![Wireframe of the landing page (desktop)](wireframes/01_landing_desktop.svg)

**Numbered elements.**

1. Utility strip: demo notice and a Register link for visitors.
2. Header: logo, section links (How it works, Why MicroLoan, Step by step) and the Login and Register buttons.
3. Headline and one-sentence promise.
4. Hero buttons: Apply for loan (the one primary action; goes to Register or Login first) and Login.
5. Example loan card: sample EMI worked out from the live settings (reducing balance).
6. Facts strip: amount range, tenure range, interest rate and EMI limit, read from the loan settings.
7. How it works: three numbered steps (apply, get approved, repay).
8. Why MicroLoan: four short benefit cards.
9. Status chips: the lifecycle Applied to Closed, and the two other outcomes, with the same badge style as the rest of the site.
10. Closing call to action with one primary button (Create your account).
11. Footer with the project note: demo only, no real money, payments are simulated.

**Validation and messages.**

- No form on this page.
- A flash message (for example "You have been logged out.") appears under the header.

**Where the buttons go.**

- The one primary (yellow) button is **Apply for loan** in the hero (element 4), plus the closing band button (element 10); the header Login and Register buttons are outlined so that the hero button stays the main action (law of focus).
- Logged-in users never see this page's buttons as actions: they are redirected where needed by the dashboards.

---

### Wireframe 2: Register

| Route | User | Requirements |
|---|---|---|
| `GET/POST /register` | Visitor (not logged in) | FR-01, FR-02, FR-03, FR-56 |

**Purpose.** Let a visitor become a borrower. The account is always a borrower; nobody can choose a role here.

![Wireframe of the register (desktop)](wireframes/02_register_desktop.svg)

**Numbered elements.**

1. Header: only a Login link (the page already is the registration).
2. Side panel: why register, three benefits.
3. Full name (required, at most 100 characters).
4. Email (valid form, unique, saved in lower case).
5. Phone: exactly 10 digits.
6. Monthly income in rupees (must be greater than 0); used later for the affordability check.
7. Password: at least 8 characters with a letter and a number.
8. Confirm password: must match.
9. Create account: the one primary action.
10. Link to Login for people who already have an account.

**Validation and messages.**

- Each wrong field gets a message under it and keeps what was typed (the wireframe shows the possible messages in dashed boxes).
- Name required and at most 100 characters; email in a valid form and not already registered ("This email is already registered.", also when two sign-ups race); phone exactly 10 digits; monthly income greater than 0; password at least 8 characters with a letter and a digit; confirmation must match.
- Password fields are never filled in again after an error.

**Where the buttons go.**

- **Create account** is the only primary button, full width, directly under the last field.
- Login link below it (secondary, text link).

---

### Wireframe 3: Login

| Route | User | Requirements |
|---|---|---|
| `GET/POST /login` | Visitor (not logged in) | FR-04, FR-05, FR-06 |

**Purpose.** Sign in with email and password; each role is sent to its own dashboard.

![Wireframe of the login (desktop)](wireframes/03_login_desktop.svg)

**Numbered elements.**

1. Header: Register link (the page already is the login).
2. Side panel with the welcome text.
3. Message area: shows one message at a time.
4. Email (not case sensitive).
5. Password.
6. Login: the one primary action. After success every role goes to its own dashboard.
7. Link to Register.

**Validation and messages.**

- Wrong email or wrong password both show "Invalid email or password." (the page does not reveal which one was wrong).
- A deactivated account shows "Your account has been deactivated. Please contact the admin."
- The typed email stays in the box after a failed attempt; the password does not.

**Where the buttons go.**

- **Login** is the only primary button, full width under the password.
- Register is a text link below it.

---

### Wireframe 4: Borrower dashboard

| Route | User | Requirements |
|---|---|---|
| `GET /borrower/dashboard` | Borrower | FR-46, FR-21, FR-35, FR-38 |

**Purpose.** Show where the borrower's loan stands and the one thing to do next (pay the next installment, or apply).

![Wireframe of the borrower dashboard (desktop)](wireframes/04_borrower_dashboard_desktop.svg)

**Numbered elements.**

1. Navigation for a borrower: Dashboard, Apply for loan, My loans. The current page has the thick underline.
2. Greeting and one line of context.
3. Apply for loan. Disabled with a helper line while a loan is active; enabled (primary) when the borrower has no active loan.
4. Overdue alert (only when an installment is overdue) with a link to the schedule.
5. Active loan card header: loan number and status badge.
6. Pay installment: the one primary action on this page (the next installment, in order).
7. Progress bar: installments paid out of the total.
8. Three figures: paid so far, outstanding, total payable.
9. Quick links to the schedule and to all loans.
10. Recent payments (latest three).

**Validation and messages.**

- No form. Messages: the overdue alert (element 4), and flash messages after a payment ("Installment 4 paid.") or an error ("Pay the earliest pending installment first.").
- Without any loan the card is replaced by an empty state with an enabled **Apply for loan** button.

**Where the buttons go.**

- Exactly one enabled primary button: **Pay installment** when a payment is due, otherwise **Apply for loan** (never both).
- While a loan is active, **Apply for loan** is disabled with the text "Available again once your current loan is closed." (the same on My loans).

**Phone layout (390 px).** The same dashboard on a phone: one column, the navigation behind a menu button, full-width buttons.

![Wireframe of the borrower dashboard (phone)](wireframes/04_borrower_dashboard_phone.svg)

Numbered elements of the phone layout:

1. Menu button: the navigation collapses into one button on a phone.
2. Greeting; all content is one column.
3. Apply for loan: full width and disabled while a loan is active (same helper text as on the desktop).
4. Overdue alert.
5. Active loan card: loan number and badge.
6. Pay installment: full width primary button, easy to hit with a thumb.
7. Progress bar of installments paid.
8. Quick links and recent payments move below the loan card.

- The primary **Pay installment** button becomes full width; the Apply button stays disabled with its helper text.

---

### Wireframe 5: Apply for a loan

| Route | User | Requirements |
|---|---|---|
| `GET/POST /borrower/apply` | Borrower with no active loan | FR-10 to FR-18, FR-21 |

**Purpose.** Collect an application and show the EMI before it is submitted, so the borrower knows the cost first.

![Wireframe of the apply for a loan (desktop)](wireframes/05_apply_desktop.svg)

**Numbered elements.**

1. Breadcrumb back to the dashboard.
2. Title and one line of help.
3. Current limits, read from the loan settings.
4. Loan amount in rupees: within the limits, at most 2 decimals.
5. Tenure in whole months within the limits.
6. Purpose (required, at most 200 characters).
7. Supporting document: exactly one PDF, JPG or PNG, up to 2 MB; the content must match the type.
8. Submit application: the one primary action.
9. EMI preview: recalculated in the browser while the borrower types, no server call.
10. Affordability line: green when the EMI is within the limit, an error with the largest affordable amount otherwise.

**Validation and messages.**

- All problems are shown together, each under its field, and the typed values are kept (the file must be chosen again). The wireframe shows one error in a dashed box.
- Amount: "Amount must be between ₹5,000.00 and ₹1,00,000.00." or "Use at most 2 decimal places."; the affordability error also names the largest amount the borrower can afford.
- Tenure: whole months within the limits. Purpose: required, at most 200 characters.
- Document: "Only PDF, JPG or PNG files are allowed.", "The file is empty.", "The file is larger than 2 MB.", or the content does not match the type.
- A borrower with an active loan is sent back to the dashboard with the message that an active loan exists.

**Where the buttons go.**

- **Submit application** is the only primary button, under the document field; **Back** is a text link beside it.

---

### Wireframe 6: Loan details and EMI schedule

| Route | User | Requirements |
|---|---|---|
| `GET /borrower/loans/<id>` | Borrower (owner of the loan) | FR-20, FR-19, FR-34 to FR-38, FR-52 |

**Purpose.** Let the borrower follow one loan from application to the last payment and pay the next installment.

![Wireframe of the loan details and emi schedule (desktop)](wireframes/06_loan_details_desktop.svg)

**Numbered elements.**

1. Breadcrumb: Dashboard, My loans, this loan.
2. Loan number and status badge; **Cancel application** (outline) is shown only while the status is Applied.
3. Step tracker: completed steps ticked, the current step highlighted.
4. Officer remarks (shown once the officer wrote some).
5. Loan details card: amount, tenure, locked rate, EMI, total payable, purpose, document link.
6. Status updates: dates and the officer who reviewed it.
7. Repayment summary: totals, progress bar, next due date.
8. EMI schedule table: one row per installment with status badge.
9. Overdue row: tinted and marked with the red Overdue badge.
10. Pay: the one primary action, only on the earliest pending row (after a confirm dialog).

**Validation and messages.**

- No typed input. A loan that is not the borrower's answers 404.
- Flash messages: payment success, "Pay the earliest pending installment first.", cancel success.
- Confirm dialogs: "Pay installment 4 of ₹5,176.45?" and "Cancel application LN-0007? This cannot be undone."

**Where the buttons go.**

- **Pay** (primary) appears only on the earliest pending row; other rows have no button.
- **Cancel application** is an outline button in the page header and exists only while the loan is Applied.

**Phone layout (390 px).** The loan page on a phone: a vertical tracker and the schedule as cards so nothing scrolls sideways.

![Wireframe of the loan details and emi schedule (phone)](wireframes/06_loan_details_phone.svg)

Numbered elements of the phone layout:

1. Menu button.
2. Title and status badge.
3. Vertical step tracker (the horizontal one does not fit on a phone).
4. Loan details card, one column.
5. Schedule as cards: two lines per installment instead of a wide table.
6. Pay: primary button, only on the earliest pending installment.

- **Pay** stays the one primary button, on the earliest pending card.

---

### Wireframe 7: Officer dashboard

| Route | User | Requirements |
|---|---|---|
| `GET /officer/dashboard` | Loan officer | FR-47 |

**Purpose.** Show an officer what needs attention now and take them to the right application in one click.

![Wireframe of the officer dashboard (desktop)](wireframes/07_officer_dashboard_desktop.svg)

**Numbered elements.**

1. Navigation for an officer: Dashboard and Applications.
2. Greeting.
3. New applications waiting for any officer (the card links to the filtered list).
4. Applications this officer picked up and has not decided yet.
5. Approved applications of this officer that still need disbursing.
6. My pending work: only Under Review and Approved loans of this officer, with the next step.
7. Open: goes to the application page where the decision is made.

**Validation and messages.**

- No form. When there is no pending work the table is replaced by an empty-state message.

**Where the buttons go.**

- No primary button on this page: the work happens on the application page. **Open** buttons are outlined; the count card "New applications" is a link to the list.

---

### Wireframe 8: Application detail (officer)

| Route | User | Requirements |
|---|---|---|
| `GET /officer/applications/<id>` and `POST .../pickup`, `.../approve`, `.../reject`, `.../disburse` | Loan officer (admin sees it read-only) | FR-23 to FR-28, FR-33 |

**Purpose.** Everything an officer needs to decide on one application and to carry it through approval and disbursal.

![Wireframe of the application detail (officer) (desktop)](wireframes/08_application_detail_desktop.svg)

**Numbered elements.**

1. Breadcrumb back to the applications list.
2. Application number and status badge.
3. Borrower card: name, email, phone, monthly income (everything needed for the decision).
4. Loan card: amount, tenure, locked rate, EMI, total payable, purpose and a link to the uploaded document.
5. Affordability bar: how close the EMI is to the income limit.
6. Decision card: its content depends on the status and on who is signed in (see the list below it).
7. Remarks box: required to reject, optional to approve (at most 300 characters).
8. Approve (green outline in the design).
9. Reject (red outline; asks to confirm).
10. Status history timeline with the officer's name and the dates.

**Validation and messages.**

- Reject without remarks: "Remarks are required to reject an application." (nothing is saved).
- An officer other than the assigned one sees "Assigned to <name>. Only they can act on this application." and the server refuses the action anyway.
- Confirm dialogs before Reject and Disburse. A loan that cannot take the action shows the state-machine message (for example "cannot move from Applied to Approved").

**Where the buttons go.**

- One primary button at a time, depending on the state: **Pick up for review** (Applied) or **Disburse** (Approved, mine).
- In the Under Review state the two decision buttons are **Approve** (green) and **Reject** (red outline), so the page still has no second yellow button.
- The admin sees no action buttons, only the **Reassign** card (see page 12 of the prototype).

---

### Wireframe 9: Admin dashboard

| Route | User | Requirements |
|---|---|---|
| `GET /admin/dashboard` | Admin | FR-48 |

**Purpose.** Give the admin a one-glance view of the system and shortcuts to the admin jobs.

![Wireframe of the admin dashboard (desktop)](wireframes/09_admin_dashboard_desktop.svg)

**Numbered elements.**

1. Navigation for an admin: Dashboard, Users, Applications, Settings, Reports.
2. Greeting and context.
3. Totals: users by role, rupees disbursed, collected and still outstanding.
4. Loans by status: one count and the standard status badge for each of the eight statuses.
5. Overdue installments: the number to act on, with a link to the report.
6. Shortcuts to the four admin jobs (all outlined: this page has no primary action).

**Validation and messages.**

- No form. All numbers come from the database when the page is drawn.

**Where the buttons go.**

- No primary button: the four shortcuts are outlined buttons, the overdue card links to the reports.

---

### Wireframe 10: Loan settings

| Route | User | Requirements |
|---|---|---|
| `GET/POST /admin/settings` | Admin | FR-43, FR-44, FR-11 |

**Purpose.** Let the admin change the loan limits and rate that every new application is checked against.

![Wireframe of the loan settings (desktop)](wireframes/10_loan_settings_desktop.svg)

**Numbered elements.**

1. Breadcrumb back to the dashboard.
2. Notice that a change affects only new applications.
3. Interest rate, 0 to 36 % a year.
4. Maximum EMI as a share of income (the affordability rule), 1 to 100 %.
5. Minimum and maximum loan amount (more than 0, maximum above minimum, at most 2 decimals).
6. Minimum and maximum tenure in whole months (at least 1, maximum above minimum).
7. Save settings: the one primary action.

**Validation and messages.**

- Each wrong field shows a message and keeps the typed values: rate outside 0 to 36; amounts not greater than 0, maximum not above minimum, or more than 2 decimals ("Use at most 2 decimal places."); tenures not whole numbers of at least 1, maximum not above minimum; EMI share outside 1 to 100.
- Success: "Settings saved." and the page shows the new values and the new "Last updated" date.

**Where the buttons go.**

- **Save settings** is the only primary button, under the last field, with the last update date beside it.

---

### Wireframe 11: Reports

| Route | User | Requirements |
|---|---|---|
| `GET /admin/reports` | Admin | FR-49, FR-50, FR-51, FR-38 |

**Purpose.** Show the admin the state of the portfolio in charts and list the overdue installments.

![Wireframe of the reports (desktop)](wireframes/11_reports_desktop.svg)

**Numbered elements.**

1. Breadcrumb back to the dashboard.
2. Pie chart of loans by status with a legend that shows the count of each status.
3. "View as table": the same data as text, with each share to one decimal that adds up to exactly 100.0 %.
4. Bar chart: amount disbursed in each of the last six months.
5. "View as table" for the bar chart.
6. Overdue installments table: borrower, loan, installment, due date with the red badge, days late, amount.

**Validation and messages.**

- No form. With no overdue installments the table is replaced by an empty-state message.
- Charts need the Chart.js script from the internet; the "View as table" blocks give the same numbers without it.

**Where the buttons go.**

- No primary button. The two "View as table" toggles are text controls under each chart.

---

## 3. Prototype (screenshots of the real pages)

The screenshots in `docs/prototype/` were taken from the running application, not from a mock-up. A throw-away copy of the app was started on port 5001 with a **temporary database** created by `seed.py`'s functions and a temporary upload folder; the real database and the server on port 5000 were not touched. Only the **seeded demo accounts** appear (Aman Gupta, Rohan Das, Priya Sharma, Admin User). Each page was captured at **1360 px** (desktop) and **390 px** (phone). For the apply page, the seeded Applied loan LN-0007 was cancelled in the temporary database so that a seeded borrower without an active loan (Rohan Das) could open the form.

| # | Page | Account and state | Desktop (1360 px) | Phone (390 px) |
|--:|---|---|---|---|
| 1 | Landing page | Visitor, not logged in (the hero, the facts strip and the three steps) | <a href="prototype/01_landing_desktop.png"><img src="prototype/01_landing_desktop.png" width="460" alt="Landing page, desktop"></a> | <a href="prototype/01_landing_phone.png"><img src="prototype/01_landing_phone.png" width="150" alt="Landing page, phone"></a> |
| 2 | Register | Empty form with the side panel | <a href="prototype/02_register_desktop.png"><img src="prototype/02_register_desktop.png" width="460" alt="Register, desktop"></a> | <a href="prototype/02_register_phone.png"><img src="prototype/02_register_phone.png" width="150" alt="Register, phone"></a> |
| 3 | Login | Empty form | <a href="prototype/03_login_desktop.png"><img src="prototype/03_login_desktop.png" width="460" alt="Login, desktop"></a> | <a href="prototype/03_login_phone.png"><img src="prototype/03_login_phone.png" width="150" alt="Login, phone"></a> |
| 4 | Borrower dashboard | Aman Gupta (seeded): active Repaying loan with one overdue installment | <a href="prototype/04_borrower_dashboard_desktop.png"><img src="prototype/04_borrower_dashboard_desktop.png" width="460" alt="Borrower dashboard, desktop"></a> | <a href="prototype/04_borrower_dashboard_phone.png"><img src="prototype/04_borrower_dashboard_phone.png" width="150" alt="Borrower dashboard, phone"></a> |
| 5 | Apply for a loan | Rohan Das (seeded) with 50,000 and 12 months typed in, so the EMI preview shows 4,442.44 | <a href="prototype/05_apply_desktop.png"><img src="prototype/05_apply_desktop.png" width="460" alt="Apply for a loan, desktop"></a> | <a href="prototype/05_apply_phone.png"><img src="prototype/05_apply_phone.png" width="150" alt="Apply for a loan, phone"></a> |
| 6 | Loan details and EMI schedule | Aman Gupta, loan LN-0002 (Repaying, installment 4 overdue) | <a href="prototype/06_loan_details_desktop.png"><img src="prototype/06_loan_details_desktop.png" width="460" alt="Loan details and EMI schedule, desktop"></a> | <a href="prototype/06_loan_details_phone.png"><img src="prototype/06_loan_details_phone.png" width="150" alt="Loan details and EMI schedule, phone"></a> |
| 7 | Officer dashboard | Priya Sharma (officer, seeded) | <a href="prototype/07_officer_dashboard_desktop.png"><img src="prototype/07_officer_dashboard_desktop.png" width="460" alt="Officer dashboard, desktop"></a> | <a href="prototype/07_officer_dashboard_phone.png"><img src="prototype/07_officer_dashboard_phone.png" width="150" alt="Officer dashboard, phone"></a> |
| 8 | Application detail (officer) | Priya Sharma on LN-0006 (Under Review): the decision card | <a href="prototype/08_application_detail_desktop.png"><img src="prototype/08_application_detail_desktop.png" width="460" alt="Application detail (officer), desktop"></a> | <a href="prototype/08_application_detail_phone.png"><img src="prototype/08_application_detail_phone.png" width="150" alt="Application detail (officer), phone"></a> |
| 9 | Admin dashboard | Admin User (seeded): totals, loans by status, overdue count | <a href="prototype/09_admin_dashboard_desktop.png"><img src="prototype/09_admin_dashboard_desktop.png" width="460" alt="Admin dashboard, desktop"></a> | <a href="prototype/09_admin_dashboard_phone.png"><img src="prototype/09_admin_dashboard_phone.png" width="150" alt="Admin dashboard, phone"></a> |
| 10 | Loan settings | Admin User: the settings form | <a href="prototype/10_loan_settings_desktop.png"><img src="prototype/10_loan_settings_desktop.png" width="460" alt="Loan settings, desktop"></a> | <a href="prototype/10_loan_settings_phone.png"><img src="prototype/10_loan_settings_phone.png" width="150" alt="Loan settings, phone"></a> |
| 11 | Reports | Admin User: pie chart, bar chart and the overdue table | <a href="prototype/11_reports_desktop.png"><img src="prototype/11_reports_desktop.png" width="460" alt="Reports, desktop"></a> | <a href="prototype/11_reports_phone.png"><img src="prototype/11_reports_phone.png" width="150" alt="Reports, phone"></a> |
| 12 | Application detail, admin view | Admin User on LN-0006: read-only page with the Reassign card | <a href="prototype/12_admin_reassign_desktop.png"><img src="prototype/12_admin_reassign_desktop.png" width="460" alt="Admin reassign, desktop"></a> | <a href="prototype/12_admin_reassign_phone.png"><img src="prototype/12_admin_reassign_phone.png" width="150" alt="Admin reassign, phone"></a> |

### What the screenshots show about responsiveness (NFR-15)

At 390 px the step tracker runs top to bottom and each schedule row becomes a two-line card, so Pay is always visible; the navigation collapses into one menu button. Tables scroll inside their own card instead of widening the page. The first set of screenshots showed that the **Officer dashboard** (594 px) and the borrower's **My loans** (655 px) were wider than the phone screen, because a visually hidden label inside the scrolling table is absolutely positioned and escaped the table wrapper; `position: relative` on `.table-responsive` fixed it, and the 13 table and form pages that were measured again are exactly 390 px wide.

---

## 4. From wireframe to prototype

The wireframes fix the **structure** (what is on the page, in which order, which button is the main one). The prototype adds the **visual design** (colour, type, icons, states) without moving that structure. Differences, and the reason for each:

| Wireframe | Prototype | Why |
|---|---|---|
| Greys only; the primary action is a dark box | Blue for structure (navigation, headings, links, tables); the one primary action is **yellow with navy text** | Yellow is rare, so it draws the eye to the next step (Von Restorff); navy on yellow keeps the contrast above 4.5 to 1 |
| Plain status text | Soft coloured **status badges**, one mapping for the whole site; red solid for Overdue | Recognition instead of reading; overdue is the loudest badge |
| A list of six steps | A **step tracker** with ticks, a highlighted current step and the steps still ahead | Zeigarnik effect; the borrower always sees what comes next |
| Plain progress bar | Bar with a **yellow tip** next to "3 of 6 paid" | Goal-gradient effect |
| Boxes and lines | Cards with a 16 px radius, summary tiles, icons marked `aria-hidden` | Common region, Jakob's law (a familiar banking layout) |
| One layout per page | **Phone layout**: vertical tracker, schedule rows as two-line cards, full-width buttons, one menu button | Fitts's law and legibility at 390 px |
| No admin action on the application page | A **Reassign** card with a blue outline button and a confirm dialog (added with the admin reassignment feature) | It must not add a second yellow button to the admin page |
| Error states drawn as dashed boxes | Red-tinted fields, an icon and a message under each wrong field, typed values kept | Error messages tell what to fix, where |

### Laws of UX applied (from `CLAUDE.md` section 9a)

| Law | How it shows in the pages | Where |
|---|---|---|
| Von Restorff (the odd one out is remembered) | Yellow is rare, so the one yellow button on each page (Pay, Submit application, Create account, Save settings...) is what the eye finds first. | all pages |
| Hick's law (fewer choices, faster decisions) | At most 5 menu items per role (admin has 5, officer 2, borrower 3); one primary action per page. | navigation bar, dashboards |
| Fitts's law (big, near targets) | The main buttons are at least 44 px tall; Pay sits on the row it pays; Reassign sits in the card that explains it; full-width buttons on a phone. | 4, 6, 8, phone layouts |
| Jakob's law (users expect familiar patterns) | A banking-style layout: thin utility strip, white header, breadcrumbs, cards, summary tiles. | all pages |
| Common region and proximity | Related facts sit together in bordered cards (borrower, loan, status updates, repayment summary). | 6, 8 |
| Miller's law and chunking | Short cards instead of long lists; Indian digit grouping (1,00,000) for money. | 4, 6, 9 |
| Goal-gradient effect | The installments-paid bar has a yellow tip; the closer to the end, the more visible the progress. | 4, 6 |
| Zeigarnik effect | The step tracker shows the steps still ahead (Closed is shown, empty, from the start). | 6, landing page |
| Peak-end rule | A success banner on a fully repaid (Closed) loan. | 6 |
| Doherty threshold (respond within 400 ms) | The EMI preview recalculates in the browser while typing; the submit button shows a busy state. | 5 |
| Tesler's law (the system takes the complexity) | The system does the maths: EMI, totals, schedule, overdue. | 5, 6 |
| Aesthetic-usability effect | One set of design tokens (blue, navy, yellow, canvas, muted text) makes every page look like one product. | all pages |

The rule of thumb behind the colours: **blue is the voice, yellow is the finger.** About 60 % neutral, 30 % blue and 10 % yellow, with at most one enabled yellow button per page.

