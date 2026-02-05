from flask import Blueprint
bp_auth = Blueprint("bp-auth", __name__, template_folder="templates")

from . import user
from . import routes
