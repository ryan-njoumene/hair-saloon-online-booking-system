"""Import"""
from flask import Blueprint

bp_appointment = Blueprint("bp-appointment", __name__, template_folder="templates", static_folder="static") 
