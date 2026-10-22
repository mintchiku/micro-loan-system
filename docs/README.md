# MicroLoan: software engineering documentation

This folder holds the documents for the Software Engineering assignment. Everything describes the application as it is now (22 routes, 5 tables, 8 loan statuses), including the fixes made after the first review.

## Where to find each assignment item

| Assignment item | Where | Files |
|---|---|---|
| Functional requirements | [01_SRS_requirements.md](01_SRS_requirements.md), section 4 (58 requirements, FR-01 to FR-58, in 8 modules) | - |
| Non-functional requirements | [01_SRS_requirements.md](01_SRS_requirements.md), section 7 (16 requirements with measurable criteria) | - |
| Business rules R1 to R11 | [01_SRS_requirements.md](01_SRS_requirements.md), section 5 | - |
| Traceability matrix (requirement to code to diagram to test) | [01_SRS_requirements.md](01_SRS_requirements.md), section 8 | - |
| Use case diagram | [02_diagrams.md](02_diagrams.md), section 1 | `diagrams/01_use_case_overview`, `01a`, `01b`, `01c` |
| Activity diagram | [02_diagrams.md](02_diagrams.md), section 2 | `diagrams/02_activity_apply_for_loan`, `02b_activity_review_disburse_reassign` |
| **Swimlane diagram** | [02_diagrams.md](02_diagrams.md), section 6 | `diagrams/05_swimlane_loan_lifecycle`, `05b_swimlane_pay_installment` |
| Class diagram | [02_diagrams.md](02_diagrams.md), section 3 | `diagrams/03_class_domain`, `03b_class_services` |
| **CRC cards** | [02_diagrams.md](02_diagrams.md), section 4 (seven cards, as tables) | - |
| Data flow diagrams level 0, 1 and 2 | [02_diagrams.md](02_diagrams.md), section 7 | `diagrams/06_dfd_level0`, `06b`, `06c`, `06d` to `06g` |
| State diagram | [02_diagrams.md](02_diagrams.md), section 5 | `diagrams/04_state_loan`, `04b_state_repayment` |
| Sequence diagrams | [02_diagrams.md](02_diagrams.md), section 8 (login, apply, review and disburse, pay, reassign) | `diagrams/07_sequence_login_logout`, `07b` to `07e` |
| Wireframes | [03_wireframes_and_prototype.md](03_wireframes_and_prototype.md), section 2 (11 pages on desktop, 2 on a phone) | `wireframes/*.svg` |
| Navigation maps | [03_wireframes_and_prototype.md](03_wireframes_and_prototype.md), section 1 | `diagrams/08_navigation_visitor`, `08b`, `08c`, `08d` |
| Prototype | [03_wireframes_and_prototype.md](03_wireframes_and_prototype.md), section 3 (screenshots of the real pages) | `prototype/*.png` |
| Wireframe to prototype, Laws of UX | [03_wireframes_and_prototype.md](03_wireframes_and_prototype.md), section 4 | - |
| Automated tests | the `tests/` folder in the project root (see the main `README.md` for the command) | - |

## Suggested reading order

1. [01_SRS_requirements.md](01_SRS_requirements.md): what the system must do.
2. [02_diagrams.md](02_diagrams.md): how it is modelled (use cases, flows, classes, states, messages).
3. [03_wireframes_and_prototype.md](03_wireframes_and_prototype.md): how it looks.
4. `../WEBSITE_COMPLETE_TECHNICAL_DOCUMENTATION.md`: the code in detail, with a viva question bank and a slide plan.

## Files

### `diagrams/` (28 diagrams, each as PNG at 2x and as SVG: 56 files)

| File (without extension) | Diagram |
|---|---|
| `01_use_case_overview` | Use case: all four actors |
| `01a_use_case_borrower` | Use case: borrower and System |
| `01b_use_case_officer` | Use case: loan officer |
| `01c_use_case_admin` | Use case: admin |
| `02_activity_apply_for_loan` | Activity: apply for a loan |
| `02b_activity_review_disburse_reassign` | Activity: review, reassign, disburse |
| `03_class_domain` | Class diagram: domain classes |
| `03b_class_services` | Class diagram: service layer |
| `04_state_loan` | State: loan lifecycle |
| `04b_state_repayment` | State: installment |
| `05_swimlane_loan_lifecycle` | Swimlane: full loan lifecycle (4 lanes) |
| `05b_swimlane_pay_installment` | Swimlane: pay an installment (2 lanes) |
| `06_dfd_level0` | DFD level 0 |
| `06b_dfd_level1_sheet1` | DFD level 1, sheet 1 |
| `06c_dfd_level1_sheet2` | DFD level 1, sheet 2 |
| `06d_dfd_level2_apply` | DFD level 2: process 2 (apply) |
| `06e_dfd_level2_review` | DFD level 2: process 3 (review and reassign) |
| `06f_dfd_level2_disburse` | DFD level 2: process 4 (disburse) |
| `06g_dfd_level2_repayment` | DFD level 2: process 5 (repayment) |
| `07_sequence_login_logout` | Sequence: login and logout |
| `07b_sequence_apply` | Sequence: apply |
| `07c_sequence_review_disburse` | Sequence: review and disburse |
| `07d_sequence_pay` | Sequence: pay an installment |
| `07e_sequence_reassign` | Sequence: admin reassigns |
| `08_navigation_visitor` | Navigation map: visitor |
| `08b_navigation_borrower` | Navigation map: borrower |
| `08c_navigation_officer` | Navigation map: officer |
| `08d_navigation_admin` | Navigation map: admin |

### `wireframes/` (13 grayscale SVG files)

- `01_landing_desktop.svg`
- `02_register_desktop.svg`
- `03_login_desktop.svg`
- `04_borrower_dashboard_desktop.svg`
- `04_borrower_dashboard_phone.svg`
- `05_apply_desktop.svg`
- `06_loan_details_desktop.svg`
- `06_loan_details_phone.svg`
- `07_officer_dashboard_desktop.svg`
- `08_application_detail_desktop.svg`
- `09_admin_dashboard_desktop.svg`
- `10_loan_settings_desktop.svg`
- `11_reports_desktop.svg`

### `prototype/` (24 screenshots: 12 pages x desktop 1360 px and phone 390 px)

- `01_landing_desktop.png`
- `01_landing_phone.png`
- `02_register_desktop.png`
- `02_register_phone.png`
- `03_login_desktop.png`
- `03_login_phone.png`
- `04_borrower_dashboard_desktop.png`
- `04_borrower_dashboard_phone.png`
- `05_apply_desktop.png`
- `05_apply_phone.png`
- `06_loan_details_desktop.png`
- `06_loan_details_phone.png`
- `07_officer_dashboard_desktop.png`
- `07_officer_dashboard_phone.png`
- `08_application_detail_desktop.png`
- `08_application_detail_phone.png`
- `09_admin_dashboard_desktop.png`
- `09_admin_dashboard_phone.png`
- `10_loan_settings_desktop.png`
- `10_loan_settings_phone.png`
- `11_reports_desktop.png`
- `11_reports_phone.png`
- `12_admin_reassign_desktop.png`
- `12_admin_reassign_phone.png`

## How the files were made

- **Diagrams** are written in Mermaid inside `02_diagrams.md` and `03_wireframes_and_prototype.md`. Each block was rendered in headless Microsoft Edge with Mermaid 10.9.3 (and checked with 11.4.0, which GitHub uses) and exported to PNG and SVG. To change a diagram, edit its block and render it again with any Mermaid tool (for example the Mermaid Live Editor); the swimlane diagrams use one subgraph per lane with invisible helper nodes that keep the lanes in a fixed grid.
- **Wireframes** are hand-built SVG files (grayscale on purpose, so the layout is judged before the colour).
- **Prototype screenshots** come from the running application. A temporary copy was started on port 5001 with a temporary database and upload folder (the real database and the server on port 5000 were not touched) and only the seeded demo accounts were used.

## Known issues noted in these documents

1. The Officer dashboard and the borrower's My loans page are wider than a 390 px phone screen (see SRS section 9 and the prototype section of file 03).
2. One decorative icon in the utility bar lacks `aria-hidden` (SRS section 9; a strict expected-failure test in `tests/test_ui.py` records it).

Both are documented, not fixed, and wait for the owner's go-ahead.

