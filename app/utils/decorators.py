"""Access-control decorator and role helpers."""
from functools import wraps

from flask import abort, url_for
from flask_login import current_user

from app import login_manager


def role_required(*roles):
    """Allow a view only for logged-in users whose role is in `roles`, e.g. @role_required("officer")."""
    def decorator(view):
        """Wrap one view function with the role check."""
        @wraps(view)
        def wrapped(*args, **kwargs):
            """Run the view only if the user is logged in with an allowed role."""
            if not current_user.is_authenticated:
                return login_manager.unauthorized()  # redirects to the login page
            if current_user.role not in roles:
                abort(403)  # logged in, but this page is for another role
            return view(*args, **kwargs)
        return wrapped
    return decorator


def dashboard_url(user):
    """Return the dashboard URL for a user's role (blueprints are named after roles)."""
    return url_for(f"{user.role}.dashboard")
