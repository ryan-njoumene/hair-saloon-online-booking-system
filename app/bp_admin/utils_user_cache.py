from flask import render_template
from app import cache
from models.database import db
from .utils_admin import flash_and_redirect, make_context

@cache.memoize(timeout=60)
def get_view_user_cached(user_id, return_type):
    """
    Cached helper to render a user's profile view.

    Fetches user details and warning count, constructs context, and renders the
    profile page. If the user is not found, redirects with a flash message.

    Args:
        user_id (int): ID of the user to view.
        return_type (str): Context to preserve for the return link (e.g., 'all', 'clients').

    Returns:
        str: Rendered HTML page showing user details, or redirect if user not found.
    """
    # Retrieve user by ID
    user = db.get_user_by_id(user_id)
    if not user:
        return flash_and_redirect("User not found.", "danger", "bp-admin.manage_users")

    # Get the number of warnings for the user
    warning_count = db.get_warning_count(user_id)

    # Build the template context with title and heading
    context = make_context(f"User Info - {user[4]}", f"Details for {user[4]}")
    context["return_type"] = return_type

    return render_template("users/view_user.html", context=context, user=user, warning_count=warning_count)
