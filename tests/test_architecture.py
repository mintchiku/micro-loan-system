"""The code structure the blueprint promises: thin routes, rules only in the service layer, simple code (NFR-11, CLAUDE.md sections 2, 3, 15)."""
import ast
import glob
import os
import re

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def source(relative):
    return open(os.path.join(ROOT, relative), encoding="utf-8").read()


def python_files(pattern):
    return sorted(glob.glob(os.path.join(ROOT, pattern), recursive=True))


ROUTE_FILES = python_files("app/routes/*.py")
ALL_APP_FILES = python_files("app/**/*.py") + [os.path.join(ROOT, f) for f in ("config.py", "run.py", "seed.py")]


def test_there_are_five_route_modules():
    names = {os.path.basename(f) for f in ROUTE_FILES}
    assert {"main.py", "auth.py", "borrower.py", "officer.py", "admin.py"} <= names


@pytest.mark.parametrize("path", ROUTE_FILES, ids=[os.path.basename(f) for f in ROUTE_FILES])
def test_routes_never_commit_or_set_a_status(path):
    code = open(path, encoding="utf-8").read()
    assert "commit(" not in code, "a route must call a service function; the service does the one commit"
    assert not re.search(r"\.status\s*=[^=]", code), "a route must not set a status; only change_status may"
    assert not re.search(r"\bLoan\(", code) and not re.search(r"\bRepayment\(", code), "routes do not build loans or installments"


def test_only_change_status_assigns_a_loan_status():
    assert len(re.findall(r"\bloan\.status\s*=[^=]", source("app/services/loan_service.py"))) == 1
    for path in ALL_APP_FILES:
        if path.endswith("loan_service.py"):
            continue
        assert not re.search(r"\.status\s*=[^=]", open(path, encoding="utf-8").read()), path


def test_installments_are_only_marked_paid_in_the_service():
    code = source("app/services/loan_service.py")
    assert len(re.findall(r'\.status\s*=\s*"Paid"', code)) == 1


def test_the_service_layer_does_not_know_about_pages():
    """Services may only use flask's current_app (for the upload folder); no pages, redirects, messages or request data."""
    for path in python_files("app/services/*.py"):
        tree = ast.parse(open(path, encoding="utf-8").read())
        imported = {alias.name for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module == "flask" for alias in n.names}
        assert imported <= {"current_app"}, f"{os.path.basename(path)} imports {imported - {'current_app'}} from flask"
        code = open(path, encoding="utf-8").read()
        for call in ("render_template(", "redirect(", "flash(", "url_for(", "request."):
            assert call not in code, f"{os.path.basename(path)} must not use {call}"


def test_every_commit_in_the_service_has_a_rollback():
    code = source("app/services/loan_service.py")
    assert code.count("db.session.commit()") <= code.count("db.session.rollback()")


def test_the_emi_module_does_not_touch_the_database():
    code = source("app/services/emi.py")
    assert "db" not in re.findall(r"^(?:from|import) (\w+)", code, re.M) and "session" not in code


def test_templates_do_not_change_data():
    for path in glob.glob(os.path.join(ROOT, "app", "templates", "**", "*.html"), recursive=True):
        html = open(path, encoding="utf-8").read()
        assert not re.search(r"\{%\s*set\s+\w+\.status\s*=", html), path
        assert "db.session" not in html, path


@pytest.mark.parametrize("path", ALL_APP_FILES, ids=[os.path.relpath(f, ROOT) for f in ALL_APP_FILES])
def test_every_function_has_a_docstring(path):
    tree = ast.parse(open(path, encoding="utf-8").read())
    missing = [n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and not ast.get_docstring(n)]
    assert not missing, f"functions without a docstring: {missing}"


def test_the_required_libraries_are_exactly_the_four_in_the_blueprint():
    lines = [l.strip() for l in source("requirements.txt").splitlines() if l.strip()]
    assert sorted(re.split(r"[<>=]", l)[0].lower() for l in lines) == ["flask", "flask-login", "flask-sqlalchemy", "python-dotenv"]


def test_pytest_is_a_development_only_dependency():
    assert "pytest" not in source("requirements.txt").lower()
    dev = source("requirements-dev.txt")
    assert "pytest" in dev and "-r requirements.txt" in dev


def test_secrets_are_not_hard_coded():
    config = source("config.py")
    assert 'os.environ.get("SECRET_KEY"' in config
    for path in ROUTE_FILES + python_files("app/services/*.py"):
        assert "SECRET_KEY" not in open(path, encoding="utf-8").read()


def test_the_blueprint_folders_exist():
    for relative in ("app/routes", "app/services", "app/utils", "app/templates/base.html", "app/static/css/style.css", "app/static/js/main.js",
                     "app/models.py", "seed.py", "run.py", "config.py", ".env.example", ".gitignore", "README.md", "CLAUDE.md"):
        assert os.path.exists(os.path.join(ROOT, relative)), relative


def test_generated_files_are_git_ignored():
    ignored = source(".gitignore").split()
    for pattern in ("venv/", "instance/", "__pycache__/", "uploads/", ".env"):
        assert pattern in ignored
