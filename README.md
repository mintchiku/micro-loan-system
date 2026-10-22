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

## Run

```powershell
python run.py
```

Open http://127.0.0.1:5000. The SQLite database is created automatically at `instance/microloan.db`.
