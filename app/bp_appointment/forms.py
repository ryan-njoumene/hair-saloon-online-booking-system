from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, DateField, IntegerField, SubmitField
from wtforms.validators import DataRequired, NumberRange
from datetime import date

class CreateAppointmentForm(FlaskForm):
    """
    Form for clients to create a new appointment.

    Fields:
        venue (SelectField): Dropdown for venue selection.
        date_appoint (DateField): Date of the appointment.
        slot (SelectField): Time slot (e.g., '10-11').
        provider_id (SelectField): Dropdown to select a professional.
        service_name (StringField): Name of the service requested.
        service_duration (IntegerField): Duration of the service in hours.
        nb_services (IntegerField): Number of services requested.
        submit (SubmitField): Button to submit the form.
    """
    venue = SelectField("Venue", choices=[], validators=[DataRequired()])
    date_appoint = DateField("Date", validators=[DataRequired()], render_kw={"min": date.today().isoformat()})
    slot = SelectField("Slot", choices=[], validators=[DataRequired()])
    provider_id = SelectField("Professional", coerce=int, validators=[DataRequired()])
    service_name = StringField("Service Name", validators=[DataRequired()])
    service_duration = IntegerField("Duration (hours)", validators=[DataRequired()])
    nb_services = IntegerField("Number of Services", validators=[DataRequired()])
    submit = SubmitField("Create Appointment")


class ModifyAppointmentForm(FlaskForm):
    """
    Form for admins to modify an existing appointment.

    Fields:
        consumer_id (SelectField): Dropdown to select a client.
        provider_id (SelectField): Dropdown to select a professional.
        date_appoint (DateField): Date of the appointment.
        slot (StringField): Time slot (e.g., '13-14').
        venue (StringField): Location/room/chair.
        service_name (StringField): Name of the service.
        nber_services (IntegerField): Number of services requested (must be ≥ 1).
        duration (IntegerField): Duration in hours (must be ≥ 1).
        submit (SubmitField): Button to submit the form.
    """
    consumer_id = SelectField("Consumer", coerce=int, validators=[DataRequired()])
    provider_id = SelectField("Provider", coerce=int, validators=[DataRequired()])
    date_appoint = DateField("Date", format="%Y-%m-%d", validators=[DataRequired()])
    slot = StringField("Slot", validators=[DataRequired()])
    venue = StringField("Venue", validators=[DataRequired()])
    service_name = StringField("Service", validators=[DataRequired()])
    nber_services = IntegerField("Number of Services", validators=[DataRequired(), NumberRange(min=1)])
    duration = IntegerField("Duration", validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField("Update Appointment")
