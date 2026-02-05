# bp_admin/reports.py

from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import cache
from . import bp_admin
from .forms import AddReport, EditReportForm
from app.bp_report.report import Report
from .utils_admin import role_required, flash_and_redirect, make_context
from models.database import db
from .utils_report_cache import _get_report_view_cached



@bp_admin.route("/manage_reports", methods=["GET", "POST"])
@login_required
@role_required("admin_appoint", "admin_super")
def manage_reports():
    """
    Admin route to manage all reports (create, view by status).

    Handles both GET and POST requests. On POST, creates a new report if the form is valid.
    On GET or after report creation, returns a filtered list of existing reports.

    Returns:
        Response: Rendered HTML page with report form and list of reports.
    """
    form = AddReport()

    # If form is submitted and valid, create a new report
    if form.validate_on_submit():
        try:
            Report.create({
                "appointment_id": form.appointment_id.data,
                "status": form.status.data,
                "feedback_client": form.feedback_client.data,
                "feedback_professional": form.feedback_professional.data
            })

            # Invalidate cached report list for the current filter
            cache.delete_memoized(
                _get_manage_reports_cached,
                current_user.user_type,
                request.args.get("status", "all")
            )

            flash("New Report was created successfully.", "success")
            return redirect(url_for("bp-admin.manage_reports"))

        except Exception as e:
            flash(f"Error creating Report: {e}", "danger")

    # Determine the status filter for report listing
    filter_status = request.args.get("status", "all")
    return _get_manage_reports_cached(current_user.user_type, filter_status, form=form)



@cache.memoize(timeout=60)
def _get_manage_reports_cached(user_type, filter_status, form=None):
    """
    Cached helper to fetch and render the Manage Reports page.

    Filters the list of reports based on the given status and returns a rendered HTML
    page with the filtered reports and the form for adding a new report.

    Args:
        user_type (str): Type of the current admin user (unused here but required for cache key uniqueness).
        filter_status (str): Status to filter reports by (e.g., "open", "closed", "flagged").
        form (AddReport, optional): Pre-bound AddReport form instance. A new one is created if not provided.

    Returns:
        str: Rendered HTML page for managing reports.
    """
    form = form or AddReport()
    reports = db.get_all_reports_with_details()

    # Apply filtering based on report status
    if filter_status == "flagged":
        reports = [r for r in reports if r["flagged_by_professional"]]
    elif filter_status == "open":
        reports = [r for r in reports if r["status"] in ("open", "grieve", "done")]
    elif filter_status == "closed":
        reports = [r for r in reports if r["status"] == "closed"]

    # Render the management page with the filtered reports and form
    return render_template(
        "reports/manage_reports.html",
        form=form,
        reports=reports,
        context=make_context("Manage Reports"),
        filter_status=filter_status
    )


@bp_admin.route("/edit_report/<int:report_id>", methods=["GET", "POST"])
@login_required
@role_required("admin_appoint", "admin_super")
def edit_report(report_id):
    """
    Admin route to edit an existing report.

    Retrieves the report by ID and pre-fills the form on GET.
    On POST, updates the report record and invalidates all relevant cache entries.

    Args:
        report_id (int): The ID of the report to be edited.

    Returns:
        Response: Redirects on success or renders the edit form with errors or pre-filled data.
    """
    # Retrieve the report record
    report = db.get_report_by_id(report_id)
    if not report:
        return flash_and_redirect("Report not found.", "danger", "bp-admin.manage_reports")

    form = EditReportForm()

    if form.validate_on_submit():
        # Update report with new values from the form
        db.execute("""
            UPDATE salon_report SET
                status = %s,
                feedback_client = %s,
                feedback_professional = %s,
                date_report = %s
            WHERE report_id = %s
        """, (
            form.status.data,
            form.client_feedback.data,
            form.professional_response.data,
            form.date_report.data,
            report_id
        ))

        # Invalidate all report management views (for each tab)
        for s in ["all", "open", "closed", "flagged"]:
            cache.delete_memoized(_get_manage_reports_cached, current_user.user_type, s)

        # Invalidate user dashboard cache if consumer ID is present
        if report.get("consumer_id"):
            cache.delete_memoized(_get_user_reports_cached, report["consumer_id"], "dashboard")

        # Invalidate individual report view cache
        cache.delete_memoized(_get_report_view_cached, report_id, "my")

        # Log the update action
        db.log_admin_action(f"Admin '{current_user.user_name}' edited report #{report_id}", current_user.user_name)

        flash("Report updated successfully.", "success")
        return redirect(url_for("bp-admin.manage_reports"))

    # Pre-fill form fields with current report values on GET
    form.status.data = report["status"]
    form.client_feedback.data = report["feedback_client"]
    form.professional_response.data = report["feedback_professional"]
    form.date_report.data = report["date"]

    return render_template(
        "reports/edit_report.html",
        form=form,
        report=report,
        context=make_context("Edit Report")
    )



@bp_admin.route("/delete_report/<int:report_id>", methods=["POST"])
@login_required
@role_required("admin_appoint", "admin_super")
def delete_report(report_id):
    """
    Admin route to delete a report by its ID.

    If the report exists, it is deleted from the database and all related cached views
    are invalidated. Handles errors gracefully with a flash message.

    Args:
        report_id (int): The ID of the report to delete.

    Returns:
        Response: Redirects to the manage reports page with a flash status.
    """
    # Retrieve the report to verify existence
    report = db.get_report_by_id(report_id)
    if not report:
        return flash_and_redirect("Report not found.", "warning", "bp-admin.manage_reports")

    try:
        # Attempt to delete the report
        db.delete_report(report_id)

        # Invalidate all cached report lists (for different status filters)
        for s in ["all", "open", "closed", "flagged"]:
            cache.delete_memoized(_get_manage_reports_cached, current_user.user_type, s)

        # Invalidate user report dashboard cache if consumer ID is known
        if report.get("consumer_id"):
            cache.delete_memoized(_get_user_reports_cached, report["consumer_id"], "dashboard")

        # Invalidate the single report view cache
        cache.delete_memoized(_get_report_view_cached, report_id, "my")

        flash("Report deleted successfully.", "success")
    except Exception as e:
        flash(f"Error deleting report: {e}", "danger")

    return redirect(url_for("bp-admin.manage_reports"))



@bp_admin.route("/view_report/<int:report_id>")
@login_required
@role_required("admin_appoint", "admin_super")
def view_report(report_id):
    """
    Admin route to view the details of a specific report.

    Args:
        report_id (int): The ID of the report to view.

    Returns:
        str: Rendered HTML page with report details.
    """
    return _get_view_report_cached(report_id)


@cache.memoize(timeout=60)
def _get_view_report_cached(report_id):
    """
    Cached helper function to fetch and render a single report's details.

    Args:
        report_id (int): The ID of the report to retrieve.

    Returns:
        str: Rendered HTML of the report view page, or redirect if not found.
    """
    report = db.get_report_by_id(report_id)
    if not report:
        return flash_and_redirect("Report not found.", "danger", "bp-admin.manage_reports")

    return render_template(
        "reports/view_report.html",
        report=report,
        context=make_context(f"Report #{report_id}", "Report Details")
    )


@bp_admin.route("/view_user_reports/<int:user_id>")
@login_required
def view_user_reports(user_id):
    """
    Admin route to view all reports associated with a specific user.

    Args:
        user_id (int): ID of the user whose reports are being viewed.

    Returns:
        str: Rendered HTML list of the user's reports.
    """
    return_to = request.args.get("return_to", "dashboard")
    return _get_user_reports_cached(user_id, return_to)


@cache.memoize(timeout=60)
def _get_user_reports_cached(user_id, return_to):
    """
    Cached helper to render all reports linked to a user's appointments.

    Args:
        user_id (int): ID of the user whose reports to fetch.
        return_to (str): Context of return path for navigation ("dashboard", etc.).

    Returns:
        str: Rendered HTML page listing the user's reports.
    """
    user = db.get_user_by_id(user_id)
    if not user:
        return flash_and_redirect("User not found.", "danger", "bp-admin.manage_users")

    # Gather all appointments and fetch their corresponding reports
    appointments = db.get_appointments_by_user(user_id)
    reports = [
        db.get_report_by_appointment(a["appointment_id"])
        for a in appointments
        if db.get_report_by_appointment(a["appointment_id"])
    ]

    return render_template(
        "reports/view_user_reports.html",
        reports=reports,
        context=make_context(
            f"Reports for {user[4]}",  # user_name
            f"Reports - {user[5]} {user[6]}"  # fname + lname
        ),
        user=user,
        return_to=return_to
    )
