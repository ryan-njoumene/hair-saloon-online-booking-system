from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField, HiddenField, TextAreaField
from wtforms.validators import DataRequired, Length
from flask_login import current_user
from models.database import db


class ClientReportForm(FlaskForm):
    """Form used by clients to submit feedback reports."""

    appointment_id = SelectField(
        "",
        coerce=int,
        validators=[DataRequired()]
    )
    feedback_client = StringField(
        "Client Feedback",
        validators=[DataRequired(), Length(min=3, max=150)]
    )
    submit = SubmitField("Create Report")

    def __init__(self, *args, **kwargs):
        """
        Initialize the ClientReportForm with appointment choices.

        Dynamically populates the appointment choices based on the
        currently authenticated user's appointments.
        """
        super().__init__(*args, **kwargs)
        if current_user.is_authenticated:
            # Fetch appointments for the currently logged-in user
            appointments = db.get_appointments_by_user(current_user.user_id)
            # Populate appointment choices as tuples of (id, description)
            self.appointment_id.choices = [
                (appt["appointment_id"], f"Appt {appt['appointment_id']}")
                for appt in appointments
            ]


class ProfessionalReportForm(FlaskForm):
    """Form used by professionals to respond to client feedback reports."""

    appointment_id = HiddenField()
    feedback_client = StringField(
        "Client Feedback",
        render_kw={'readonly': True}
    )
    feedback_professional = TextAreaField(
        "Your Response",
        validators=[DataRequired(), Length(min=3, max=150)]
    )
    status = SelectField(
        "Status",
        choices=[("open", "Open"), ("closed", "Closed")],
        validators=[DataRequired()]
    )
    submit = SubmitField("Submit Response")
