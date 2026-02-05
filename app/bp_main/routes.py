from flask import Blueprint, render_template
from flask_login import current_user
from app.bp_auth.user import User
from app import cache
from models.database import db
from app.bp_auth.user import User

# Blueprint for the main routes of the application.
bp_main = Blueprint(
    "bp-main",
    __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path='/bp_main/static/'
)

@bp_main.route("/")
@bp_main.route("/home")
def home():
    """Render the homepage of the application."""
    return render_template("home.html")

@bp_main.route("/about")
def about():
    """Render the About page with context including super admin users."""

    image_path = {}
    username = ["andrew", "alexander", "rix"]
    for user in username:
        if (single_user := User.get_user_by_username(user)):
            image_path[user] = single_user.user_image
    
    return _render_about(current_user.is_authenticated, image_path)


@cache.memoize(timeout=300)
def _render_about(_auth_flag, image_path):
    context = {
        "page_title": "About",
        "main_heading": "About Page",
        "super_admins": get_super_admins_cached()
    }
    return render_template("about.html", context=context, image_path=image_path)


@cache.memoize(timeout=300)
def get_super_admins_cached():
    """
    Retrieve and cache a list of super admin users.

    Returns:
        list: List of User objects for super admin usernames.
    """
    # List comprehension to filter existing users by their usernames
    return [
        user for username in ["andrew", "alexander", "rix"]
        if (user := User.get_user_by_username(username))
    ]
