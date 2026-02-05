from flask import render_template, redirect, url_for, flash, request
from datetime import date
from flask_login import login_required, current_user

from app.bp_admin.utils_admin import flash_and_redirect, make_context
from . import bp_appointment
from models.database import db
from .forms import ModifyAppointmentForm, CreateAppointmentForm
from types import SimpleNamespace
from app import cache

# === Constants ===

# Dropdown choices for appointment venues
VENUES = [
    ("room1", "Room 1"),
    ("room2", "Room 2"),
    ("chair1", "Chair 1"),
    ("chair2", "Chair 2"),
    ("cmn_room", "Common Room")
]

# Time slot options (1–11 AM and 1–9 PM)
SLOTS = [(f"{h}-{h+1}", f"{h}-{h+1}") for h in list(range(1, 12)) + list(range(13, 22))]

# Extract only the slot values (e.g., "1-2", "13-14")
ALL_SLOTS = [slot[0] for slot in SLOTS]


# === Helpers ===

def get_pay_rates(provider_choices):
    """
    Construct a dictionary mapping provider IDs to their pay rates.

    If a provider has no rate stored, the default is 15.75.

    Args:
        provider_choices (list): List of tuples (provider_id, display_name)

    Returns:
        dict: Mapping from provider_id to pay_rate
    """
    return {
        pid: db.get_user_by_id(pid)[14] or 15.75  # pay_rate is at index 14
        for pid, _ in provider_choices if pid != -1
    }


# === Utility Functions ===

def invalidate_my_appt_cache():
    """
    Invalidate appointment cache entries for the currently logged-in user.

    Clears both personal appointment list and global list views.
    """
    cache.delete_memoized(_get_my_appointments_cached, current_user.id, current_user.user_type, 1)
    cache.delete_memoized(list_all_appointments)


def paginate(data, page, per_page):
    """
    Paginate a list of data.

    Args:
        data (list): The full list of items to paginate.
        page (int): Current page number (1-based).
        per_page (int): Number of items per page.

    Returns:
        tuple: (paginated subset, total number of pages)
    """
    total = len(data)
    total_pages = (total + per_page - 1) // per_page
    return data[(page - 1) * per_page : page * per_page], total_pages


# === Routes ===

@bp_appointment.route("/my-appointments")
@login_required
def my_appointments():
    """
    Route for clients and professionals to view their own appointments.

    Paginated view, based on the 'page' query parameter.

    Returns:
        str: Rendered HTML page showing a list of appointments.
    """
    page = request.args.get("page", 1, type=int)
    return _get_my_appointments_cached(current_user.id, current_user.user_type, page)



@cache.memoize(timeout=60)
def _get_my_appointments_cached(user_id, user_type, page):
    per_page = 5

    # Determine which appointments to fetch based on user type
    if user_type == "client":
        appts = db.get_appointments_by_client(user_id)
    elif user_type == "professional":
        appts = db.get_appointments_by_professional(user_id)
    else:
        appts = db.get_appointments_by_user(user_id)  # Fallback for admin types

    print(f"[DEBUG] Total appointments for user {user_id}: {len(appts)}")

    # Paginate the appointment list
    paginated, total_pages = paginate(appts, page, per_page)

    print(f"[DEBUG] Appointments on page {page}: {len(paginated)}")

    result = [
        SimpleNamespace(**{
            **a,
            "can_write_report": (
                user_type == "client"
                and a["date_appoint"] < date.today()
                and not db.has_report_for_appointment(a["appointment_id"])
            )
        })
        for a in paginated
    ]

    return render_template(
        "my_appointments.html",
        appointments=result,
        total_pages=total_pages,
        current_page=page
    )



@bp_appointment.route("/create", methods=["GET", "POST"])
@login_required
def create_appointment():
    """
    Route for clients to create a new appointment.

    Displays a form to schedule an appointment with a professional.
    On POST, the form data is validated and the appointment and service
    are inserted into the database. Pay rate is determined dynamically,
    and relevant caches are invalidated after creation.

    Returns:
        str or Response: Rendered form on GET or failed POST,
                         redirect on successful submission.
    """
    form = CreateAppointmentForm()

    # Populate dropdowns with professionals and predefined slots/venues
    professionals = db.get_all_professionals_with_names()
    form.provider_id.choices = [(-1, 'Select a professional')] + [
        (p["user_id"], f"{p['fname']} {p['lname']} [id:{p['user_id']}]") for p in professionals
    ]
    form.venue.choices = VENUES
    form.slot.choices = SLOTS

    # Build pay rate lookup for pricing calculation
    pay_rates = {
        p["user_id"]: db.get_user_by_id(p["user_id"])[14] or 15.75 for p in professionals
    }

    if form.validate_on_submit():
        try:
            # Get selected provider's full record
            provider = db.get_user_by_id(form.provider_id.data)

            # Create appointment record
            appoint_id = db.add_appointment({
                "consumer_id": current_user.id,
                "provider_id": provider[0],
                "consumer_name": f"{current_user.fname} {current_user.lname}",
                "provider_name": f"{provider[5]} {provider[6]}",  # fname, lname
                "status": "requested",
                "approved": 0,
                "date_appoint": form.date_appoint.data,
                "slot": form.slot.data,
                "venue": form.venue.data,
                "nber_services": 1,
                "consumer_report": None,
                "provider_report": None
            })

            # Create linked service record
            db.add_service({
                "appointment_id": appoint_id,
                "service_name": form.service_name.data,
                "service_duration": form.service_duration.data,
                "service_price": float(form.service_duration.data) * float(pay_rates.get(form.provider_id.data, 15.75)),
                "service_materials": None
            })

            # Invalidate cache so new appointment appears in views
            invalidate_my_appt_cache()

            flash("Appointment created successfully", "success")
            return redirect(url_for("bp-appointment.my_appointments"))

        except Exception as e:
            flash(f"Error creating appointment: {e}", "danger")

    # Render form on GET or form validation failure
    return render_template("create_appointment.html", form=form, pay_rates=pay_rates)


@bp_appointment.route("/view_appointment/<int:appointment_id>")
@login_required
def view_appointment(appointment_id):
    appointment = db.get_appointment_by_id(appointment_id)

    if not appointment:
        flash("Appointment not found.", "danger")
        return redirect(url_for("bp-appointment.my_appointments"))

    # ✅ Check that only the correct client/professional/admin can view
    if current_user.user_type == "client" and appointment["consumer_id"] != current_user.id:
        return flash_and_redirect("You are not authorized to view this appointment.", "danger", "bp-appointment.my_appointments")

    if current_user.user_type == "professional" and appointment["provider_id"] != current_user.id:
        return flash_and_redirect("You are not authorized to view this appointment.", "danger", "bp-appointment.my_appointments")

    return render_template(
        "view_my_appointment.html",
        main_heading=f"View Appointment #{appointment_id}",
        appointment=appointment,
        return_to=request.args.get("return_to", "all")
    )



@bp_appointment.route("/list_all_appointments")
@cache.cached(timeout=60, query_string=True)
def list_all_appointments():
    """
    Route to display a paginated and filterable list of all appointments.

    Admins and users can view appointments filtered by status (requested, approved, cancelled)
    and sorted by a given field (e.g., date_appoint). Results are paginated, and
    the output is cached per unique query string.

    Query Params:
        status (str): Filter by appointment status ('all', 'requested', 'approved', 'cancelled').
        sort (str): Field to sort by (e.g., 'date_appoint').
        page (int): Page number for pagination.

    Returns:
        str: Rendered HTML template with paginated, sorted, and filtered appointments.
    """
    status_map = {
        "all": None,
        "requested": "requested",
        "approved": "accepted",
        "cancelled": "cancelled"
    }

    # Get query parameters
    filter_status = request.args.get("status", "all")
    sort_by = request.args.get("sort", "date_appoint")
    page = request.args.get("page", 1, type=int)

    # Fetch all appointments
    appts = db.get_all_appointments()

    # Filter based on selected status
    if status_map[filter_status]:
        filtered = [a for a in appts if a["status"] == status_map[filter_status]]
    else:
        filtered = appts

    # Sort the appointments by the requested field
    filtered.sort(key=lambda x: x.get(sort_by, x.get("date_appoint")))

    # Paginate the sorted list
    paginated, total_pages = paginate(filtered, page, 5)

    # Render the appointment list view
    return render_template(
        "list_all_appointments.html",
        appointments=paginated,
        total_pages=total_pages,
        current_page=page,
        status_filter=filter_status,
        sort_by=sort_by,
        current_user=current_user
    )


@bp_appointment.route("/accept/<int:appointment_id>", methods=["POST"])
@login_required
def accept_appointment(appointment_id):
    """
    Route for a professional to accept a requested appointment.

    Only the provider assigned to the appointment may accept it.
    If authorized, the appointment status is updated to 'accepted'
    and related caches are invalidated.

    Args:
        appointment_id (int): ID of the appointment to accept.

    Returns:
        Response: Redirects to the appointment detail view with a flash message.
    """
    # Retrieve the appointment
    appointment = db.get_appointment_by_id(appointment_id)

    # Validate access: only the provider can accept the appointment
    if not appointment or current_user.id != appointment["provider_id"]:
        flash("You are not authorized to accept this appointment.", "danger")
        return redirect(url_for("bp-appointment.view_appointment", appointment_id=appointment_id))

    # Update appointment status to 'accepted'
    appointment["status"] = "accepted"
    db.update_appointment(appointment_id, appointment)

    # Invalidate appointment caches
    invalidate_my_appt_cache()

    flash("Appointment accepted.", "success")
    return redirect(url_for("bp-appointment.view_appointment", appointment_id=appointment_id))


@bp_appointment.route("/cancel/<int:appointment_id>", methods=["POST"])
@login_required
def cancel_appointment(appointment_id):
    """
    Route for clients or professionals to cancel a requested appointment.

    Only users directly involved in the appointment (consumer or provider)
    are authorized to cancel it, and only if the appointment is still in
    'requested' status.

    Args:
        appointment_id (int): ID of the appointment to cancel.

    Returns:
        Response: Redirects to the appointment view with a flash message.
    """
    # Retrieve appointment record
    appointment = db.get_appointment_by_id(appointment_id)
    if not appointment:
        flash("Appointment not found.", "danger")
        return redirect(url_for("bp-appointment.list_all_appointments"))

    # Authorization: must be the consumer or provider
    if current_user.id not in [appointment["provider_id"], appointment["consumer_id"]]:
        flash("You are not authorized to cancel this appointment.", "danger")
        return redirect(url_for("bp-appointment.view_appointment", appointment_id=appointment_id))

    # Only requested appointments can be cancelled
    if appointment["status"] != "requested":
        flash("Only requested appointments can be cancelled.", "warning")
        return redirect(url_for("bp-appointment.view_appointment", appointment_id=appointment_id))

    # Update status and invalidate cache
    db.update_appointment_status(appointment_id, "cancelled")
    invalidate_my_appt_cache()

    flash("Appointment cancelled.", "info")
    return redirect(url_for("bp-appointment.view_appointment", appointment_id=appointment_id))



@bp_appointment.route("/delete/<int:appointment_id>", methods=["POST"])
@login_required
def delete_appointment(appointment_id):
    """
    Route to delete an appointment.

    Only the client, provider, or an admin can delete an appointment.
    Deletion is blocked if the appointment is linked to a report.

    Args:
        appointment_id (int): ID of the appointment to delete.

    Query Params:
        return_to (str): Determines which view to return to after deletion ("my" or "all").

    Returns:
        Response: Redirect to the appropriate appointments list with a flash message.
    """
    # Retrieve the appointment
    appointment = db.get_appointment_by_id(appointment_id)
    if not appointment:
        flash("Appointment not found.", "danger")
        return redirect(url_for("bp-appointment.list_all_appointments"))

    # Determine if user is authorized to delete (owner or admin)
    is_owner = current_user.id in [appointment["consumer_id"], appointment["provider_id"]]
    is_admin = current_user.user_type in ["admin_user", "admin_super"]
    if not (is_owner or is_admin):
        flash("Unauthorized to delete this appointment.", "danger")
        return redirect(url_for("bp-appointment.list_all_appointments"))

    try:
        # Prevent deletion if a report is linked
        report = db.get_report_by_appointment_id(appointment_id)
        if report:
            flash("Cannot delete appointment because it is linked to a report.", "danger")
            return redirect(url_for("bp-appointment.view_appointment", appointment_id=appointment_id))

        # Perform deletion and invalidate cache
        db.delete_appointment(appointment_id)
        invalidate_my_appt_cache()
        flash("Appointment successfully deleted.", "success")

    except Exception as e:
        flash(f"Error deleting appointment: {e}", "danger")

    # Redirect to the appropriate list view
    return_to = request.args.get("return_to", "all")
    return redirect(url_for(
        "bp-appointment.my_appointments" if return_to == "my"
        else "bp-appointment.list_all_appointments"
    ))




@bp_appointment.route("/modify_appointment/<int:appointment_id>", methods=["GET", "POST"])
@login_required
def modify_appointment(appointment_id):
    """
    Admin route to modify an existing appointment's details.

    Handles both GET and POST requests. On GET, the form is pre-filled with existing
    appointment data. On POST, input is validated and updates are applied to both
    the appointment and service tables.

    Args:
        appointment_id (int): ID of the appointment to be modified.

    Returns:
        Response: Rendered template on GET or form error, or redirect on success.
    """
    # Fetch appointment from DB
    appt = db.get_appointment_by_id(appointment_id)
    if not appt:
        return flash_and_redirect("Appointment not found.", "danger", "bp-appointment.my_appointments")

    if current_user.user_type =="client" and current_user.id != appt["consumer_id"]:
        return flash_and_redirect("You are not authorized to modify this appointment.", "danger", "bp-appointment.my_appointments")
    if current_user.user_type == "professional" and current_user.id != appt["provider_id"]:
        return flash_and_redirect("You are not authorized to modify this appointment.", "danger", "bp-appointment.my_appointments")
    
    form = ModifyAppointmentForm()

    # Populate dropdown choices
    form.consumer_id.choices = db.get_client_choices()
    form.provider_id.choices = db.get_provider_choices()
    pay_rates = {
        pid: db.get_user_by_id(pid)[14] or 15.75 for pid, _ in form.provider_id.choices
    }

    if form.validate_on_submit():
        try:
            # Extract form data
            consumer_id = form.consumer_id.data
            provider_id = form.provider_id.data
            consumer_name = db.get_user_name_by_id(consumer_id)
            provider_name = db.get_user_name_by_id(provider_id)
            date = form.date_appoint.data
            slot = form.slot.data
            venue = form.venue.data
            service_name = form.service_name.data
            nber_services = form.nber_services.data
            duration = form.duration.data

            # Validate slot format and compute max duration
            try:
                start_hour = int(slot.split("-")[0])
            except ValueError:
                flash("Invalid time slot format. Example: '10-11'.", "danger")
                return render_template("modify_appointment.html", form=form, pay_rates=pay_rates)

            max_end_hour = 12 if start_hour < 12 else 22
            max_duration = max_end_hour - start_hour

            if not (1 <= duration <= max_duration):
                flash(f"Invalid duration. For slot {slot}, allowed is 1 to {max_duration} hours.", "danger")
                return render_template("modify_appointment.html", form=form, pay_rates=pay_rates)

            if nber_services > duration:
                flash(f"Services ({nber_services}) cannot exceed duration ({duration}).", "danger")
                return render_template("modify_appointment.html", form=form, pay_rates=pay_rates)

            # Update appointment info
            db.execute("""
                UPDATE salon_appointment
                SET date_appoint = %s, slot = %s, venue = %s,
                    provider_id = %s, provider_name = %s,
                    consumer_id = %s, consumer_name = %s,
                    nber_services = %s
                WHERE appointment_id = %s
            """, (
                date, slot, venue,
                provider_id, provider_name,
                consumer_id, consumer_name,
                nber_services, appointment_id
            ))

            # Update linked service info
            db.execute("""
                UPDATE salon_service
                SET service_name = %s, service_duration = %s,
                    service_price = %s
                WHERE appointment_id = %s
            """, (
                service_name,
                duration,
                duration * pay_rates.get(provider_id, 15.75),
                appointment_id
            ))

            db.log_admin_action(f"{current_user.user_name} modified appt #{appointment_id}", current_user.user_name)

            flash("Appointment updated successfully.", "success")
            return redirect(url_for("bp-appointment.view_appointment", appointment_id=appointment_id))

        except Exception as e:
            flash(f"Error updating appointment: {e}", "danger")
            return render_template("modify_appointment.html", form=form, pay_rates=pay_rates)

    # Pre-fill form fields for GET
    form.consumer_id.data = appt["consumer_id"]
    form.provider_id.data = appt["provider_id"]
    form.date_appoint.data = appt["date_appoint"]
    form.slot.data = appt["slot"]
    form.venue.data = appt["venue"]
    form.service_name.data = appt["service_name"]
    form.nber_services.data = appt["nber_services"]
    form.duration.data = appt["service_duration"]
    form.meta.appointment_id = appointment_id  # Optional: for template or tracking use

    return render_template(
        "modify_appointment.html",
        form=form,
        pay_rates=pay_rates,
        context=make_context("Modify Appointment")
    )



