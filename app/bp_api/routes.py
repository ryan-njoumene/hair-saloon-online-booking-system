from flask import jsonify, request, render_template
from flask_login import login_required, current_user
from functools import wraps
from . import bp_api
from models.database import db
from app import cache
from flask_jwt_extended import get_jwt, jwt_required, get_jwt_identity

# === Decorators ===
def roles_required(*roles):
    """
    API decorator to restrict access to specific user roles.

    If the current user’s role is not in the allowed list, a 403 JSON response is returned.

    Args:
        *roles (str): One or more user_type strings that are authorized (e.g., "admin_super").

    Returns:
        function: Wrapped view function with role enforcement.
    """
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if current_user.user_type not in roles:
                return jsonify({"error": "Unauthorized"}), 403
            return f(*args, **kwargs)
        return wrapped
    return decorator


# === Cache Invalidation Helpers ===
def invalidate_appointment_cache(appt_id=None):
    """
    Invalidate cached appointment data.

    Clears the global appointment list cache. If an appointment ID is provided,
    also clears the individual appointment cache.

    Args:
        appt_id (int, optional): ID of a specific appointment to invalidate.
    """
    cache.delete_memoized(_get_appointments_cached)
    if appt_id:
        cache.delete_memoized(_get_single_appointment_cached, appt_id)


def invalidate_report_cache(user_type=None, user_id=None, report_id=None):
    """
    Invalidate cached report data.

    Clears cached user-specific report lists and individual report details.

    Args:
        user_type (str, optional): User type (e.g., "client", "professional").
        user_id (int, optional): ID of the user whose reports should be cleared.
        report_id (int, optional): ID of a single report to clear from cache.
    """
    if user_type and user_id:
        cache.delete_memoized(_get_reports_cached, user_type, user_id)
    if report_id:
        cache.delete_memoized(_get_single_report_cached, report_id)


# === Routes ===

@bp_api.route("/")
def docs():
    """
    Public route for viewing the API documentation.

    Returns:
        str: Rendered HTML page with API documentation.
    """
    return render_template("api_docs.html")


# === USERS ===

@bp_api.route("/users", methods=["GET"])
def get_users():
    """
    API route to retrieve a list of all users.

    Returns:
        JSON: List of all users with basic identifying information.
    """
    return _get_users_cached()


@cache.cached(timeout=120)
def _get_users_cached():
    """
    Cached helper to fetch all users.

    Returns:
        JSON: Cached response with list of users.
    """
    return jsonify(db.get_all_users())


@bp_api.route("/users/<int:user_id>", methods=["GET"])
def get_single_user(user_id):
    """
    API route to retrieve details of a single user by ID.

    Args:
        user_id (int): The ID of the user to fetch.

    Returns:
        JSON: User object if found, or 404 error message.
    """
    return _get_single_user_cached(user_id)


@cache.memoize(timeout=120)
def _get_single_user_cached(user_id):
    """
    Cached helper to fetch a single user by ID.

    Args:
        user_id (int): ID of the user to fetch.

    Returns:
        JSON: User data or 404 error message.
    """
    user = db.get_user_by_id(user_id)
    return jsonify(user) if user else (jsonify({"error": "User not found"}), 404)


# === APPOINTMENTS ===

@bp_api.route("/appointments", methods=["GET"])
def get_appointments():
    """
    API route to retrieve all appointments.

    Returns:
        JSON: List of all appointments with associated details.
    """
    return _get_appointments_cached()


@cache.cached(timeout=60)
def _get_appointments_cached():
    """
    Cached helper to fetch all appointments.

    Returns:
        JSON: Cached list of appointment records.
    """
    return jsonify(db.get_all_appointments())


@bp_api.route("/appointments/<int:appt_id>", methods=["GET"])
def get_single_appointment(appt_id):
    """
    API route to retrieve a single appointment by ID.

    Args:
        appt_id (int): ID of the appointment to retrieve.

    Returns:
        JSON: Appointment data if found, otherwise a 404 error.
    """
    return _get_single_appointment_cached(appt_id)


@cache.memoize(timeout=60)
def _get_single_appointment_cached(appt_id):
    """
    Cached helper to fetch a single appointment by ID.

    Args:
        appt_id (int): ID of the appointment.

    Returns:
        JSON: Appointment object or a 404 error message.
    """
    appt = db.get_appointment_by_id(appt_id)
    return jsonify(appt) if appt else (jsonify({"error": "Appointment not found"}), 404)


@bp_api.route("/appointments", methods=["POST"])
def api_create_appointment():
    """
    API endpoint to create a new appointment.

    Expects a JSON payload with required fields. If valid, creates the appointment
    and returns the newly generated appointment ID.

    Returns:
        JSON: 201 with appointment_id on success, or 400/500 with error message.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing JSON body"}), 400

    # Validate required fields
    required = ["consumer_id", "provider_id", "consumer_name", "provider_name"]
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    try:
        # Create appointment in the database
        appt_id = db.add_appointment(data)

        # Invalidate cache so it reflects the new data
        invalidate_appointment_cache()

        return jsonify({"appointment_id": appt_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp_api.route("/appointments/<int:appt_id>", methods=["PUT"])
def api_update_appointment(appt_id):
    """
    API endpoint to update an existing appointment.

    Expects a JSON payload with the fields to update. If successful,
    returns a success message. Handles error and validation gracefully.

    Args:
        appt_id (int): The ID of the appointment to update.

    Returns:
        JSON: Success status or error message.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing JSON body"}), 400

    try:
        # Update appointment record in the database
        db.update_appointment(appt_id, data)

        # Invalidate the specific appointment cache
        invalidate_appointment_cache(appt_id)

        return jsonify({"status": "Appointment updated"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp_api.route("/appointments/<int:appt_id>", methods=["DELETE"])
def api_delete_appointment(appt_id):
    """
    API endpoint to delete an appointment by ID.

    Attempts to remove the appointment from the database and clear related caches.

    Args:
        appt_id (int): ID of the appointment to delete.

    Returns:
        JSON: Success status message or 500 error on failure.
    """
    try:
        # Delete the appointment from the database
        db.delete_appointment(appt_id)

        # Invalidate relevant appointment cache
        invalidate_appointment_cache(appt_id)

        return jsonify({"status": "Appointment deleted"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# === REPORTS ===

@bp_api.route("/reports", methods=["GET"])
def get_reports():
    """
    Public API route to retrieve all reports.

    This version does NOT require login and will return all reports,
    similar to the appointments and users endpoints.
    """
    reports = db.get_all_report()
    return jsonify(reports), 200



@cache.memoize(timeout=60)
def _get_reports_cached(user_type, user_id):
    """
    Cached helper to fetch reports for a user based on their role.

    Args:
        user_type (str): The type of the current user (client, professional, admin).
        user_id (int): The ID of the user making the request.

    Returns:
        JSON: List of reports or error response.
    """
    if user_type == "client":
        reports = db.get_reports_by_client(user_id)
    elif user_type == "professional":
        reports = db.get_reports_by_professional(user_id)
    elif user_type.startswith("admin"):
        reports = db.get_all_report()
    else:
        return jsonify({"error": "Unauthorized user type"}), 403

    return jsonify(reports), 200


@bp_api.route("/reports/<int:report_id>", methods=["GET"])
def api_get_report(report_id):
    """
    API route to retrieve a single report by ID.

    Args:
        report_id (int): ID of the report to retrieve.

    Returns:
        JSON: Report data if found, or a 404 error message.
    """
    return _get_single_report_cached(report_id)


@cache.memoize(timeout=60)
def _get_single_report_cached(report_id):
    """
    Cached helper to fetch a single report by ID.

    Args:
        report_id (int): ID of the report.

    Returns:
        JSON: Report data or 404 error message.
    """
    report = db.get_report_by_id(report_id)
    return jsonify(report) if report else (jsonify({"error": "Report not found"}), 404)


@bp_api.route("/reports", methods=["POST"])
def api_create_report():
    """
    API endpoint to create a new report.

    Expects a JSON body containing appointment_id, feedback_client, and feedback_professional.
    Creates the report and returns the new report_id on success.

    Returns:
        JSON: 201 response with report_id, or 400/500 error message.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing JSON body"}), 400

    # Validate required fields
    required = ["appointment_id", "feedback_client", "feedback_professional"]
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    try:
        # Add report to the database
        report_id = db.add_report(data)

        # Invalidate cached report list for the user
        invalidate_report_cache(current_user.user_type, current_user.id)

        return jsonify({"report_id": report_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp_api.route("/reports/<int:report_id>", methods=["PUT"])
def api_update_report(report_id):
    """
    API endpoint to update an existing report.

    Expects a JSON body with at least one of the following fields:
    feedback_client, feedback_professional, or status.

    Args:
        report_id (int): The ID of the report to update.

    Returns:
        JSON: Success message or error message.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing JSON body"}), 400

    # Ensure at least one updatable field is provided
    if not any(field in data for field in ["feedback_client", "feedback_professional", "status"]):
        return jsonify({"error": "At least one field must be provided"}), 400

    try:
        # Apply update to the report
        db.update_report(report_id, data)

        # Invalidate relevant cached entries
        invalidate_report_cache(current_user.user_type, current_user.id, report_id)

        return jsonify({"status": "Report updated"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp_api.route("/reports/<int:report_id>", methods=["DELETE"])
def api_delete_report(report_id):
    """
    API endpoint to delete a report by ID.

    Deletes the specified report from the database and invalidates any related caches.

    Args:
        report_id (int): The ID of the report to delete.

    Returns:
        JSON: Success message or error details.
    """
    try:
        # Delete the report from the database
        db.delete_report(report_id)

        # Invalidate all related report caches
        invalidate_report_cache(current_user.user_type, current_user.id, report_id)

        return jsonify({"status": "Report deleted"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp_api.route("/secret", methods=["GET"])
@jwt_required()
def secret_stuff():
    """
    JWT-protected route to demonstrate access to secure resources.

    Returns a personalized welcome message using JWT claims.

    Returns:
        dict: Welcome message with the user's ID and username.
    """
    claims = get_jwt()
    user_id = get_jwt_identity()
    username = claims.get("username")

    return {
        "message": f"Welcome, user #{user_id} ({username})!"
    }
