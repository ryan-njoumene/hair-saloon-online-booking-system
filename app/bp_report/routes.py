from flask import render_template, flash, redirect, request, url_for, abort
from flask_login import login_required, current_user
from .report import Report
from .forms import ClientReportForm, ProfessionalReportForm
from models.database import db
from app import cache
from flask import Blueprint

bp_report = Blueprint("bp-report", __name__, template_folder="templates", static_folder="static", static_url_path='/bp_report/static/')

# === Utilities ===
def invalidate_report_caches(report_id=None):
    """
    Invalidate cached report data to ensure fresh data retrieval.

    This function clears memoized caches for user reports and optionally
    clears specific caches for individual reports if a report ID is provided.

    Args:
        report_id (int, optional): Specific report ID whose cache should be cleared.
            Defaults to None.
    """
    # Clear cached user reports based on current user details
    cache.delete_memoized(_get_user_reports_cached, current_user.id, current_user.user_type)

    if report_id:
        # Clear cache for the specific report detail
        cache.delete_memoized(_get_report_cached, report_id)
        # Clear cache for the detailed view of the report in 'my_reports' context
        cache.delete_memoized(_get_report_view_cached, report_id, "my_reports")


# === Routes ===
@bp_report.route("/my-reports")
@login_required
def my_reports():
    """
    Display paginated reports relevant to the logged-in user.

    Retrieves reports for the current user (client or professional),
    paginated according to the provided 'page' parameter.

    Query Parameters:
        page (int, optional): Page number for pagination. Defaults to 1.

    Returns:
        Response: Rendered template displaying the user's reports.
    """
    # Retrieve 'page' argument from URL, defaulting to 1 if not provided
    page = request.args.get("page", 1, type=int)

    # Fetch cached reports for the current user based on user type and page number
    return _get_user_reports_cached(current_user.id, current_user.user_type, page)



@cache.memoize(timeout=60)
def _get_user_reports_cached(user_id, user_type, page=1):
    """
    Retrieve and cache paginated reports for a specific user.

    Args:
        user_id (int): ID of the user whose reports are retrieved.
        user_type (str): Type of the user ('client', 'professional', etc.).
        page (int, optional): Current page number for pagination. Defaults to 1.

    Returns:
        Response: Rendered template displaying paginated reports.
    """
    reports_per_page = 5

    # Fetch all reports associated with the given user
    all_reports = db.get_reports_by_user(user_id)

    # Calculate total number of pages needed for pagination
    total_pages = max(1, -(-len(all_reports) // reports_per_page))

    # Calculate start and end indices for slicing reports list
    start = (page - 1) * reports_per_page
    end = start + reports_per_page

    # Select reports for the current page
    reports = all_reports[start:end]

    # Structure report data into dictionaries suitable for rendering
    reports_dicts = [
        {
            "report_id": r["report_id"],
            "appointment_id": r["appointment_id"],
            "status": r["status"],
            "feedback_client": r["feedback_client"],
            "feedback_professional": r["feedback_professional"],
            "date_report": r["date_report"],
            "flagged_by_professional": r.get("flagged_by_professional")
        }
        for r in reports
    ]

    # Render the template with paginated reports
    return render_template(
        "my_reports.html",
        reports_list=reports_dicts,
        main_heading="My Reports",
        current_page=page,
        total_pages=total_pages
    )




@bp_report.route("/create_reports", methods=["GET", "POST"])
@login_required
def create_reports():
    """
    Handle the creation of new reports by clients.

    GET: Display a form for creating a new client feedback report.
         Optionally prefill the appointment ID if provided in query parameters.

    POST: Validate form input and create a new report in the database.

    Query Parameters:
        appointment_id (int, optional): Appointment ID to prefill in the form.

    Returns:
        Response: Rendered template for report creation or redirect after successful submission.
    """
    # Initialize the form for client feedback report creation
    form = ClientReportForm()

    # Retrieve optional prefill parameter from query string
    prefill = request.args.get("appointment_id", type=int)
    if prefill:
        form.appointment_id.data = prefill

    # Handle form submission
    if form.validate_on_submit():
        try:
            # Create a new report with the provided data
            Report.create({
                "appointment_id": form.appointment_id.data,
                "status": "open",
                "feedback_client": form.feedback_client.data
            })

            # Invalidate cached reports to reflect new data
            invalidate_report_caches()

            flash("Report created!", "success")
            return redirect(url_for("bp-report.my_reports"))

        except Exception as e:
            flash(f"Report Creation error: {e}", "danger")

    # Render the report creation form template
    return render_template(
        "create_report.html",
        form=form,
        page_title="New Report",
        main_heading="Create Report",
        locked_appointment_id=prefill
    )



@bp_report.route("/report/<id>")
@login_required
def report(id):
    """
    Display a specific report identified by its ID.

    Args:
        id (int): The unique identifier of the report to display.

    Returns:
        Response: Rendered template showing detailed report information.
    """
    return _get_report_cached(id)


@cache.memoize(timeout=60)
def _get_report_cached(report_id):
    """
    Retrieve and cache a report by its ID.

    Fetches the report from the database. If the report does not exist,
    a 404 error is raised.

    Args:
        report_id (int): Unique identifier of the report.

    Returns:
        Response: Rendered template displaying report details.

    Raises:
        HTTPException: 404 error if the report is not found.
    """
    # Attempt to retrieve the report by ID from the database
    if not (report := Report.get_report_by_id(report_id)):
        abort(404, description=f"Report {report_id} does not exist.")

    # Render the template with report details
    return render_template(
        "report.html",
        page_title=f"Report {report_id}",
        main_heading=f"View Report {report_id}",
        report=report
    )


@bp_report.route("/respond/<int:report_id>", methods=["GET", "POST"])
@login_required
def respond_to_report(report_id):
    """
    Allow professionals to respond to a client-submitted report.

    GET: Display a form prefilled with the client's feedback, enabling the professional to respond.
    POST: Validate and submit the professional's response to the report.

    Args:
        report_id (int): Unique identifier of the report to respond to.

    Returns:
        Response: Rendered response form or a redirect after submission.
    """
    # Ensure the user is a professional
    if current_user.user_type != "professional":
        flash("Unauthorized access", "danger")
        return redirect(url_for("bp-main.home"))

    # Retrieve report from the database
    report = db.get_report_by_id(report_id)
    if not report:
        flash("Report not found", "danger")
        return redirect(url_for("bp-main.home"))

    # Attach report_id explicitly for template use
    report["report_id"] = report_id

    # Initialize form for professional response
    form = ProfessionalReportForm()

    # Prefill form with existing report data on initial page load (GET request)
    if request.method == "GET":
        form.appointment_id.data = report["appointment_id"]
        form.feedback_client.data = report["feedback_client"]
        form.feedback_professional.data = report["feedback_professional"]
        form.status.data = report["status"]

    # Handle form submission (POST request)
    if form.validate_on_submit():
        # Update report with professional's response
        db.update_report(report_id, {
            "feedback_professional": form.feedback_professional.data,
            "status": form.status.data
        })

        # Mark report as updated, notifying the client
        db.mark_report_client_notified(report_id)

        # Invalidate cached report data to reflect recent changes
        invalidate_report_caches(report_id)

        flash("Your response has been submitted.", "success")
        return redirect(url_for("bp-report.my_reports"))

    # Render response form template
    return render_template("respond_report.html", form=form, report=report)


@bp_report.route("/report/view/<int:report_id>")
@login_required
def view_report(report_id):
    """
    Display a detailed view of a specific report.

    Args:
        report_id (int): Unique identifier for the report to view.

    Query Parameters:
        return_to (str, optional): Endpoint to return to after viewing the report.

    Returns:
        Response: Rendered template displaying the detailed report view.
    """
    # Retrieve the 'return_to' parameter from the URL query string
    return_to = request.args.get("return_to")

    # Fetch and return cached detailed report view
    return _get_report_view_cached(report_id, return_to)


@cache.memoize(timeout=60)
def _get_report_view_cached(report_id, return_to):
    """
    Fetch a specific report's detailed view and cache the result.

    Args:
        report_id (int): ID of the report to retrieve.
        return_to (str): The endpoint to redirect back after viewing the report.

    Returns:
        Response: Rendered report view template or a redirect if not found.
    """
    # Retrieve the report from the database
    report = db.get_report_by_id(report_id)

    # Handle case where the report does not exist
    if not report:
        flash("Report not found.", "danger")
        return redirect(url_for("bp-report.my_reports"))

    # Explicitly attach report ID for use in the template
    report["report_id"] = report_id

    # Render the report view template with appropriate context
    return render_template(
        "report_view.html",
        report=report,
        return_to=return_to,
        main_heading=f"Report #{report_id}"
    )


@bp_report.route("/flag/<int:report_id>", methods=["POST"])
@login_required
def flag_report(report_id):
    """
    Allow a professional to flag a report for admin review.

    Args:
        report_id (int): Unique identifier of the report to flag.

    Form Data:
        return_to (str, optional): Endpoint to redirect to after action.
                                   Defaults to 'my_reports'.

    Returns:
        Response: Redirect to the specified endpoint after flagging.
    """
    # Verify user authorization
    if current_user.user_type != "professional":
        flash("Unauthorized access", "danger")
        return redirect(url_for("bp-main.home"))

    # Retrieve the return endpoint from form data
    return_to = request.form.get("return_to", "my_reports")

    try:
        # Flag the report in the database
        db.flag_report_by_professional(report_id)
        # Invalidate cache to reflect updated report status
        invalidate_report_caches(report_id)
        flash("You have flagged this report for admin review.", "warning")
    except Exception as e:
        flash(f"Error flagging report: {e}", "danger")

    # Redirect after performing the flag action
    return _redirect_report_action(report_id, return_to)


@bp_report.route("/unflag/<int:report_id>", methods=["POST"])
@login_required
def unflag_report(report_id):
    """
    Allow a professional to remove the flag from a previously flagged report.

    Args:
        report_id (int): Unique identifier of the report to unflag.

    Form Data:
        return_to (str, optional): Endpoint to redirect to after action.
                                   Defaults to 'my_reports'.

    Returns:
        Response: Redirect to the specified endpoint after unflagging.
    """
    # Verify user authorization
    if current_user.user_type != "professional":
        flash("Unauthorized access", "danger")
        return redirect(url_for("bp-main.home"))

    # Retrieve the return endpoint from form data
    return_to = request.form.get("return_to", "my_reports")

    try:
        # Unflag the report in the database
        db.unflag_report_by_professional(report_id)
        # Invalidate cache to reflect updated report status
        invalidate_report_caches(report_id)
        flash("You have unflagged this report.", "info")
    except Exception as e:
        flash(f"Error unflagging report: {e}", "danger")

    # Redirect after performing the unflag action
    return _redirect_report_action(report_id, return_to)


def _redirect_report_action(report_id, return_to):
    """
    Helper function to handle redirection after report actions.

    Args:
        report_id (int): Unique identifier of the relevant report.
        return_to (str): Target endpoint for redirection.

    Returns:
        Response: Redirect to the appropriate endpoint based on context.
    """
    # Redirect logic based on specified return endpoint
    if return_to == "respond_report":
        return redirect(url_for("bp-report.respond_to_report", report_id=report_id))
    elif return_to == "view_report":
        return redirect(url_for("bp-report.view_report", report_id=report_id, return_to="my_reports"))

    # Default redirection to 'my_reports' if unspecified or unknown
    return redirect(url_for("bp-report.my_reports"))
