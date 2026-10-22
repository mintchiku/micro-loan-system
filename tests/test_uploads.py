"""Supporting documents: type, content, size, safe storage and protected viewing (R10, FR-17, FR-52, NFR-05)."""
import os
import re

import pytest

from app import db
from app.models import Document, Loan
from app.services.loan_service import detect_file_type
from support import JPG, MB2, PDF, PNG, apply, padded, post, text

NAME_MESSAGE = "Only PDF, JPG or PNG files are allowed."
CONTENT_MESSAGE = "not a real PDF, JPG or PNG that matches its name"


def stored_files(app):
    folder = app.config["UPLOAD_FOLDER"]
    return os.listdir(folder) if os.path.isdir(folder) else []


# ---------- accepted files ----------

@pytest.mark.parametrize("name, content", [
    ("slip.pdf", PDF), ("scan.png", PNG), ("photo.jpg", JPG), ("photo.jpeg", JPG),
    ("SCAN.PNG", PNG), ("UPPER.PDF", PDF), ("my file (1).pdf", PDF),
])
def test_real_files_are_accepted_and_saved_unchanged(app, borrower_with_income, name, content):
    client, uid = borrower_with_income(80000)
    assert apply(client, document=(content, name)).status_code == 302
    with app.app_context():
        document = Document.query.one()
        saved = open(os.path.join(app.config["UPLOAD_FOLDER"], document.stored_name), "rb").read()
        assert saved == content, "the file must be saved byte for byte (the stream is rewound after the check)"
        assert re.fullmatch(r"[0-9a-f]{32}\.(pdf|png|jpg|jpeg)", document.stored_name), "stored under a random uuid name"


def test_exactly_two_megabytes_is_accepted(borrower_with_income):
    client, _ = borrower_with_income(80000)
    assert apply(client, document=(padded(PDF, MB2), "big.pdf")).status_code == 302


# ---------- refused files ----------

@pytest.mark.parametrize("name, content, message", [
    ("fake.pdf", b"this is plain text, not a pdf at all", CONTENT_MESSAGE),   # a text file renamed .pdf
    ("wrong.pdf", PNG, CONTENT_MESSAGE),                                       # a PNG renamed .pdf
    ("wrong.png", PDF, CONTENT_MESSAGE),
    ("wrong.jpg", PNG, CONTENT_MESSAGE),
    ("wrong.jpeg", PDF, CONTENT_MESSAGE),
    ("virus.exe", b"MZ\x90\x00 program", NAME_MESSAGE),
    ("noext", PDF, NAME_MESSAGE),
    ("image.svg", b"<svg xmlns='http://www.w3.org/2000/svg'/>", NAME_MESSAGE),
    ("page.html", b"<html><script>alert(1)</script></html>", NAME_MESSAGE),
    ("note.txt", b"hello", NAME_MESSAGE),
    ("double.pdf.exe", PDF, NAME_MESSAGE),
    ("empty.pdf", b"", "The file is empty."),
])
def test_bad_files_are_refused_and_nothing_is_saved(app, borrower_with_income, name, content, message):
    client, uid = borrower_with_income(80000)
    response = apply(client, document=(content, name))
    assert response.status_code == 200 and message in text(response)
    with app.app_context():
        assert Loan.query.filter_by(borrower_id=uid).count() == 0 and Document.query.count() == 0
    assert stored_files(app) == [], "a refused file must never be saved"


def test_one_byte_over_two_megabytes_is_refused(app, borrower_with_income):
    client, _ = borrower_with_income(80000)
    response = apply(client, document=(padded(PDF, MB2 + 1), "big.pdf"))
    assert "The file is larger than 2 MB." in text(response) and stored_files(app) == []


def test_a_request_over_three_megabytes_is_cut_off(app, borrower_with_income):
    """The whole request is capped at 3 MB (MAX_CONTENT_LENGTH): the visitor is sent back with a message."""
    client, uid = borrower_with_income(80000)
    response = apply(client, document=(padded(PDF, 4 * 1024 * 1024), "huge.pdf"))
    assert response.status_code == 302
    assert "The file is too large" in text(client.get("/borrower/apply"))
    assert stored_files(app) == []


def test_missing_file_is_refused(borrower_with_income):
    client, _ = borrower_with_income(80000)
    assert "Please upload a supporting document" in text(apply(client, document=None))


def test_one_document_per_application(app, borrower_with_income):
    client, uid = borrower_with_income(80000)
    apply(client)
    with app.app_context():
        loan = Loan.query.filter_by(borrower_id=uid).one()
        assert Document.query.filter_by(loan_id=loan.id).count() == 1
    assert len(stored_files(app)) == 1


def test_original_name_is_made_safe(app, borrower_with_income):
    client, _ = borrower_with_income(80000)
    apply(client, document=(PDF, "../../evil name.pdf"))
    with app.app_context():
        document = Document.query.one()
        assert ".." not in document.original_name and "/" not in document.original_name
        assert document.original_name.endswith(".pdf")
        assert os.path.dirname(os.path.join(app.config["UPLOAD_FOLDER"], document.stored_name)) == app.config["UPLOAD_FOLDER"]


@pytest.mark.parametrize("header, expected", [
    (b"%PDF-1.7", ".pdf"), (bytes.fromhex("89504e470d0a1a0a"), ".png"), (bytes.fromhex("ffd8ffe000104a46"), ".jpg"),
    (b"GIF89a", None), (b"PK\x03\x04", None), (b"", None), (b"MZ", None),
])
def test_detect_file_type(header, expected):
    assert detect_file_type(header) == expected


# ---------- files are not publicly reachable (NFR-05) ----------

@pytest.fixture
def uploaded(app, borrower_with_income):
    """A borrower with one uploaded PDF: returns (client, loan id, document id, stored name)."""
    client, uid = borrower_with_income(80000)
    apply(client, document=(PDF, "salary.pdf"))
    with app.app_context():
        document = Document.query.one()
        return client, document.loan_id, document.id, document.stored_name


def test_uploads_live_outside_the_static_folder(app):
    upload = os.path.abspath(app.config["UPLOAD_FOLDER"])
    static = os.path.abspath(app.static_folder)
    assert not upload.startswith(static)


def test_the_file_cannot_be_fetched_by_url(uploaded, anon):
    _client, _loan, _doc, stored = uploaded
    for url in (f"/static/{stored}", f"/static/uploads/{stored}", f"/uploads/{stored}", f"/{stored}"):
        assert anon.get(url).status_code == 404, url


def test_owner_officer_and_admin_can_open_the_document(uploaded, priya, admin):
    client, _loan, doc, _stored = uploaded
    for who in (client, priya, admin):
        response = who.get(f"/documents/{doc}")
        assert response.status_code == 200 and response.data == PDF


def test_another_borrower_gets_404(uploaded, aman):
    _client, _loan, doc, _stored = uploaded
    assert aman.get(f"/documents/{doc}").status_code == 404


def test_a_visitor_is_sent_to_login(uploaded, anon):
    _client, _loan, doc, _stored = uploaded
    response = anon.get(f"/documents/{doc}")
    assert response.status_code == 302 and "/login" in response.headers["Location"]


def test_missing_document_is_404(priya):
    assert priya.get("/documents/9999").status_code == 404
