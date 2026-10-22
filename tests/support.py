"""Small helpers shared by the tests: CSRF-aware client, sample files, database shortcuts."""
import io

import seed

TOKEN = "test-csrf-token"
PASSWORDS = {email: password for _name, email, password, _role, _phone, _income in seed.DEMO_USERS}

# The first bytes of real files; the upload check reads them (PDF "%PDF", PNG 89 50 4E 47, JPEG FF D8 FF)
PDF = b"%PDF-1.4\n1 0 obj\n<< >>\nendobj\ntrailer\n<< >>\n%%EOF\n"
PNG = bytes.fromhex("89504e470d0a1a0a") + b"\x00" * 40
JPG = bytes.fromhex("ffd8ffe0") + b"\x00" * 40
MB2 = 2 * 1024 * 1024


def new_client(app):
    """A test client whose session already holds a known CSRF token."""
    client = app.test_client()
    with client.session_transaction() as session:
        session["csrf_token"] = TOKEN
    return client


def post(client, url, data=None, **kwargs):
    """POST with the CSRF token added (unless the data already names one)."""
    data = dict(data or {})
    data.setdefault("csrf_token", TOKEN)
    return client.post(url, data=data, **kwargs)


def padded(signature, size):
    """A file of exactly `size` bytes that starts with `signature`."""
    return signature + b"x" * (size - len(signature))


def apply_data(amount="10000", tenure="6", purpose="Test purpose", document=(PDF, "slip.pdf")):
    """Form data for POST /borrower/apply; pass document=None to send no file."""
    data = {"amount": amount, "tenure_months": tenure, "purpose": purpose}
    if document is not None:
        data["document"] = (io.BytesIO(document[0]), document[1])
    return data


def apply(client, follow_redirects=False, **fields):
    """Submit the apply form (multipart); `fields` are the form fields (see apply_data)."""
    return post(client, "/borrower/apply", apply_data(**fields), content_type="multipart/form-data",
                follow_redirects=follow_redirects)


def register_data(**overrides):
    """A valid registration form; override single fields to test one rule at a time."""
    data = {"name": "Test Borrower", "email": "test@example.com", "phone": "9000000012", "monthly_income": "80000",
            "password": "Passw0rd1", "confirm_password": "Passw0rd1"}
    data.update(overrides)
    return data


def text(response):
    """The response body as text."""
    return response.get_data(as_text=True)
