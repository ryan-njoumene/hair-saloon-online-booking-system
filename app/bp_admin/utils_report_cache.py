from flask import render_template
from app import cache
from models.database import db
from .utils_admin import flash_and_redirect, make_context

@cache.memoize(timeout=60)
def _get_report_view_cached(report_id, return_type):
    """
    Cached helper function to render a specific report's details for admin view.

    Fetches the report by ID and renders the view_report template. If the report is not
    found, redirects with a flash message. The 'return_type' helps indicate the context
    to return to after viewing the report.

    Args:
        report_id (int): The ID of the report to retrieve.
        return_type (str): Contextual indicator for the back button or navigation state.

    Returns:
        str: Rendered HTML page for the report, or redirect if not found.
    """
    # Retrieve the report from the database
    report = db.get_report_by_id(report_id)
    if not report:
        return flash_and_redirect("Report not found.", "danger", "bp-admin.manage_reports")

    # Prepare context for the page
    context = make_context(f"Report #{report_id}", "Report Details")
    context["return_type"] = return_type

    # Render report view
    return render_template("reports/view_report.html", report=report, context=context)
