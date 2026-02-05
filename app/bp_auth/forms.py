"""Forms for user registration, login, profile management, and password changes."""

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, IntegerField, FileField, SelectField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, EqualTo


class RegisterForm(FlaskForm):
    """
    User registration form.

    Allows clients or professionals to register with optional specialty and pay rate
    for professionals. Includes profile image upload and password confirmation.
    """
    user_type = SelectField('User Type', choices=[
        ('client', 'Client'),
        ('professional', 'Professional')
    ], validators=[DataRequired()])
    
    user_name = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    fname = StringField('First Name', validators=[DataRequired(), Length(min=2, max=20)])
    lname = StringField('Last Name', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password', message="Passwords must match")])
    phone_number = StringField('Phone Number', validators=[DataRequired(), Length(min=10, max=15)])
    address = StringField('Address', validators=[DataRequired(), Length(min=5, max=100)])
    age = IntegerField('Age', validators=[DataRequired()])
    user_image = FileField('Upload Profile Picture')

    # Optional fields for professionals
    specialty = StringField('Specialty')
    pay_rate = StringField('Pay Rate')

    submit = SubmitField('Register')


class LoginForm(FlaskForm):
    """
    User login form.

    Requires username and password for authentication.
    """
    user_name = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')


class ProfileForm(FlaskForm):
    """
    Form for users to update their profile details.

    Includes name, contact info, and optional profile picture upload.
    """
    fname = StringField('First Name', validators=[DataRequired(), Length(min=2, max=20)])
    lname = StringField('Last Name', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    user_image = FileField('Profile Picture')
    phone_number = StringField('Phone Number', validators=[DataRequired(), Length(min=10, max=15)])
    address = StringField('Address', validators=[DataRequired(), Length(min=5, max=100)])
    submit = SubmitField('Update Profile')


class PasswordChangeForm(FlaskForm):
    """
    Form for changing a user's password.

    Requires verification of the old password and confirmation of the new one.
    """
    old_password = PasswordField('Old Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired(), Length(min=6)])
    confirm_new_password = PasswordField('Confirm New Password', validators=[DataRequired(), EqualTo('new_password', message="Passwords must match")])
    submit = SubmitField('Change Password')


# ---------- Messages Forms

class NewGroupChatForm(FlaskForm):
    """
    Form for creating a new GroupChat with an initial message.

    Includes group_name, members, and contents.
    """
    group_name = StringField('Group Chat Name', validators=[DataRequired(), Length(min=2)])
    members = SelectField('Members', choices=[], validators=[DataRequired()])
    contents = TextAreaField('Message', validators=[DataRequired(), Length(min=1)])
    submit = SubmitField('Send')

class MessageForm(FlaskForm):
    """
    Form for sending a message to an existing GroupChat.

    Includes contents.
    """
    members = SelectField('Add New Member', choices=[], validators=[DataRequired()])
    contents = TextAreaField('Message', validators=[DataRequired(), Length(min=1)])
    submit = SubmitField('Send')
