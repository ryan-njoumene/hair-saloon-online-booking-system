from flask import render_template
from flask_login import login_required
from app import cache
from . import bp_admin
from models.database import db
from .utils_admin import role_required


@bp_admin.route("/dashboard")
@login_required
@role_required("admin_user", "admin_super", "admin_appoint")
def dashboard():
    """
    Admin route for the main dashboard.

    Displays a cached view of the dashboard page for authorized admin roles.

    Returns:
        str: Rendered HTML for the dashboard.
    """
    return _get_dashboard_cached()


@cache.cached(timeout=60)
def _get_dashboard_cached():
    """
    Cached helper to render the admin dashboard.

    Returns:
        str: Rendered HTML for the dashboard view.
    """
    return render_template("dashboard.html")


@bp_admin.route("/admin_logs")
@login_required
@role_required("admin_super")
def admin_logs():
    """
    Superadmin route to view administrative action logs.

    Returns:
        str: Rendered HTML page showing a list of admin actions.
    """
    return _get_admin_logs_cached()


@cache.cached(timeout=60)
def _get_admin_logs_cached():
    """
    Cached helper to fetch and render the admin logs page.

    Retrieves user actions from the salon_log table.

    Returns:
        str: Rendered HTML page with a list of admin logs.
    """
    logs = db.fetch("""
        SELECT user_action, action_by, action_time 
        FROM salon_log 
        ORDER BY action_time DESC
    """)
    return render_template("admin_logs.html", logs=logs)
