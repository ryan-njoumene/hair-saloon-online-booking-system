"""Imports"""
import os
from flask import render_template, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename
from models.database import db
from app import cache
from .forms import LoginForm, RegisterForm, ProfileForm, NewGroupChatForm, MessageForm
from . import bp_auth
from .user import User
from .messages import Message

# Folder for uploaded files
UPLOAD_FOLDER = os.path.join("app", "static", "uploads")

# Default image filename if no image is uploaded
DEFAULT_IMAGE = 'default.jpeg'

# Allowed file extensions for uploads
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Create the upload folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    """
    Check if the uploaded file has an allowed extension.

    Args:
        filename (str): The name of the uploaded file.

    Returns:
        bool: True if the file has a valid extension, False otherwise.
    """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@bp_auth.route("/login", methods=["GET", "POST"])
def login():
    """
    User login route.

    Handles both GET and POST requests. On POST, authenticates the user based on the 
    provided username and password. Displays appropriate flash messages on success or failure.
    After successful login, redirects the user to the home page. For professionals and clients,
    notifications about pending reports or responses are displayed.

    Returns:
        Response: Rendered login page on GET or redirect on successful login.
    """
    form = LoginForm()

    # If the form is submitted and valid
    if form.validate_on_submit():
        # Fetch user by username
        user = User.get_user_by_username(form.user_name.data)
        
        # Authenticate user and check if account is active
        if user and check_password_hash(user.password, form.password.data):
            if not user.active:
                flash("Account is deactivated. Please contact support.", "danger")
                return redirect(url_for("bp-auth.login"))

            # Log the user in
            login_user(user)
            print(f"[DEBUG] Logged in as {user.user_name}, id={user.id}")

            # Display warning if applicable
            if (warning := db.get_user_warning(user.id)):
                flash(f"⚠️ WARNING: {warning}", "danger")
                db.clear_user_warning(user.id)

            # Notifications for reports
            if user.user_type == "professional":
                reports = db.get_pending_reports_for_professional(user.id)
                if reports:
                    flash(f"📋 You have {len(reports)} report(s) awaiting your response.", "info")
            elif user.user_type == "client":
                responses = db.get_reports_with_new_professional_feedback(user.id)
                if responses:
                    flash(f"✅ {len(responses)} report(s) received a professional response.", "success")
                    db.mark_reports_as_seen_by_client([r["report_id"] for r in responses])

            flash("Logged in successfully.", "success")
            return redirect(url_for("bp-main.home"))

        # Invalid username or password
        flash("Invalid username or password.", "danger")

    # Render the login form on GET or invalid POST
    return render_template("login.html", form=form, page_title="Login", main_heading="Login")


@bp_auth.route("/register", methods=["GET", "POST"])
def register():
    """
    User registration route.

    Handles both GET and POST requests. On GET, it renders the registration form.
    On POST, it processes the form data, including handling file uploads for the user image,
    validates the data, and creates a new user in the database. Upon successful registration,
    the user is redirected to the login page.

    Returns:
        Response: Rendered registration page on GET or redirect to login on successful registration.
    """
    form = RegisterForm()

    # If the form is submitted and validated
    if form.validate_on_submit():
        # Handle user image upload, if provided
        image = form.user_image.data
        image_filename = DEFAULT_IMAGE  # Default image if no file is uploaded

        # Check if image is valid and save it
        if image and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            image_path = os.path.join(UPLOAD_FOLDER, filename)
            image.save(image_path)
            image_filename = filename

        try:
            # Prepare form data and create user
            data = form.data
            data["user_image"] = image_filename  # Save image filename to database

            # Create new user in the database
            User.create(data)

            flash("Account created! You can now log in.", "success")
            return redirect(url_for("bp-auth.login"))
        except Exception as e:
            flash(f"Registration error: {e}", "danger")

    # Render the registration form on GET or if POST validation fails
    return render_template("register.html", form=form, page_title="Register", main_heading="Register")


@bp_auth.route("/logout")
@login_required
def logout():
    """
    User logout route.

    Logs the user out by calling Flask-Login's logout_user function.
    Displays a flash message confirming the logout, then redirects to the home page.

    Returns:
        Response: Redirects to the home page with a flash message.
    """
    logout_user()  # Log the user out
    flash("You’ve been logged out.", "info")  # Notify user
    return redirect(url_for("bp-main.home"))  # Redirect to the home page


@bp_auth.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    """
    User profile route.

    Allows the logged-in user to view and update their profile information, including
    personal details and profile picture. On successful form submission, the profile
    is updated in the database, and the user session is refreshed.

    Returns:
        Response: Rendered profile page on GET or redirect on successful update.
    """
    # Create the profile form pre-filled with current user's data
    form = ProfileForm(obj=current_user)

    # If the form is submitted and valid
    if form.validate_on_submit():
        # Handle profile image upload
        image = form.user_image.data
        image_filename = current_user.user_image or DEFAULT_IMAGE  # Default if no new image

        # If a valid image is uploaded, save it
        if image and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            image_path = os.path.join(UPLOAD_FOLDER, filename)
            image.save(image_path)
            image_filename = filename

        try:
            # Update the user profile information in the database
            db.execute("""
                UPDATE salon_user
                SET fname = %s, lname = %s, email = %s, phone_number = %s, address = %s, user_image = %s
                WHERE user_id = %s
            """, (
                form.fname.data,
                form.lname.data,
                form.email.data,
                form.phone_number.data,
                form.address.data,
                image_filename,
                current_user.id
            ))

            # Refresh the user session after updating their profile
            updated_user = User.get_user_by_id(current_user.id)
            login_user(updated_user)

            flash("Profile updated!", "success")
            return redirect(url_for("bp-auth.profile"))

        except Exception as e:
            flash(f"Error updating profile: {e}", "danger")

    # Render the profile page with the form on GET or if POST fails
    return render_template(
        "profile.html",
        form=form,
        page_title="Your Profile",
        main_heading="Your Profile",
        user=current_user
    )


# --------- Messages System

@bp_auth.route("/manage_groupchat", methods=["GET", "POST"])
@login_required
def manage_groupchat():
    """
    Handle the creation of new a Group Chat between the Logged User and Any Existing Users.

    GET: Display a form for creating a new GroupChat with an initial message and all Group Chat
        the Current Logged User is part of
    POST: Validate form input and create a new message in the database.

    Returns:
        Response: Rendered template for message creation or redirect after successful submission.
    """

    return _get_groupchat_cached()


@cache.memoize(timeout=10)
def _get_groupchat_cached():
    """
    Cached helper to render the View Manage Group Chat page with all our Group Chat.

    Returns:
        str: Rendered template displaying all Group Chat the current user is member of.
    """

    # Initialize the form for the Group Chat creation
    form = NewGroupChatForm()

    # Populate dropdowns with all users
    users = db.get_all_user_with_names()
    form.members.choices = [(None, 'Select a member')] + [
        (u["user_name"], f"{u['fname']} {u['lname']} [id:{u['user_id']}]") for u in users
    ]

    # Handle form submission
    if form.validate_on_submit():
        try:
            # Create a new message with the provided data
            Message.create({
                "group_name": form.group_name.data,
                "members": form.members.data + f", {current_user.user_name}",
                "sender_id": current_user.user_id,
                "sender_username": current_user.user_name,
                "contents": form.contents.data
            })

            # Invalidate cached grouphcat to reflect new data
            invalidate_messages_caches()

            flash("Group Chat created!", "success")
            return redirect(url_for("bp-auth.manage_groupchat"))
        except Exception as e:
            flash(f"Group Chat Creation error: {e}", "danger")

    # Get a list of all Group Chat the Logged user is member of.
    groupchats = Message.get_group_name_by_member(current_user.user_name)
    
    # Render the Manage Group Chat page with the list of all Group Chat the user is part of
    context = make_context("My Group Chats")
    return render_template("manage_groupchat.html", groupchats=groupchats, form=form, context=context)


# -------- Group Chat and its Messages

@bp_auth.route("/groupchat/<string:group_name>", methods=["GET", "POST"])
@login_required
def view_groupchat_messages(group_name):
    """
    Allow Users to communicate to each other through messages.

    GET: Display all the previous messages exchanged in a Group Chat.
    POST: Validate and submit a message to the Group Chat.

    Args:
        group_name (int): Unique identifier of a Group Chat, useful to send a message to the rigth destinators.

    Returns:
        Response: Rendered message form or a redirect after submission.
    """
    group_list = Message.get_group_name_by_member(current_user.user_name)

    # Ensure the Logged User is a member of the current Group Chat
    valid_group_name = False
    for groupchat in group_list:
        if groupchat[0] == group_name:
            valid_group_name = True
            break
    # If not a member of the Group Chat, redirect to manage_groupchat
    if valid_group_name is False:
        flash("Unauthorized access", "danger")
        return redirect(url_for("bp-auth.manage_groupchat"))
    
    return _get_messages_cached(group_name)

# @cache.memoize(timeout=5)
def _get_messages_cached(group_name):
    """
    Cached helper to render the View Group Chat page with all its previous messages displayed.

    Returns:
        str: Rendered template displaying messages of a Group Chat.
    """
    # Get a list of all previous messages sent in the current Group Chat
    messages = Message.get_messages_by_group_name(group_name)

    # Set the members attributed to the new message be the same as the last messages sent
    members = messages[len(messages)-1]["members"]

    # Initialize form for a message in a Group Chat
    form = MessageForm()

    # Populate dropdowns with all users
    users = db.get_all_user_with_names()
    form.members.choices = [(None, 'Select a member')] + [
        (u["user_name"], f"{u['fname']} {u['lname']} [id:{u['user_id']}]") for u in users
    ]

    # Handle form submission (POST request)
    if form.validate_on_submit():
        try:
            if form.members.data is not None:
                new_members = form.members.data + f", {members}"
            else:
                new_members = members
            
            # Create a new message with the provided data
            Message.create({
                "group_name": group_name,
                "members": new_members,
                "sender_id": current_user.user_id,
                "sender_username": current_user.user_name,
                "contents": form.contents.data
            })

            # Invalidate cached messages data to reflect recent changes
            # invalidate_messages_caches(group_name)

            flash("Your message has been sent.", "success")
            return redirect(url_for("bp-auth.view_groupchat_messages", group_name=f"{group_name}"))

        except Exception as e:
            flash(f"Message Creation error: {e}", "danger")
    
    # Render the Group Chat page with the list of previous messages and message form
    context = make_context("Group Chat", group_name)
    return render_template("groupchat.html", messages=messages, form=form, context=context)


# === Utilities ===

def invalidate_messages_caches(group_name=None):
    """
    Invalidate cached report data to ensure fresh data retrieval.

    This function clears memoized caches for user messages (Group Chat) and optionally
    clears specific caches for individual message if a message ID is provided.

    Args:
        group_name (int, optional): Specific Group Chat Identifier whose cache should be cleared.
            Defaults to None.
    """

    # Clear cache for the list of Group Chats the Logged User is part of
    cache.delete_memoized(_get_groupchat_cached)

    if group_name:
        # Clear cache for the specific Groupchat
        cache.delete_memoized(_get_messages_cached, group_name)


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