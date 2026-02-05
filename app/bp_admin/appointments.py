from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import cache
from . import bp_admin
from .forms import AddAppointment, EditAppointmentForm
from .utils_admin import (
    flash_and_redirect, role_required, make_context,
    invalidate_appointment_cache, populate_appointment_form_choices
)
from models.database import db


# Constants
ALL_SLOTS = [(f"{h}-{h+1}", f"{h}-{h+1}") for h in list(range(1, 12)) + list(range(13, 22))]

# Helpers
def get_pay_rates(provider_choices):
    return {
        pid: db.get_user_by_id(pid)[14] or 15.75
        for pid, _ in provider_choices if pid != -1
    }


@bp_admin.route("/manage_appointments")
@login_required
@role_required("admin_appoint", "admin_super")
def manage_appointments():
    """
    Admin route to manage appointments.

    Retrieves the 'status' filter from the query string and calls the
    cached helper function to render the appointments management page.
    """
    filter_status = request.args.get("status", "all")
    return _get_manage_appointments_cached(current_user.user_type, filter_status)


@cache.memoize(timeout=60)
def _get_manage_appointments_cached(user_type, filter_status):
    """
    Cached helper function to render the Manage Appointments view.

    Args:
        user_type (str): The user type of the currently logged-in admin.
        filter_status (str): The appointment status to filter by.

    Returns:
        str: Rendered HTML of the manage_appointments page.
    """
    form = AddAppointment()

    # Populate dropdown choices for the appointment form (e.g., venues, slots, users)
    populate_appointment_form_choices(form, db)

    # Retrieve and optionally filter appointments by status
    all_appointments = db.get_all_appointments()
    appointments = [
        a for a in all_appointments if a["status"] == filter_status
    ] if filter_status != "all" else all_appointments

    # Prepare pay rates for professionals, used to display or calculate cost
    pay_rates = get_pay_rates(form.provider_id.choices)

    # Render the management template with context and data
    return render_template(
        "appointments/manage_appointments.html",
        appointments=appointments,
        form=form,
        pay_rates=pay_rates,
        context=make_context("Manage Appointments"),
        filter_status=filter_status
    )



@bp_admin.route("/view_admin_appointment/<int:appt_id>")
@login_required
@role_required("admin_appoint", "admin_super")
def view_admin_appointment(appt_id):
    """
    Admin route to view the details of a specific appointment.

    Args:
        appt_id (int): ID of the appointment to view.

    Returns:
        str: Rendered HTML of the appointment detail page.
    """
    return_status = request.args.get("status", "all")  # Optional return context for navigation
    return _get_view_appointment_cached(appt_id, return_status)


@cache.memoize(timeout=60)
def _get_view_appointment_cached(appt_id, return_status):
    """
    Cached helper function to fetch and render a specific appointment's details.

    Args:
        appt_id (int): ID of the appointment.
        return_status (str): Status filter to preserve page context on return.

    Returns:
        str: Rendered HTML page with appointment details.
    """
    appointment = db.get_appointment_by_id(appt_id)

    # Redirect with error if appointment is not found
    if not appointment:
        return flash_and_redirect("Appointment not found.", "danger", "bp-admin.manage_appointments")

    # Render appointment detail template
    return render_template(
        "appointments/view_admin_appointment.html",
        appointment=appointment,
        context=make_context(f"Appointment #{appt_id}", "Appointment Details"),
        return_status=return_status
    )



@bp_admin.route("/edit_appointment/<int:appt_id>", methods=["GET", "POST"])
@login_required
@role_required("admin_appoint", "admin_super")
def edit_appointment(appt_id):
    """
    Admin route to edit an existing appointment.

    Allows authorized admins to update appointment and service details. Validates slot
    format and ensures duration constraints are respected based on the time slot range.

    Args:
        appt_id (int): ID of the appointment to be edited.

    Returns:
        str: Rendered HTML template for the edit form or redirects on success.
    """
    # Fetch the appointment by ID
    appt = db.get_appointment_by_id(appt_id)
    if not appt:
        return flash_and_redirect("Appointment not found.", "danger", "bp-admin.manage_appointments")

    form = EditAppointmentForm()

    # Populate dropdowns for client, professional, and slot selection
    form.consumer_id.choices = db.get_client_choices()
    form.provider_id.choices = db.get_provider_choices()
    form.slot.choices = [(f"{h}-{h+1}", f"{h}-{h+1}") for h in list(range(1, 12)) + list(range(13, 22))]
    pay_rates = get_pay_rates(form.provider_id.choices)

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

            # Validate time slot format and duration bounds
            try:
                start_hour = int(slot.split("-")[0])
            except ValueError:
                flash("Invalid time slot format. Example: '10-11'.", "danger")
                return render_template("appointments/edit_appointment.html", form=form, pay_rates=pay_rates)

            max_end_hour = 12 if start_hour < 12 else 22
            max_duration = max_end_hour - start_hour

            if not (1 <= duration <= max_duration):
                flash(f"Invalid duration. For time slot {slot}, allowed duration is 1 to {max_duration} hours.", "danger")
                return render_template("appointments/edit_appointment.html", form=form, pay_rates=pay_rates)

            if nber_services > duration:
                flash(f"Number of services ({nber_services}) cannot exceed duration ({duration}).", "danger")
                return render_template("appointments/edit_appointment.html", form=form, pay_rates=pay_rates)

            # Update appointment
            db.execute("""
                UPDATE salon_appointment
                SET date_appoint = %s, slot = %s, venue = %s,
                    provider_id = %s, provider_name = %s,
                    consumer_id = %s, consumer_name = %s,
                    nber_services = %s
                WHERE appointment_id = %s
            """, (date, slot, venue, provider_id, provider_name, consumer_id, consumer_name, nber_services, appt_id))

            # Update service
            db.execute("""
                UPDATE salon_service
                SET service_name = %s, service_duration = %s
                WHERE appointment_id = %s
            """, (service_name, duration, appt_id))

            db.log_admin_action(
                f"Admin '{current_user.user_name}' edited appointment #{appt_id} (Consumer: {consumer_name}, Provider: {provider_name})",
                current_user.user_name
            )

            invalidate_appointment_cache(cache, current_user.user_type)
            cache.delete_memoized(_get_user_appointments_cached, consumer_id)
            cache.delete_memoized(_get_user_appointments_cached, provider_id)

            return flash_and_redirect("Appointment updated successfully.", "success", "bp-admin.manage_appointments")

        except Exception as e:
            flash(f"Error updating appointment: {e}", "danger")
            return render_template("appointments/edit_appointment.html", form=form, pay_rates=pay_rates)

    # Pre-fill fields on GET
    form.consumer_id.data = appt["consumer_id"]
    form.provider_id.data = appt["provider_id"]
    form.date_appoint.data = appt["date_appoint"]
    form.slot.data = appt["slot"]
    form.venue.data = appt["venue"]
    form.service_name.data = appt["service_name"]
    form.nber_services.data = appt["nber_services"]
    form.duration.data = appt["service_duration"]

    return render_template(
        "appointments/edit_appointment.html",
        form=form,
        pay_rates=pay_rates,
        context=make_context("Edit Appointment"),
        appt_id=appt_id
    )






@bp_admin.route("/delete_appointment/<int:appt_id>", methods=["POST"])
@login_required
@role_required("admin_appoint", "admin_super")
def delete_appointment(appt_id):
    """
    Admin route to delete an existing appointment.

    Deletes the specified appointment and its associated service record from the database.
    Also clears related cache entries for the admin and involved users.

    Args:
        appt_id (int): The ID of the appointment to be deleted.

    Returns:
        Response: Redirect to the appointment management page with a flash message.
    """
    # Retrieve the appointment record
    appt = db.get_appointment_by_id(appt_id)
    if not appt:
        return flash_and_redirect("Appointment not found.", "warning", "bp-admin.manage_appointments")

    # Perform deletion and cache invalidation
    db.delete_appointment(appt_id)
    invalidate_appointment_cache(cache, current_user.user_type)
    cache.delete_memoized(_get_user_appointments_cached, appt["consumer_id"])
    cache.delete_memoized(_get_user_appointments_cached, appt["provider_id"])

    flash("Appointment deleted successfully.", "success")
    return redirect(url_for("bp-admin.manage_appointments"))



@bp_admin.route("/view_user_appointments/<int:user_id>")
@login_required
def view_user_appointments(user_id):
    """
    Admin route to view all appointments for a specific user.

    Args:
        user_id (int): The ID of the user whose appointments will be displayed.

    Returns:
        str: Rendered HTML page listing the user's appointments.
    """
    return _get_user_appointments_cached(user_id)


@cache.memoize(timeout=60)
def _get_user_appointments_cached(user_id):
    """
    Cached helper function to fetch and render all appointments for a given user.

    Args:
        user_id (int): The ID of the user.

    Returns:
        str: Rendered HTML template displaying the user's appointments.
    """
    # Retrieve the user by ID
    user = db.get_user_by_id(user_id)
    if not user:
        return flash_and_redirect("User not found.", "danger", "bp-admin.manage_users")

    # Get all appointments associated with the user
    appointments = db.get_appointments_by_user(user_id)

    # Render the template with appointment data and contextual headings
    return render_template(
        "appointments/view_user_appointments.html",
        appointments=appointments,
        user=user,
        context=make_context(
            f"Appointments for {user[4]}",  # user_name
            f"Appointments - {user[5]} {user[6]}"  # fname + lname
        )
    )



@bp_admin.route("/create_appointment", methods=["POST"])
@login_required
def create_appointment():
    """
    Admin route to create a new appointment.

    Handles appointment creation from the submitted form data, performs validation on duration
    and number of services, inserts the appointment and associated service into the database,
    and logs the action. On success, redirects to the appointment management page.
    
    Returns:
        Response: Redirect or rendered HTML with form errors.
    """
    form = AddAppointment()

    # Populate dropdowns for venue, time slot, client, and provider
    populate_appointment_form_choices(form, db)
    pay_rates = get_pay_rates(form.provider_id.choices)

    if form.validate_on_submit():
        try:
            # Extract form fields
            client_id = form.client_id.data
            provider_id = form.provider_id.data
            venue = form.venue.data
            date_appoint = form.date_appoint.data
            slot = form.slot.data
            service_id = form.service.data
            duration = form.duration.data
            nb_services = form.nb_services.data or 1

            # Determine max duration based on selected time slot
            start_hour = int(slot.split("-")[0])
            max_end_hour = 12 if start_hour < 12 else 22
            max_duration = max_end_hour - start_hour

            # Validate duration constraints
            if not (1 <= duration <= max_duration):
                flash(f"Invalid duration. For time slot {slot}, allowed duration is 1 to {max_duration} hours.", "danger")
                return redirect(url_for("bp-admin.manage_appointments"))

            # Validate logical relationship between services and duration
            if nb_services > duration:
                flash(f"Number of services ({nb_services}) cannot exceed duration in hours ({duration}).", "danger")
                return redirect(url_for("bp-admin.manage_appointments"))

            # Lookup full names for client and provider
            consumer_name = db.get_user_name_by_id(client_id) or "Client"
            provider_name = db.get_user_name_by_id(provider_id) or "Professional"

            # Insert appointment into database
            appointment_id = db.add_appointment({
                "consumer_id": client_id,
                "provider_id": provider_id,
                "consumer_name": consumer_name,
                "provider_name": provider_name,
                "status": "requested",
                "approved": 0,
                "date_appoint": date_appoint,
                "slot": slot,
                "venue": venue,
                "nber_services": nb_services,
                "consumer_report": None,
                "provider_report": None
            })

            # Insert service linked to the appointment
            db.add_service({
                "appointment_id": appointment_id,
                "service_name": f"Service from ID {service_id}",
                "service_duration": duration,
                "service_price": duration * nb_services * pay_rates.get(provider_id, 15.75),
                "service_materials": None
            })

            # Log the creation action in the admin log
            db.log_admin_action(
                f"Admin '{current_user.user_name}' created appointment for {consumer_name} with {provider_name}",
                current_user.user_name
            )

            # Clear cached appointment data
            invalidate_appointment_cache(cache, current_user.user_type)

            flash("Appointment created successfully.", "success")
            return redirect(url_for("bp-admin.manage_appointments", status="requested"))

        except Exception as e:
            flash(f"Error saving appointment: {e}", "danger")
            return redirect(url_for("bp-admin.manage_appointments"))

    # If form not valid, show error and re-render appointment form
    flash("Failed to create appointment. Please check the form.", "danger")
    appointments = db.get_all_appointments()
    return render_template(
        "appointments/manage_appointments.html",
        appointments=appointments,
        form=form,
        pay_rates=pay_rates,
        context=make_context("Manage Appointments"),
        filter_status="all"
    )
