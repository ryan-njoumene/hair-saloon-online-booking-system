"""Import"""
from . import routes
from flask import Blueprint

bp_report = Blueprint("bp-report", __name__, template_folder="templates", static_folder="static") 


