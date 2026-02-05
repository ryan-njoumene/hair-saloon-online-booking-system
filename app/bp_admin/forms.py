from flask_wtf import FlaskForm
from wtforms import DateField, IntegerField, StringField, PasswordField, SubmitField, SelectField, TextAreaField
from wtforms.validators import DataRequired, Length, Email, EqualTo, NumberRange
from models.database import db

# === Form for editing an appointment by admin ===
class EditAppointmentForm(FlaskForm):
    """Form used by admins to edit an existing appointment."""
    consumer_id = SelectField("Consumer", coerce=int, validators=[DataRequired()])
    provider_id = SelectField("Provider", coerce=int, validators=[DataRequired()])
    date_appoint = DateField("Date", format="%Y-%m-%d", validators=[DataRequired()])
    slot = SelectField("Time Slot", choices=[], validators=[DataRequired()])
    venue = StringField("Venue", validators=[DataRequired()])
    service_name = StringField("Service", validators=[DataRequired()])
    nber_services = IntegerField("Number of Services", validators=[DataRequired(), NumberRange(min=1)])
    duration = IntegerField("Duration", validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField("Update Appointment")

# === Form for editing a report by admin ===
class EditReportForm(FlaskForm):
    """Form used by admins to edit an existing report."""
    status = SelectField("Status", choices=[
        ("closed", "Closed"),
        ("open", "Open")
    ], validators=[DataRequired()])
    client_feedback = TextAreaField("Client Feedback", validators=[DataRequired()])
    professional_response = TextAreaField("Professional Response", validators=[DataRequired()])
    date_report = DateField("Date", format='%Y-%m-%d', validators=[DataRequired()])
    submit = SubmitField("Update Report")

# === Form for editing user information by admin ===
class EditUserForm(FlaskForm):
    """Form used by admins to edit user details."""
    user_type = SelectField('User Type', choices=[
        ('client', 'Client'), 
        ('professional', 'Professional'),
        ('admin_user', 'Admin User'), 
        ('admin_appoint', 'Admin Appoint'), 
        ('admin_super', 'Admin Super')
    ], validators=[DataRequired()])
    user_name = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    fname = StringField('First Name', validators=[DataRequired(), Length(min=2, max=20)])
    lname = StringField('Last Name', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone_number = StringField('Phone Number', validators=[DataRequired(), Length(min=10, max=15)])
    address = StringField('Address', validators=[DataRequired(), Length(min=5, max=100)])
    age = IntegerField('Age', validators=[DataRequired()])
    specialty = StringField('Specialty')  # Optional field for professionals
    pay_rate = StringField('Pay Rate')    # Optional field for professionals
    submit = SubmitField('Update')

# === Form for creating a new admin user ===
class AddAdminForm(FlaskForm):
    """Form for super admins to create a new admin account."""
    user_type = SelectField('Admin Type', choices=[
        ('admin_user', 'Admin User'),
        ('admin_appoint', 'Admin Appoint'),
        ('admin_super', 'Admin Super')
    ], validators=[DataRequired()])
    user_name = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    fname = StringField('First Name', validators=[DataRequired()])
    lname = StringField('Last Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Create Admin')

# === Form for creating a new appointment by admin ===
class AddAppointment(FlaskForm):
    """Form used by admins to create a new appointment."""
    venue = SelectField("Venue", choices=[], validators=[DataRequired()])
    date_appoint = DateField("Date", validators=[DataRequired()])
    slot = SelectField("Time Slot", choices=[], validators=[DataRequired()])
    provider_id = SelectField("Professional", coerce=int, validators=[DataRequired()])
    service = StringField("Service", validators=[DataRequired()])
    duration = IntegerField("Duration (Hours)", validators=[DataRequired()], render_kw={"id": "duration"})
    nb_services = IntegerField("Number of services", validators=[DataRequired()], render_kw={"id": "nb_services"})
    client_id = SelectField("Client", coerce=int, validators=[DataRequired()])
    submit = SubmitField("Create Appointment")

# === Form for creating a new report (both feedbacks) ===
class AddReport(FlaskForm):
    """Form used by admins to create a report with both client and professional feedback."""
    appointment_id = SelectField("Appointment", coerce=int, validators=[DataRequired()])
    status = SelectField("Status", choices=[("open", "Open"), ("closed", "Closed")], validators=[DataRequired()])
    feedback_client = StringField("Client Feedback", validators=[DataRequired(), Length(min=3, max=150)])
    feedback_professional = TextAreaField("Professionnal Feedback", validators=[DataRequired(), Length(min=3, max=150)])
    submit = SubmitField("Submit Response")

    def __init__(self, *args, **kwargs):
        """Populate the appointment dropdown with all available appointments."""
        super().__init__(*args, **kwargs)
        appointments = db.get_all_appointments()
        self.appointment_id.choices = [
            (appt["appointment_id"], f"Appt {appt['appointment_id']}") for appt in appointments
        ]
