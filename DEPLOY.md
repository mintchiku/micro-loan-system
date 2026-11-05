# Deploying MicroLoan on PythonAnywhere (free plan)

Replace `YOURNAME` with your PythonAnywhere username everywhere below. The site will be at `https://YOURNAME.pythonanywhere.com`.

The app needs nothing else: SQLite is a file, uploads are files, and Bootstrap / Chart.js are loaded by the visitor's browser from a CDN.

## 1. Get the code onto PythonAnywhere

Open **Consoles -> Bash** and run one of these.

**A. From GitHub** (push the project first; do not push `.env`, `instance/` or `uploads/`, they are git-ignored):

```bash
cd ~
git clone https://github.com/YOURGITHUB/micro-loan-system.git
```

**B. Without GitHub:** zip the project folder on your PC (without `venv/`, `instance/`, `uploads/`, `.env`), use the **Files** tab to upload the zip into your home folder, then:

```bash
cd ~
unzip micro-loan-system.zip -d micro-loan-system
```

The project folder is now `/home/YOURNAME/micro-loan-system` (check with `ls ~/micro-loan-system/wsgi.py`).

## 2. Virtual environment and packages

```bash
mkvirtualenv microloan --python=python3.13   # if this version is not offered, use python3.12 or python3.11
pip install -r ~/micro-loan-system/requirements.txt
```

(Do not install `requirements-dev.txt` on the server; pytest is only for your PC.)

## 3. Create the `.env` file with a generated secret

```bash
cd ~/micro-loan-system
python -c "import secrets; print('SECRET_KEY=' + secrets.token_hex(32))" > .env
chmod 600 .env
cat .env        # should show one line: SECRET_KEY=<64 hex characters>
```

Never share or commit this file. The app refuses to start without a `SECRET_KEY`.

## 4. Create the database and the demo data

```bash
cd ~/micro-loan-system
python seed.py          # answer y; this creates instance/microloan.db and loads the demo users and loans
```

Demo logins are in `README.md` (for example `admin@microloan.com` / `Admin@123`). **Change the demo passwords or reseed with your own data before showing the site to anyone you do not trust**; the demo passwords are public in the repository.

`uploads/` is created automatically the first time the app starts.

## 5. Create the web app (Web tab)

1. Open the **Web** tab -> **Add a new web app** -> **Next**.
2. Choose **Manual configuration** (not Flask) -> choose the same Python version as in step 2 -> **Next**.
3. On the web app page set:

| Setting | Value |
|---|---|
| **Source code** | `/home/YOURNAME/micro-loan-system` |
| **Working directory** | `/home/YOURNAME/micro-loan-system` |
| **Virtualenv** | `/home/YOURNAME/.virtualenvs/microloan` |
| **Force HTTPS** | Enabled |

4. **Static files** section -> **Enter URL** `/static/` -> **Enter path** `/home/YOURNAME/micro-loan-system/app/static`.
   Do **not** map `/uploads/`: documents must stay private and are served only by the app after a login check.

## 6. The WSGI file

On the Web tab click the link **WSGI configuration file** (`/var/www/YOURNAME_pythonanywhere_com_wsgi.py`). Delete everything in it and put exactly this:

```python
import sys

PROJECT = "/home/YOURNAME/micro-loan-system"
if PROJECT not in sys.path:
    sys.path.insert(0, PROJECT)

from wsgi import application  # noqa: E402,F401  (loads .env, then creates the app)
```

Save it. `wsgi.py` in the project reads `/home/YOURNAME/micro-loan-system/.env`, so the secret never appears in this file.

## 7. Reload and test

1. Web tab -> green **Reload YOURNAME.pythonanywhere.com** button.
2. Open `https://YOURNAME.pythonanywhere.com`: the landing page should appear with styling.
3. Log in as `admin@microloan.com`, open Reports, then register a borrower and run the demo script from `CLAUDE.md` section 13.
4. If something is wrong, open the **Error log** link on the Web tab (a missing `SECRET_KEY` or a wrong path shows up there).

After every code change on the server (`git pull` or new upload) press **Reload** again.

## 8. Updating the site later

```bash
cd ~/micro-loan-system
git pull                                  # option A; for option B upload the changed files instead
workon microloan && pip install -r requirements.txt
```

Then **Reload** on the Web tab. Do not run `python seed.py` again unless you want to erase all data (it resets the database).

## 9. Keeping the free site alive (expiry)

A free web app is switched off after a limited time unless you extend it (the Web tab shows **"This site will be disabled on <date>"**; for your account that is every month).

- Log in to PythonAnywhere before that date, open the **Web** tab and press the **Run until <date> / Extend** button (it restarts the countdown).
- Put a reminder in your calendar a few days before the date.
- Your files, database and `.env` are kept while the site is disabled; extending it brings the site back.

## Limits of the free plan (good to know)

- One web app, at `YOURNAME.pythonanywhere.com` only (no custom domain).
- Small disk (about 512 MB) and CPU quota: fine for a demo, not for many users.
- SQLite on a single web worker is fine here; do not run two copies of the app against the same database file.
- The server cannot call arbitrary websites, which does not matter here (the app calls none).

## Not done on purpose

- `SESSION_COOKIE_SECURE` is not switched on (the app runs over plain http locally). On PythonAnywhere everything is served over https; if you want the extra protection, add `SESSION_COOKIE_SECURE = True` to `config.py` for the deployed copy only.
- No monitoring, backups or password rotation: copy `instance/microloan.db` with the Files tab if you want a backup.
