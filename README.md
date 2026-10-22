# Micro-Loan Management System

A Flask web app where borrowers apply for small loans, loan officers review and disburse them,
and admins manage users, settings and reports. Payments are simulated.

## Setup (Windows PowerShell)

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1          # if blocked: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
pip install -r requirements.txt
copy .env.example .env                # then put your own SECRET_KEY in .env
```

## Seed demo data

```powershell
python seed.py      # asks y/n, then RESETS the database and loads demo accounts
```

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

## Run

```powershell
python run.py
```

Open http://127.0.0.1:5000. The SQLite database is created automatically at `instance/microloan.db`.
