"""User class for the application."""
from flask_login import UserMixin
from werkzeug.security import generate_password_hash
from models.database import db


class User(UserMixin):
    """
    Base class for all users in the system.

    This class represents a user and stores various details about the user, including
    personal information, account status, and role-based attributes.

    Attributes:
        id (int): Unique identifier for the user.
        active (bool): Indicates if the user's account is active.
        user_type (str): Type of user (e.g., 'client', 'professional').
        access_level (int): Defines the user's level of access (e.g., admin, user).
        user_name (str): The username used for login.
        fname (str): The user's first name.
        lname (str): The user's last name.
        email (str): The user's email address.
        user_image (str): File name of the user's profile picture.
        password (str): Hashed password for user authentication.
        phone_number (str): The user's phone number.
        address (str): The user's home address.
        age (int): The user's age.
        specialty (str, optional): User's profession or specialization (only for professionals).
        pay_rate (float, optional): Professional's pay rate.
        warning (str, optional): Warning message for the user (if any).
        warning_count (int): The number of warnings the user has received.
    """

    def __init__(self, user_id, active, user_type, access_level, user_name,
                 fname, lname, email, user_image, password, phone_number,
                 address, age, specialty=None, pay_rate=None, warning=None, warning_count=0):
        """
        Initialize a new User object with provided information.

        Args:
            user_id (int): Unique identifier for the user.
            active (bool): Whether the user's account is active.
            user_type (str): Type of user (e.g., 'client', 'professional').
            access_level (int): User's access level (e.g., admin or regular user).
            user_name (str): The username for login.
            fname (str): The user's first name.
            lname (str): The user's last name.
            email (str): The user's email address.
            user_image (str): The user's profile image filename.
            password (str): The user's password (hashed).
            phone_number (str): The user's phone number.
            address (str): The user's address.
            age (int): The user's age.
            specialty (str, optional): The user's specialty (for professionals).
            pay_rate (float, optional): Pay rate for professionals.
            warning (str, optional): Warning message for the user (if any).
            warning_count (int, optional): The number of warnings for the user.
        """
        self.id = user_id
        self.active = active
        self.user_type = user_type
        self.access_level = access_level
        self.user_name = user_name
        self.fname = fname
        self.lname = lname
        self.email = email
        self.user_image = user_image
        self.password = password
        self.phone_number = phone_number
        self.address = address
        self.age = age
        self.specialty = specialty
        self.pay_rate = pay_rate
        self.warning = warning
        self.warning_count = warning_count



    @staticmethod
    def create(data):
        """
        Create a new user in the database.

        This method hashes the password, determines the user's role, sets default values for 
        missing fields, and creates the user in the database. It also assigns an appropriate
        access level based on the user's role.

        Args:
            data (dict): Dictionary containing user data such as username, password, 
                         first name, last name, email, etc.

        Returns:
            object: The newly created user record from the database.
        """
        # Hash the provided password
        hashed = generate_password_hash(data["password"])

        # Set the user type (default to 'client' if not provided)
        user_type = data.get("user_type", "client")

        # Determine the user's access level based on their role
        user_data = {
            "user_type": user_type,
            "access_level": (
                3 if user_type == "admin_super" else  # Superadmins get highest level
                2 if user_type in ["admin_user", "admin_appoint"] else  # Admins get level 2
                1  # Regular users get level 1
            ),
            "user_name": data["user_name"],
            "fname": data["fname"],
            "lname": data["lname"],
            "email": data["email"],
            "password": hashed,
            "phone_number": data.get("phone_number", "514-123-4567"),  # Default phone number if missing
            "address": data.get("address", "Montreal"),  # Default address if missing
            "age": data.get("age", 18),  # Default age if missing
            "user_image": data.get("user_image", "person_icon.png"),  # Default image if missing
            "pay_rate": float(data.get("pay_rate", 15.75)) if user_type == "professional" else None, # Pay rate for professionals
            "specialty": data.get("specialty", "Hair-Dresser" if user_type == "professional" else None)  # Specialty for professionals
        }

        # Call the database method to create the user and return the result
        return db.create_user(user_data)




    @staticmethod
    def get_user_by_id(user_id):
        """
        Retrieve a user by their ID.

        Args:
            user_id (int): The ID of the user to retrieve.

        Returns:
            User: The user object if found, or None if not found.
        """
        # TODO: Change based on how db methods are implemented
        row = db.get_user_by_id(user_id)
        return User(*row) if row else None


    @staticmethod
    def get_user_by_username(user_name):
        """
        Retrieve a user by their username.

        Args:
            user_name (str): The username of the user to retrieve.

        Returns:
            User: The user object if found, or None if not found.
        """
        # TODO: Change based on how db methods are implemented
        row = db.get_user_by_username(user_name)
        return User(*row) if row else None


    @staticmethod
    def get_users_by_type(user_type):
        """
        Get all users of a specific type.

        Args:
            user_type (str): The type of users to retrieve (e.g., 'client', 'professional').

        Returns:
            list: A list of User objects matching the given user_type.
        """
        rows = db.get_users_by_type(user_type)
        return [User(*row) for row in rows]


    @property
    def user_id(self):
        """
        Property to retrieve the user ID.

        Returns:
            int: The unique ID of the user.
        """
        return self.id




class ProfessionalUser(User):
    """
    Professional user class for users with a specific profession.

    Inherits from the User class and sets default values for professional-specific
    attributes, such as pay rate and specialty. The user_type is automatically set to
    'professional' for this class.

    Attributes:
        pay_rate (float): The pay rate for the professional (default is 15.75).
        specialty (str): The user's professional specialty (default is 'Hair-Dresser').
    """

    def __init__(self, user_id, active, user_type, access_level, user_name, fname, lname,
                 email, user_image, password, phone_number, address, age,
                 pay_rate=15.75, specialty="Hair-Dresser"):
        """
        Initialize a new ProfessionalUser object.

        Args:
            user_id (int): The unique ID for the user.
            active (bool): Indicates if the user account is active.
            user_type (str): The type of user, default is 'professional'.
            access_level (int): The user's access level.
            user_name (str): The username for login.
            fname (str): The user's first name.
            lname (str): The user's last name.
            email (str): The user's email address.
            user_image (str): The filename for the user's profile image.
            password (str): The user's password (hashed).
            phone_number (str): The user's phone number.
            address (str): The user's address.
            age (int): The user's age.
            pay_rate (float, optional): The professional's pay rate (default is 15.75).
            specialty (str, optional): The professional's specialty (default is 'Hair-Dresser').

        """
        # Initialize base User class with general attributes
        super().__init__(user_id, active, user_type, access_level, user_name, fname, lname,
                         email, user_image, password, phone_number, address, age)
        
        # Set user type to 'professional' for this subclass
        self.user_type = "professional"
        
        # Set default or provided pay rate and specialty for professionals
        self.pay_rate = pay_rate
        self.specialty = specialty

