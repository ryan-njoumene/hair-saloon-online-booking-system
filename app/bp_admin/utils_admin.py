# utils_admin.py (helper module for admin blueprint)

from datetime import datetime
from flask import flash, redirect, url_for
from functools import wraps
from flask_login import current_user


def role_required(*roles):
    """
    Decorator to enforce role-based access control for admin routes.

    Args:
        *roles (str): One or more authorized user types (e.g., 'admin_super').

    Returns:
        function: A wrapped view function that checks the user's role.
    """
    def wrapper(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if current_user.user_type not in roles:
                flash("Access Denied.", "danger")
                return redirect(url_for("bp-main.home"))
            return f(*args, **kwargs)
        return decorated_function
    return wrapper


def populate_appointment_form_choices(form, db):
    """
    Populate choices for dropdown fields in the appointment form.

    Args:
        form (FlaskForm): The appointment form instance.
        db (Database): Database instance for fetching user choices.
    """
    form.venue.choices = [
        ("room1", "Room 1"), ("room2", "Room 2"),
        ("chair1", "Chair 1"), ("chair2", "Chair 2")
    ]
    form.slot.choices = [
        (f"{i}-{i+1}", f"{i}-{i+1}") for i in list(range(1, 12)) + list(range(13, 22))
    ]
    form.client_id.choices = db.get_client_choices()
    form.provider_id.choices = db.get_provider_choices()


def invalidate_appointment_cache(cache, user_type):
    """
    Clear cached appointment views for an admin user by appointment status.

    Args:
        cache (Cache): Flask-Caching instance.
        user_type (str): The admin's user type used for cache scoping.
    """
    from app.bp_admin.appointments import _get_manage_appointments_cached
    for status in ["all", "requested", "accepted", "cancelled"]:
        cache.delete_memoized(_get_manage_appointments_cached, user_type, status)


def invalidate_user_cache(cache, user_type):
    """
    Clear cached user views for an admin user by filter type.

    Args:
        cache (Cache): Flask-Caching instance.
        user_type (str): The admin's user type used for cache scoping.
    """
    from app.bp_admin.users import _get_manage_users_cached
    for filter_type in ["all", "clients", "professionals", "admins", "warned", "deactivated"]:
        cache.delete_memoized(_get_manage_users_cached, user_type, filter_type)


def flash_and_redirect(message, category, endpoint, **kwargs):
    """
    Flash a message and redirect to a given endpoint.

    Args:
        message (str): Flash message to show.
        category (str): Flash category (e.g., 'success', 'danger').
        endpoint (str): Target endpoint for redirection.
        **kwargs: Additional parameters for url_for.

    Returns:
        Response: Flask redirect response.
    """
    flash(message, category)
    return redirect(url_for(endpoint, **kwargs))


def make_context(title, heading=None):
    """
    Build a consistent context dictionary for template rendering.

    Args:
        title (str): Page title.
        heading (str, optional): Page heading. Defaults to title if not provided.

    Returns:
        dict: Context containing 'page_title' and 'main_heading'.
    """
    return {
        "page_title": title,
        "main_heading": heading or title
    }


def register_template_filters(bp):
    """
    Register Jinja2 template filters for formatting.

    Args:
        bp (Blueprint): The Flask blueprint to register the filter on.
    """
    @bp.app_template_filter('datetimeformat')
    def datetimeformat(value, fmt='%B %d, %Y - %I:%M %p'):
        """
        Format a datetime value for display in templates.

        Args:
            value (datetime|str): The datetime value to format.
            fmt (str): Format string.

        Returns:
            str: Formatted date string, or raw input if formatting fails.
        """
        if isinstance(value, datetime):
            return value.strftime(fmt)
        try:
            dt = datetime.strptime(str(value), '%Y-%m-%d %H:%M:%S')
            return dt.strftime(fmt)
        except Exception:
            return value
