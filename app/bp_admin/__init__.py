from flask import Blueprint
from . import utils_admin  # already imported

bp_admin = Blueprint("bp-admin", __name__, template_folder="templates", static_folder="static")

# Register filters
utils_admin.register_template_filters(bp_admin)

# Import routes
from . import routes
from . import appointments
from . import reports
from . import users
