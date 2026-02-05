# bp_admin/users.py

from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
import sys
from app import cache
from . import bp_admin
from .forms import EditUserForm, AddAdminForm
from app.bp_auth.forms import RegisterForm
from app.bp_auth.routes import allowed_file
from app.bp_auth.user import User
from .utils_admin import (
    role_required, flash_and_redirect, invalidate_user_cache, make_context
)
from models.database import db
from .appointments import _get_user_appointments_cached
from .reports import _get_user_reports_cached
from .utils_user_cache import get_view_user_cached


@bp_admin.route("/manage_users")
@login_required
@role_required("admin_user", "admin_super")
def manage_users():
    """
    Admin route to manage all users.

    Allows admins to view users filtered by type (e.g., clients, professionals, etc.).
    The filter is specified via the 'type' query parameter.

    Returns:
        str: Rendered HTML page listing filtered users.
    """
    filter_type = request.args.get("type", "all")  # Default to showing all users
    return _get_manage_users_cached(current_user.user_type, filter_type)



@cache.memoize(timeout=60)
def _get_manage_users_cached(user_type, filter_type):
    """
    Cached helper to render the Manage Users page with optional filtering.

    Args:
        user_type (str): The type of the current admin (used to restrict access to certain filters).
        filter_type (str): The user category to filter by (e.g., 'clients', 'admins').

    Returns:
        str: Rendered HTML of the user management page with the appropriate filtered users.
    """
    form = RegisterForm()

    # Helper to convert DB row tuples to dictionaries for rendering
    def format_users(rows):
        return [
            {
                "id": r[0],
                "username": r[1],
                "user_type": r[2],
                "active": r[3],
                "warning_count": r[4]
            }
            for r in rows
        ]

    # SQL conditions based on filter type
    queries = {
        "clients": "user_type = 'client'",
        "professionals": "user_type = 'professional'",
        "admins": "user_type LIKE 'admin_%'",
        "warned": "warning_count > 0",
        "deactivated": "active = 0"
    }

    # Default to no filter if unknown type
    condition = queries.get(filter_type, "1=1")

    # Prevent non-super admins from accessing admin list
    if filter_type == "admins" and user_type != "admin_super":
        condition = "1=0"

    # Fetch user rows from the database based on the condition
    rows = db.fetch(f"""
        SELECT user_id, user_name, user_type, active, warning_count
        FROM salon_user
        WHERE {condition}
    """)

    # Render the user management page with the filtered user list and registration form
    context = make_context("Manage Users")
    return render_template("users/manage_users.html", users=format_users(rows), form=form, context=context)



@bp_admin.route("/add_user", methods=["POST"])
@login_required
@role_required("admin_user", "admin_super")
def add_user():
    """
    Admin route to add a new user (client, professional, or admin).

    Processes form data submitted via POST, validates fields and passwords, handles
    image upload, and inserts a new user into the database. Displays flash messages
    based on success or failure.

    Returns:
        Response: Redirect to the manage users page with flash message.
    """
    form_data = request.form

    # Extract fields from form
    username = form_data.get("user_name")
    password = form_data.get("password")
    confirm_password = form_data.get("confirm_password")
    user_type = form_data.get("user_type")
    fname = form_data.get("fname")
    lname = form_data.get("lname")
    email = form_data.get("email")
    phone = form_data.get("phone_number")
    address = form_data.get("address")
    age = form_data.get("age")
    specialty = form_data.get("specialty")
    pay_rate = form_data.get("pay_rate")
    image_file = request.files.get("user_image")

    # Ensure all required fields are present
    if not all([username, password, confirm_password, fname, lname, email, phone, address, age, user_type]):
        return flash_and_redirect("Please provide all user details.", "danger", "bp-admin.manage_users")

    # Ensure passwords match
    if password != confirm_password:
        return flash_and_redirect("Passwords do not match.", "danger", "bp-admin.manage_users")

    # Check if username is already taken
    existing_user = db.get_user_by_username(username)
    if existing_user:
        return flash_and_redirect(f"Username '{username}' is already taken. Please choose a different one.", "danger", "bp-admin.manage_users")

    # Handle image upload or set default
    image_filename = "default.jpeg"
    if image_file and allowed_file(image_file.filename):
        filename = secure_filename(image_file.filename)
        image_path = os.path.join("app", "static", "uploads", filename)
        image_file.save(image_path)
        image_filename = filename

    try:
        # Prepare user data dictionary
        new_user = {
            "user_type": user_type,
            "user_name": username,
            "password": password,
            "fname": fname,
            "lname": lname,
            "email": email,
            "phone_number": phone,
            "address": address,
            "age": int(age),
            "user_image": image_filename,
            "specialty": specialty if user_type == "professional" else None,
            "pay_rate": pay_rate if user_type == "professional" else None
        }

        # Create user in database
        User.create(new_user)

        # Invalidate cache so new user appears in list
        invalidate_user_cache(cache, current_user.user_type)

        flash("User successfully added.", "success")
    except Exception as e:
        flash(f"Error adding user: {str(e)}", "danger")

    return redirect(url_for("bp-admin.manage_users"))




@bp_admin.route("/view_user/<int:user_id>")
@login_required
def view_user(user_id):
    """
    Admin route to view details of a specific user.

    Args:
        user_id (int): The ID of the user whose profile is being viewed.

    Returns:
        str: Rendered HTML page with user details.
    """
    # Used to determine what section the admin is returning from (e.g., 'all', 'clients', etc.)
    return_type = request.args.get("return_type", "all")
    return get_view_user_cached(user_id, return_type)




@bp_admin.route("/edit_user/<int:user_id>", methods=["GET", "POST"])
@login_required
def edit_user(user_id):
    """
    Admin route to edit user information.

    Loads the user data into an editable form. On submission, updates the user's details
    in the database and invalidates all related cache entries. Includes validation for
    professional pay rates.

    Args:
        user_id (int): The ID of the user to edit.

    Returns:
        Response: Renders the edit form or redirects on success.
    """
    # Fetch user data by ID
    user_data = db.get_user_by_id(user_id)
    if not user_data:
        return flash_and_redirect("User not found.", "danger", "bp-admin.manage_users")

    user = User(*user_data)
    form = EditUserForm(obj=user)

    if form.validate_on_submit():
        try:
            # Validate pay rate if user is a professional
            if form.user_type.data == "professional" and form.pay_rate.data:
                try:
                    pay_rate_val = float(form.pay_rate.data)
                except ValueError:
                    flash("Invalid pay rate format. Please enter a numeric value.", "danger")
                    return render_template("users/edit_user.html", form=form, user=user)
            else:
                pay_rate_val = None

            # Update user details in the database
            db.execute("""
                UPDATE salon_user SET
                    user_type = %s, user_name = %s, fname = %s, lname = %s,
                    email = %s, phone_number = %s, address = %s, age = %s,
                    specialty = %s, pay_rate = %s
                WHERE user_id = %s
            """, (
                form.user_type.data,
                form.user_name.data,
                form.fname.data,
                form.lname.data,
                form.email.data,
                form.phone_number.data,
                form.address.data,
                form.age.data,
                form.specialty.data if form.user_type.data == "professional" else None,
                pay_rate_val,
                user_id
            ))

            # Invalidate user cache globally and per return type
            invalidate_user_cache(cache, current_user.user_type)

            for return_type in ["all", "clients", "professionals", "admins", "warned", "deactivated"]:
                try:
                    view_user_func = sys.modules["app.bp_admin.utils_user_cache"].get_view_user_cached
                    cache.delete_memoized(view_user_func, user_id, return_type)
                except Exception as ce:
                    flash(f"Warning: failed to clear cache for return_type '{return_type}': {ce}", "warning")

            flash("User updated successfully.", "success")
            return redirect(url_for("bp-admin.view_user", user_id=user_id))

        except Exception as e:
            flash(f"Error updating user: {str(e)}", "danger")

    # Render the form with existing user data
    return render_template("users/edit_user.html", form=form, user=user)



@bp_admin.route("/delete_user/<int:user_id>", methods=["POST"])
@login_required
def delete_user(user_id):
    """
    Admin route to delete a user from the system.

    Deletes the user record from the database and clears all associated cache entries,
    including user profile, appointments, and reports. Displays flash messages based
    on success or failure of the operation.

    Args:
        user_id (int): The ID of the user to delete.

    Returns:
        Response: Redirects to the user management page with a status flash message.
    """
    try:
        # Delete the user from the database
        db.delete_user(user_id)

        # Invalidate main user cache
        invalidate_user_cache(cache, current_user.user_type)

        # Invalidate cached profile views across user filters
        for return_type in ["all", "clients", "professionals", "admins", "warned", "deactivated"]:
            try:
                view_user_func = sys.modules["app.bp_admin.utils_user_cache"].get_view_user_cached
                cache.delete_memoized(view_user_func, user_id, return_type)
            except Exception as ce:
                flash(f"Warning: failed to clear view cache '{return_type}': {ce}", "warning")

        # Invalidate cached appointments
        try:
            cache.delete_memoized(_get_user_appointments_cached, user_id)
        except Exception as ce:
            flash(f"Warning: failed to clear appointment cache: {ce}", "warning")

        # Invalidate cached reports
        try:
            cache.delete_memoized(_get_user_reports_cached, user_id, "dashboard")
        except Exception as ce:
            flash(f"Warning: failed to clear report cache: {ce}", "warning")

        flash("User deleted successfully.", "success")

    except Exception as e:
        flash(f"Error deleting user: {str(e)}", "danger")

    return redirect(url_for("bp-admin.manage_users"))





@bp_admin.route("/warn_user/<int:user_id>", methods=["GET", "POST"])
@login_required
@role_required("admin_user", "admin_super")
def warn_user(user_id):
    """
    Admin route to issue a warning to a user.

    On GET, displays the warning form. On POST, records the warning message and increments
    the warning count. If the user reaches 3 warnings, their account is automatically deactivated.
    Caches are cleared accordingly.

    Args:
        user_id (int): The ID of the user being warned.

    Returns:
        Response: Renders the warning form or redirects with a flash message after issuing a warning.
    """
    # Fetch the user to ensure they exist
    user = db.get_user_by_id(user_id)
    if not user:
        return flash_and_redirect("User not found.", "danger", "bp-admin.manage_users")

    if request.method == "POST":
        warning_text = request.form.get("warning_text")

        if not warning_text:
            flash("Warning text cannot be empty.", "danger")
        else:
            # Store warning message and increment count
            db.set_user_warning(user_id, warning_text)
            new_count = db.get_warning_count(user_id) + 1
            db.set_warning_count(user_id, new_count)

            # Auto-deactivate account if warning count reaches 3
            if new_count >= 3:
                db.set_user_active_status(user_id, False)
                flash("User has reached 3 warnings. Account automatically deactivated.", "danger")
            else:
                flash("Warning issued successfully.", "success")

            # Invalidate relevant caches
            invalidate_user_cache(cache, current_user.user_type)
            cache.delete_memoized(get_view_user_cached, user_id, "all")

            return redirect(url_for("bp-admin.view_user", user_id=user_id))

    # Render the warning form on GET
    return render_template("users/warn_user.html", user=user)



@bp_admin.route("/toggle_active/<int:user_id>", methods=["POST"])
@login_required
@role_required("admin_user", "admin_super")
def toggle_user_active(user_id):
    """
    Admin route to toggle a user's active status.

    Retrieves the user, reverses their current activation state (active/inactive),
    updates the database, and clears relevant cached data.

    Args:
        user_id (int): The ID of the user whose status is being toggled.

    Returns:
        Response: Redirects to the user's profile page with a status flash message.
    """
    # Retrieve user data to confirm existence
    user = db.get_user_by_id(user_id)
    if not user:
        return flash_and_redirect("User not found.", "danger", "bp-admin.manage_users")

    # Toggle the user's active status (user[1] is expected to be the 'active' field)
    new_status = not user[1]
    db.execute("UPDATE salon_user SET active = %s WHERE user_id = %s", (int(new_status), user_id))

    # Clear user cache entries
    invalidate_user_cache(cache, current_user.user_type)
    cache.delete_memoized(get_view_user_cached, user_id, "all")

    flash("User activation status updated.", "success")
    return redirect(url_for("bp-admin.view_user", user_id=user_id, return_type=request.args.get("return_type", "all")))




@bp_admin.route("/add_admin", methods=["GET", "POST"])
@login_required
def add_admin():
    """
    Superadmin-only route to create a new admin user.

    Displays a form to collect new admin information. On successful submission, the
    admin is added to the database, relevant caches are invalidated, and the action
    is logged.

    Returns:
        Response: Renders the form on GET or failure, or redirects to the dashboard on success.
    """
    # Only superadmins are allowed to access this route
    if current_user.user_type != 'admin_super':
        flash("Access Denied. Only Superusers can add admins.", "danger")
        return redirect(url_for('bp-main.home'))

    form = AddAdminForm()

    if form.validate_on_submit():
        try:
            # Build new admin data from form
            new_admin_data = {
                "user_type": form.user_type.data,
                "user_name": form.user_name.data,
                "password": form.password.data,
                "fname": form.fname.data,
                "lname": form.lname.data,
                "email": form.email.data
            }

            # Create the new admin
            User.create(new_admin_data)

            # Invalidate user management cache for all filter types
            for filter_type in ["all", "clients", "professionals", "admins", "warned", "deactivated"]:
                cache.delete_memoized(_get_manage_users_cached, current_user.user_type, filter_type)

            # Log the admin creation action
            db.log_admin_action(
                f"Superuser {current_user.user_name} added new admin {form.user_name.data}",
                current_user.user_name
            )

            flash("New admin user created successfully.", "success")
            return redirect(url_for("bp-admin.dashboard"))

        except Exception as e:
            flash(f"Error creating admin: {e}", "danger")

    # Render form if GET request or submission failed
    return render_template("add_admin.html", form=form)
