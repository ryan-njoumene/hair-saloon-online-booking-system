import os
import psycopg2
from config import Config
from contextlib import contextmanager
from werkzeug.security import check_password_hash
import psycopg2.extras
from psycopg2.extras import RealDictCursor
import logging

# Logger for database-related errors and information
logger = logging.getLogger(__name__)

class Database:
    """Database class for handling PostgreSQL database operations."""
    
    def __init__(self, autocommit=True):
        """
        Initialize the Database instance and establish a connection.rm 

        Args:
            autocommit (bool): Whether to enable autocommit for the database connection. Defaults to True.
        """
        # Establish a connection to the database
        self.__connection = self.__connect()
        self.__connection.autocommit = autocommit

    def __connect(self):
        """
        Establish a connection to the PostgreSQL database using configuration from the Config class.

        Returns:
            psycopg2.extensions.connection: A connection object to interact with the database.

        Raises:
            DatabaseConnectionError: If there is an error connecting to the database.
        """
        try:
            return psycopg2.connect(
                host=Config.DATABASE_HOST,
                database=Config.DATABASE_NAME,
                user=Config.DATABASE_USER,
                password=Config.DATABASE_PASSWORD,
                port=Config.DATABASE_PORT
            )
        except psycopg2.Error as e:
            # Log the error and raise a custom exception
            raise DatabaseConnectionError(f"Database connection error: {e}") from e

    
    def execute(self, query, params=None):
        """
        Execute a database query with optional parameters.

        Args:
            query (str): The SQL query string to execute.
            params (tuple, optional): A tuple of parameters to pass with the query.
        """
        with self.__connection.cursor() as cur:
            cur.execute(query, params)  # Execute the query with the parameters
            self.__connection.commit()  # Commit the transaction to the database

    def fetch(self, query, params=None):
        """
        Execute a database query and fetch all results.

        Args:
            query (str): The SQL query string to execute.
            params (tuple, optional): A tuple of parameters to pass with the query.

        Returns:
            list: A list of tuples representing the rows returned by the query.
        """
        with self.__connection.cursor() as cur:
            cur.execute(query, params)  # Execute the query with the parameters
            return cur.fetchall()  # Return all rows of the query result

    def __reconnect(self):
        """
        Attempt to reconnect to the database if the current connection is lost.
        
        This method closes the existing connection (if possible) and tries to re-establish it.
        """
        try:
            self.close()  # Attempt to close the existing connection
        except psycopg2.Error:
            pass  # If closing fails, ignore it and proceed
        self.__connection = self.__connect()  # Reconnect to the database

    def db_conn(self):
        """
        Return the current database connection object.

        Returns:
            psycopg2.extensions.connection: The current database connection object.
        """
        return self.__connection

    def close(self):
        """
        Close the current database connection.

        If the connection exists, it will be closed and set to None.
        """
        if self.__connection is not None:
            self.__connection.close()  # Close the connection
            self.__connection = None  # Set the connection to None to indicate it's closed

    def get_cursor(self):
        """
        Get a new cursor for interacting with the database.

        Attempts to get a database cursor up to 3 times before raising an exception if it fails.

        Returns:
            psycopg2.extensions.cursor: A cursor object for database interaction.

        Raises:
            DatabaseConnectionError: If a cursor cannot be retrieved after 3 attempts.
        """
        for _ in range(3):
            try:
                return self.__connection.cursor()  # Try to get a cursor
            except psycopg2.Error:
                self.__reconnect()  # If an error occurs, try to reconnect
        raise DatabaseConnectionError("Failed to get a database cursor after 3 attempts")  # Raise an error if all attempts fail


    @contextmanager
    def cursor(self):
        """
        Context manager for database cursor to ensure proper resource handling.

        Provides a database cursor within the context and ensures that the transaction 
        is committed if no exceptions are raised. If an exception occurs, the transaction
        is rolled back to maintain data integrity.

        Yields:
            psycopg2.extensions.cursor: A cursor object for interacting with the database.

        Raises:
            Exception: If any exception occurs during query execution, it is raised.
        """
        cur = self.get_cursor()  # Get a new cursor for interacting with the database
        try:
            yield cur  # Yield the cursor to be used in the context block
            self.__connection.commit()  # Commit the transaction if no errors occurred
        except Exception as e:
            self.__connection.rollback()  # Rollback the transaction in case of an error
            raise e  # Re-raise the exception
        finally:
            cur.close()  # Ensure the cursor is closed after the operation

    def __run_file(self, file_path):
        """
        Run an SQL script file on the database.

        This method reads an SQL file, processes its contents line by line, and executes
        SQL commands. It ignores lines that are comments (starting with '--').

        Args:
            file_path (str): Path to the SQL file to execute.

        Raises:
            DatabaseConnectionError: If there is an error while executing the SQL script.
        """
        with self.__connection.cursor() as cursor:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    statement = ''
                    # Read the file line by line and execute the SQL statements
                    for line in f:
                        if line.startswith('--'):
                            continue  # Skip comments
                        statement += line
                        if line.strip().endswith(';'):
                            cursor.execute(statement)  # Execute the SQL statement
                            statement = ''  # Reset the statement for the next query
                self.__connection.commit()  # Commit the transaction after running the script
            except psycopg2.Error as e:
                self.__connection.rollback()  # Rollback if an error occurs
                raise DatabaseConnectionError(f"Error running SQL script {file_path}: {e}") from e

    def run_sql_script(self, sql_filename, close_after=True):
        """
        Run an SQL script from a file.

        Executes an SQL file on the database and optionally closes the connection after execution.

        Args:
            sql_filename (str): The path to the SQL script file.
            close_after (bool, optional): If True, the connection will be closed after execution. Defaults to True.

        Raises:
            FileNotFoundError: If the provided file path does not exist.
        """
        if os.path.exists(sql_filename):
            self.__run_file(sql_filename)  # Run the SQL script
            if close_after:
                self.close()  # Close the connection if specified
        else:
            print('Invalid Path')  # Print an error if the file path is invalid

    def __del__(self):
        """
        Cleanup method to close the database connection when the object is destroyed.

        Ensures that the database connection is properly closed to release resources.
        """
        self.close()  # Close the database connection when the object is deleted




# ----------------- User Methods

    def check_password(self, username, plain_password):
        """
        Verify a user's password against the stored hashed password in the database.

        Args:
            username (str): The username of the user whose password is being verified.
            plain_password (str): The plain-text password to verify.

        Returns:
            bool: True if the password matches the stored hash, False otherwise.
        """
        # Retrieve the user's data by their username
        row = self.get_user_by_username(username)
        
        # Return False if no user was found with the provided username
        if not row:
            return False

        # Extract the hashed password from the retrieved user data (index 9 corresponds to 'password' column)
        hashed_password = row[9]  # Column index for 'password'
        
        # Compare the provided plain password with the stored hashed password
        return check_password_hash(hashed_password, plain_password)  # Return True if passwords match, False otherwise

    
    def create_user(self, user_data):
        """
        Insert a new user into the salon_user table and return the new user ID.

        Args:
            user_data (dict): A dictionary containing the user data to be inserted.
                            Expected keys: 'user_type', 'access_level', 'user_name', 'fname', 'lname', 
                            'email', 'password', 'phone_number', 'address', 'age', 'pay_rate', 'specialty'.
                            If a key is missing, default values are used for 'user_type', 'access_level', 'phone_number', 'address', and 'age'.

        Returns:
            int: The user ID of the newly inserted user.
        """
        # Define the SQL query for inserting a new user into the salon_user table
        query = """
        INSERT INTO salon_user (
            user_type, access_level, user_name, fname, lname, email,
            password, phone_number, address, age, pay_rate, specialty
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING user_id;
        """

        # Prepare the values to insert into the database
        values = (
            user_data.get("user_type", "client"),  # Default to "client" if not provided
            user_data.get("access_level", 1),  # Default to 1 if not provided
            user_data["user_name"],  # Username (required)
            user_data["fname"],  # First name (required)
            user_data["lname"],  # Last name (required)
            user_data["email"],  # Email address (required)
            user_data["password"],  # Password (required)
            user_data.get("phone_number", "514-123-4567"),  # Default to "514-123-4567" if not provided
            user_data.get("address", "Montreal"),  # Default to "Montreal" if not provided
            user_data.get("age", 18),  # Default to 18 if not provided
            user_data.get("pay_rate"),  # Pay rate (optional)
            user_data.get("specialty")  # Specialty (optional)
        )

        # Insert the new user and return the user_id of the newly created user
        return self.insert_and_return_id(query, values)



    def get_all_users(self):
        """
        Retrieve all users with basic identifying information from the database.

        This method fetches the user ID, username, and user type for every user in the system.

        Returns:
            list: A list of dictionaries, each containing the 'id', 'username', and 'user_type' of a user.
        """
        # Define the SQL query to retrieve basic user details
        query = "SELECT user_id, user_name, user_type FROM salon_user;"

        # Execute the query and fetch all rows
        rows = self.fetchall(query)

        # Return a list of dictionaries with user information
        return [{"id": r[0], "username": r[1], "user_type": r[2]} for r in rows]


    def get_all_user_with_names(self):
        """
        Fetch all users, including their user_id, username, and full name.

        Returns:
            list: A list of dictionaries, each containing the 'user_id', 'user_name', 'fname', and 'lname' 
                of users.
        """
        # Define the SQL query to fetch all professionals from the database, ordered by user_name
        query = """
            SELECT user_id, user_name, fname, lname
            FROM salon_user
            ORDER BY user_name;
        """
        
        # Execute the query and fetch all matching rows
        rows = self.fetchall(query)

        # Return the results as a list of dictionaries
        return [
            {
                "user_id": r[0],
                "user_name": r[1],
                "fname": r[2],
                "lname": r[3]
            } for r in rows
        ]



    def get_user_by_id(self, user_id):
        """
        Retrieve a user record from the database by their unique user ID.

        Args:
            user_id (int): The unique identifier of the user to retrieve.

        Returns:
            dict or None: A dictionary containing the user's information if found, 
                        or None if the user does not exist.
        """
        # Define the SQL query to retrieve the user's details based on their user_id
        query = """
            SELECT
                user_id,
                active,
                user_type,
                access_level,
                user_name,
                fname,
                lname,
                email,
                user_image,
                password,
                phone_number,
                address,
                age,
                specialty,
                pay_rate,
                warning,
                warning_count
            FROM salon_user
            WHERE user_id = %s
        """

        # Execute the query and return the first result as a dictionary
        return self.fetchone(query, (user_id,))




    def get_user_by_username(self, user_name):
        """
        Retrieve a user record from the database by their unique username.

        Args:
            user_name (str): The unique username of the user to retrieve.

        Returns:
            tuple or None: A tuple containing the user's information if found,
                        or None if the user does not exist.
        """
        # Define the SQL query to retrieve the user's details based on their username
        # Includes all fields required by the User class constructor
        query = """
            SELECT user_id, active, user_type, access_level, user_name, fname, lname, email,
                user_image, password, phone_number, address, age,
                specialty, pay_rate, warning, warning_count
            FROM salon_user
            WHERE user_name = %s;
        """

        # Execute the query with the given username and return the first matching result
        return self.fetchone(query, (user_name,))



    def get_users_by_type(self, user_type):
        """
        Retrieve all users that match a specific user type.

        Args:
            user_type (str): The user type to filter by (e.g., 'client', 'professional').

        Returns:
            list: A list of dictionaries, each containing the details of a user with the specified user_type.
        """
        # Define the SQL query to retrieve users with the specified user_type
        query = """
            SELECT user_id, active, user_type, access_level, user_name, fname, lname, email,
                user_image, password, phone_number, address, age
            FROM salon_user
            WHERE user_type = %s;
        """

        # Execute the query and return all matching results as a list of dictionaries
        return self.fetchall(query, (user_type,))



    def update_user_email(self, user_id, new_email):
        """
        Update a user's email address by their user ID.

        Args:
            user_id (int): The unique identifier of the user whose email is to be updated.
            new_email (str): The new email address to set for the user.
        """
        # Define the SQL query to update the user's email based on their user_id
        query = "UPDATE salon_user SET email = %s WHERE user_id = %s"
        
        # Execute the query and commit the changes
        self.execute_commit(query, (new_email, user_id))


    def delete_user(self, user_id):
        """
        Delete a user from the salon_user table by their user ID.

        Args:
            user_id (int): The unique identifier of the user to be deleted.
        """
        # Define the SQL query to delete the user from the database based on their user_id
        query = "DELETE FROM salon_user WHERE user_id = %s"
        
        # Execute the query and commit the changes
        self.execute_commit(query, (user_id,))


    def get_all_professionals(self):
        """
        Fetch all users with user_type 'professional', returning their user_id and user_name.

        Returns:
            list: A list of dictionaries containing the 'user_id' and 'user_name' of all professionals.
        """
        # Define the SQL query to retrieve all professionals from the database
        query = """
            SELECT user_id, user_name
            FROM salon_user
            WHERE user_type = 'professional'
            ORDER BY user_name;
        """
        
        # Execute the query and fetch all matching rows
        rows = self.fetchall(query)

        # Return the results as a list of dictionaries
        return [{"user_id": r[0], "user_name": r[1]} for r in rows]



    def get_all_clients_with_name(self):
        """
        Fetch all users with user_type 'client', including their user_id, username, and full name.

        Returns:
            list: A list of dictionaries, each containing the 'user_id', 'user_name', 'fname', and 'lname' 
                of clients.
        """
        # Define the SQL query to fetch all clients from the database, ordered by user_name
        query = """
            SELECT user_id, user_name, fname, lname
            FROM salon_user
            WHERE user_type = 'client'
            ORDER BY user_name;
        """
        
        # Execute the query and fetch all matching rows
        rows = self.fetchall(query)

        # Return the results as a list of dictionaries
        return [
            {
                "user_id": r[0],
                "user_name": r[1],
                "fname": r[2],
                "lname": r[3]
            } for r in rows
        ]


    def get_all_professionals_with_names(self):
        """
        Fetch all users with user_type 'professional', including their user_id, username, and full name.

        Returns:
            list: A list of dictionaries, each containing the 'user_id', 'user_name', 'fname', and 'lname' 
                of professionals.
        """
        # Define the SQL query to fetch all professionals from the database, ordered by user_name
        query = """
            SELECT user_id, user_name, fname, lname
            FROM salon_user
            WHERE user_type = 'professional'
            ORDER BY user_name;
        """
        
        # Execute the query and fetch all matching rows
        rows = self.fetchall(query)

        # Return the results as a list of dictionaries
        return [
            {
                "user_id": r[0],
                "user_name": r[1],
                "fname": r[2],
                "lname": r[3]
            } for r in rows
        ]


    def set_user_warning(self, user_id, warning_text):
        """
        Set a warning message for a user by their user ID.

        Args:
            user_id (int): The unique identifier of the user to receive the warning.
            warning_text (str): The warning message to be set for the user.
        """
        # Define the SQL query to update the user's warning in the database
        query = "UPDATE salon_user SET warning = %s WHERE user_id = %s"
        
        # Execute the query to update the warning message for the specified user
        self.execute_commit(query, (warning_text, user_id))


    def get_user_warning(self, user_id):
        """
        Retrieve the warning message for a specific user, if any.

        Args:
            user_id (int): The unique identifier of the user whose warning is to be retrieved.

        Returns:
            str or None: The warning message for the user, or None if no warning exists.
        """
        # Define the SQL query to fetch the warning message for the specified user
        query = "SELECT warning FROM salon_user WHERE user_id = %s"
        
        # Execute the query and fetch the result
        result = self.fetchone(query, (user_id,))
        
        # Return the warning message if found, otherwise return None
        return result[0] if result else None


    def clear_user_warning(self, user_id):
        """
        Clear the warning message for a specific user.

        Args:
            user_id (int): The unique identifier of the user whose warning is to be cleared.
        """
        # Define the SQL query to clear the warning message for the specified user
        query = "UPDATE salon_user SET warning = NULL WHERE user_id = %s"
        
        # Execute the query to clear the warning message
        self.execute_commit(query, (user_id,))


    def get_users_by_type_dict(self, user_type):
        """
        Return user_id, username, and user_type for all users of a given type.

        Args:
            user_type (str): The user type to filter by (e.g., 'client', 'professional').

        Returns:
            list: A list of dictionaries, each containing the 'user_id', 'user_name', and 'user_type' of a user.
        """
        # Define the SQL query to retrieve users by the specified user_type
        query = """
            SELECT user_id, user_name, user_type
            FROM salon_user
            WHERE user_type = %s;
        """
        
        # Execute the query and fetch all matching rows
        rows = self.fetchall(query, (user_type,))

        # Return the results as a list of dictionaries
        return [{"id": r[0], "username": r[1], "user_type": r[2]} for r in rows]


    def get_warning_count(self, user_id):
        """
        Return the warning count for a given user. Defaults to 0 if none is found.

        Args:
            user_id (int): The unique identifier of the user whose warning count is to be retrieved.

        Returns:
            int: The warning count for the user, or 0 if no warnings exist.
        """
        # Define the SQL query to retrieve the warning count for the specified user
        query = "SELECT warning_count FROM salon_user WHERE user_id = %s"
        
        # Execute the query and fetch the result
        result = self.fetchone(query, (user_id,))

        # Return the warning count, defaulting to 0 if no result is found
        return result[0] if result else 0


    def set_warning_count(self, user_id, count):
        """
        Update the warning count for a specific user.

        Args:
            user_id (int): The unique identifier of the user whose warning count is to be updated.
            count (int): The new warning count to set for the user.
        """
        # Define the SQL query to update the warning count for the specified user
        query = "UPDATE salon_user SET warning_count = %s WHERE user_id = %s"
        
        # Execute the query to update the warning count
        self.execute_commit(query, (count, user_id))


    def set_user_active_status(self, user_id, active):
        """
        Set whether a user is active (1) or inactive (0).

        Args:
            user_id (int): The unique identifier of the user whose active status is to be updated.
            active (bool): A boolean indicating whether the user should be active (1) or inactive (0).
        """
        # Define the SQL query to update the user's active status
        query = "UPDATE salon_user SET active = %s WHERE user_id = %s"
        
        # Execute the query to update the user's active status
        self.execute_commit(query, (int(active), user_id))


    def get_user_id_by_name(self, name, user_type):
        """
        Retrieve the user ID based on the user's full name and user type.

        Args:
            name (str): The full name of the user to search for.
            user_type (str): The user type (e.g., 'client', 'professional') to filter by.

        Returns:
            int or None: The user ID if a matching user is found, or None if no user is found.
        """
        # Define the SQL query to retrieve the user ID based on full name and user type
        query = """
            SELECT user_id
            FROM salon_user
            WHERE user_type = %s AND fname || ' ' || lname = %s
        """
        
        # Execute the query and fetch the result
        row = self.fetchone(query, (user_type, name))

        # Return the user ID if found, otherwise return None
        return row[0] if row else None


    def get_user_id_by_username_and_type(self, username, user_type):
        """
        Retrieve the user ID based on the username and user type.

        Args:
            username (str): The username of the user to search for.
            user_type (str): The user type (e.g., 'client', 'professional') to filter by.

        Returns:
            int or None: The user ID if a matching user is found, or None if no user is found.
        """
        # Define the SQL query to retrieve the user ID based on username and user type
        query = """
            SELECT user_id
            FROM salon_user
            WHERE user_type = %s AND user_name = %s
        """
        
        # Execute the query and fetch the result
        row = self.fetchone(query, (user_type, username))

        # Return the user ID if found, otherwise return None
        return row[0] if row else None


    def get_user_name_by_id(self, user_id):
        """
        Return the full name of a user given their user ID.

        Args:
            user_id (int): The unique identifier of the user.

        Returns:
            str or None: The full name of the user (first name + last name) if found,
                        or None if no user is found with the given user ID.
        """
        # Define the SQL query to retrieve the first and last name of the user by user ID
        query = """
            SELECT fname, lname 
            FROM salon_user 
            WHERE user_id = %s
        """
        
        # Execute the query and fetch the result
        result = self.fetchone(query, (user_id,))

        # Return the full name (first name + last name) if found, otherwise return None
        return f"{result[0]} {result[1]}" if result else None


#------------APPOINTMENT METHODS
    def add_appointment(self, appt_data):
        """
        Insert a new appointment into the salon_appointment table and return the appointment ID.

        Args:
            appt_data (dict): A dictionary containing the appointment details, such as:
                            - 'status' (str): The appointment status (default is 'requested').
                            - 'approved' (int): Approval status (default is 0).
                            - 'date_appoint' (str): The date of the appointment.
                            - 'slot' (str): The time slot for the appointment (default is "9-10").
                            - 'venue' (str): The venue for the appointment (default is "cmn_room").
                            - 'consumer_id' (int): The ID of the consumer.
                            - 'provider_id' (int): The ID of the provider.
                            - 'consumer_name' (str): The name of the consumer.
                            - 'provider_name' (str): The name of the provider.
                            - 'nber_services' (int): The number of services (default is 1).
                            - 'consumer_report' (str): The report from the consumer (optional).
                            - 'provider_report' (str): The report from the provider (optional).

        Returns:
            int: The appointment ID of the newly created appointment.
        """
        # Define the SQL query to insert a new appointment into the salon_appointment table
        query = """
            INSERT INTO salon_appointment (
                status, approved, date_appoint, slot, venue,
                consumer_id, provider_id, consumer_name, provider_name,
                nber_services, consumer_report, provider_report
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING appointment_id;
        """
        
        # Prepare the values to be inserted into the database, using defaults where necessary
        values = (
            appt_data.get("status", "requested"),  # Default status is 'requested'
            appt_data.get("approved", 0),  # Default approved status is 0 (not approved)
            appt_data.get("date_appoint"),  # Appointment date (required)
            appt_data.get("slot", "9-10"),  # Default slot is '9-10'
            appt_data.get("venue", "cmn_room"),  # Default venue is 'cmn_room'
            appt_data["consumer_id"],  # Consumer ID (required)
            appt_data["provider_id"],  # Provider ID (required)
            appt_data["consumer_name"],  # Consumer name (required)
            appt_data["provider_name"],  # Provider name (required)
            appt_data.get("nber_services", 1),  # Default number of services is 1
            appt_data.get("consumer_report"),  # Consumer report (optional)
            appt_data.get("provider_report")  # Provider report (optional)
        )
        
        # Call the method to insert the values into the database and return the appointment ID
        return self.insert_and_return_id(query, values)


        
    def add_service(self, service_data):
        """
        Insert a new service linked to an appointment and return the service ID.

        Args:
            service_data (dict): A dictionary containing the service details, such as:
                                - 'appointment_id' (int): The ID of the related appointment.
                                - 'service_name' (str): The name of the service.
                                - 'service_duration' (int): The duration of the service in minutes.
                                - 'service_price' (float): The price of the service.
                                - 'service_materials' (str, optional): The materials used for the service (optional).

        Returns:
            int: The service ID of the newly created service.
        """
        # Define the SQL query to insert a new service into the salon_service table
        query = """
            INSERT INTO salon_service (
                appointment_id, service_name, service_duration, service_price, service_materials
            ) VALUES (%s, %s, %s, %s, %s)
            RETURNING service_id;
        """
        
        # Prepare the values to be inserted into the database
        values = (
            service_data["appointment_id"],  # Appointment ID (required)
            service_data["service_name"],  # Service name (required)
            service_data["service_duration"],  # Service duration (required)
            service_data["service_price"],  # Service price (required)
            service_data.get("service_materials")  # Service materials (optional)
        )
        
        # Call the method to insert the values into the database and return the service ID
        return self.insert_and_return_id(query, values)


        
    def get_all_appointments(self):
        """
        Retrieve all appointments with joined service data, if available.

        This method fetches all appointment details, including associated service information
        (service name, duration, and price) using a LEFT JOIN on the salon_service table.

        Returns:
            list: A list of dictionaries, each containing the appointment details with 
                the associated service data (if available).
        """
        # Define the SQL query to retrieve all appointments with associated service data
        query = """
            SELECT sa.appointment_id, sa.status, sa.date_appoint, sa.slot, sa.venue,
                sa.consumer_id, sa.consumer_name, sa.provider_id, sa.provider_name,
                ss.service_name, ss.service_duration, ss.service_price
            FROM salon_appointment sa
            LEFT JOIN salon_service ss ON sa.appointment_id = ss.appointment_id
            ORDER BY sa.date_appoint ASC, sa.slot ASC;
        """
        
        # Execute the query and fetch all rows
        rows = self.fetchall(query)

        # Return the results as a list of dictionaries with appointment and service details
        return [
            {
                "appointment_id": r[0],
                "status": r[1],
                "date_appoint": r[2],
                "slot": r[3],
                "venue": r[4],
                "consumer_id": r[5],
                "consumer_name": r[6],
                "provider_id": r[7],
                "provider_name": r[8],
                "service_name": r[9] if r[9] else "N/A",  # Default to "N/A" if no service is linked
                "service_duration": r[10] if r[10] else 0,  # Default to 0 if no service duration is available
                "service_price": r[11] if r[11] else 0.00  # Default to 0 if no service price is available
            } for r in rows
        ]



    def get_appointment_by_id(self, appt_id):
        """
        Retrieve a specific appointment by its ID, including joined service information.

        Args:
            appt_id (int): The unique identifier of the appointment to retrieve.

        Returns:
            dict or None: A dictionary containing the appointment details along with associated service information,
                        or None if no appointment is found with the given ID.
        """
        # Define the SQL query to retrieve the appointment details along with associated service information
        query = """
            SELECT sa.appointment_id, sa.status, sa.date_appoint, sa.slot, sa.venue, 
                sa.consumer_id, sa.consumer_name, sa.provider_id, sa.provider_name,
                sa.nber_services,  -- Include this field for number of services
                ss.service_name, ss.service_duration, ss.service_price
            FROM salon_appointment sa
            LEFT JOIN salon_service ss ON sa.appointment_id = ss.appointment_id
            WHERE sa.appointment_id = %s;
        """
        
        # Execute the query and fetch the result for the given appointment ID
        # import pdb
        # pdb.set_trace()
        row = self.fetchone(query, (appt_id,))
        
        # Return None if no result is found
        if not row:
            return None

        # Return the appointment details as a dictionary
        return {
            "appointment_id": row[0],
            "status": row[1],
            "date_appoint": row[2],
            "slot": row[3],
            "venue": row[4],
            "consumer_id": row[5],
            "consumer_name": row[6],
            "provider_id": row[7],
            "provider_name": row[8],
            "nber_services": row[9],  # Number of services associated with the appointment
            "service_name": row[10] or "N/A",  # Default to "N/A" if no service name is available
            "service_duration": row[11] or 0,  # Default to 0 if no service duration is available
            "service_price": row[12] or 0.0  # Default to 0.0 if no service price is available
        }




    
    def get_appointments_by_user(self, user_id):
        """
        Return all appointments booked by a specific client, including service details.

        Args:
            user_id (int): The unique identifier of the client whose appointments are to be retrieved.

        Returns:
            list: A list of dictionaries, each containing appointment and service details for the client.
        """
        # Define the SQL query to retrieve all appointments for the specified client, 
        # including service details by joining with the salon_service table
        query = """
            SELECT sa.appointment_id, sa.status, sa.date_appoint, sa.slot, sa.venue,
                sa.provider_id, sa.provider_name, ss.service_name, ss.service_duration, ss.service_price
            FROM salon_appointment sa
            INNER JOIN salon_service ss ON sa.appointment_id = ss.appointment_id
            WHERE consumer_id = %s
            ORDER BY date_appoint DESC, slot ASC;
        """
        
        # Execute the query and fetch all matching rows
        rows = self.fetchall(query, (user_id,))

        # Return the results as a list of dictionaries containing the appointment and service details
        return [
            {
                "appointment_id": r[0],
                "status": r[1],
                "date_appoint": r[2],
                "slot": r[3],
                "venue": r[4],
                "provider_id": r[5],
                "provider_name": r[6],
                "service_name": r[7],
                "service_duration": r[8],
                "service_price": r[9]
            } for r in rows
        ]



    def get_appointments_by_client(self, user_id):
        """
        Return all appointments for a specific client, including basic service info.

        Args:
            user_id (int): The unique identifier of the client whose appointments are to be retrieved.

        Returns:
            list: A list of dictionaries, each containing the appointment details for the client, 
                including basic service information (service name).
        """
        # Define the SQL query to retrieve all appointments for the specified client, 
        # including basic service information by joining with the salon_service table
        query = """
            SELECT sa.appointment_id, sa.status, sa.date_appoint, sa.slot,
                sa.consumer_id, sa.consumer_name, sa.provider_id, sa.provider_name,
                ss.service_name
            FROM salon_appointment sa
            INNER JOIN salon_service ss ON sa.appointment_id = ss.appointment_id
            WHERE sa.consumer_id = %s
            ORDER BY sa.date_appoint ASC, sa.slot ASC;
        """
        
        # Execute the query and fetch all matching rows
        rows = self.fetchall(query, (user_id,))

        # Return the results as a list of dictionaries containing the appointment and basic service details
        return [
            {
                "appointment_id": r[0],
                "status": r[1],
                "date_appoint": r[2],
                "slot": r[3],
                "consumer_id": r[4],
                "consumer_name": r[5],
                "provider_id": r[6],
                "provider_name": r[7],
                "service_name": r[8]
            } for r in rows
        ]


    
    def get_appointments_by_professional(self, user_id):
        """
        Return all appointments for a specific professional, including basic client and service info.

        Args:
            user_id (int): The unique identifier of the professional whose appointments are to be retrieved.

        Returns:
            list: A list of dictionaries, each containing the appointment details for the professional, 
                including the client's basic information and the service details.
        """
        # Define the SQL query to retrieve all appointments for the specified professional,
        # including basic client information and service details by joining with the salon_service table
        query = """
            SELECT sa.appointment_id, sa.status, sa.date_appoint, sa.slot,
                sa.consumer_id, sa.consumer_name, sa.provider_id, sa.provider_name,
                ss.service_name
            FROM salon_appointment sa
            INNER JOIN salon_service ss ON sa.appointment_id = ss.appointment_id
            WHERE sa.provider_id = %s
            ORDER BY sa.date_appoint DESC, sa.slot ASC;
        """
        
        # Execute the query and fetch all matching rows
        rows = self.fetchall(query, (user_id,))

        # Return the results as a list of dictionaries containing the appointment, client, and service details
        return [
            {
                "appointment_id": r[0],
                "status": r[1],
                "date_appoint": r[2],
                "slot": r[3],
                "consumer_id": r[4],
                "consumer_name": r[5],
                "provider_id": r[6],
                "provider_name": r[7],
                "service_name": r[8]
            } for r in rows
        ]


    def update_appointment_status(self, appt_id, status):
        """
        Update the status of an appointment by its ID.

        Args:
            appt_id (int): The unique identifier of the appointment whose status is to be updated.
            status (str): The new status to set for the appointment.

        Returns:
            None: This method updates the appointment status in the database and does not return any value.
        """
        # Define the SQL query to update the status of the appointment based on its appointment_id
        query = "UPDATE salon_appointment SET status = %s WHERE appointment_id = %s"
        
        # Execute the query to update the appointment status
        self.execute_commit(query, (status, appt_id))


    
    def update_appointment(self, appointment_id, update_data):
        """
        Update appointment and related service details for a given appointment ID.

        Args:
            appointment_id (int): The unique identifier of the appointment to update.
            update_data (dict): A dictionary containing the updated appointment and service details, such as:
                                - 'provider_id' (int): The provider's ID.
                                - 'provider_name' (str): The provider's name.
                                - 'consumer_id' (int): The consumer's ID.
                                - 'consumer_name' (str): The consumer's name.
                                - 'status' (str): The status of the appointment.
                                - 'venue' (str): The venue of the appointment.
                                - 'date_appoint' (str): The new appointment date.
                                - 'slot' (str): The new appointment slot.
                                - 'service_name' (str): The name of the service.
                                - 'service_duration' (int): The duration of the service.
                                - 'service_price' (float): The price of the service.

        Returns:
            None: This method updates the appointment and related service data in the database and does not return a value.
        """
        
        # Define the SQL query to update the appointment details
        appointment_query = """
            UPDATE salon_appointment
            SET provider_id = %s,
                provider_name = %s,
                consumer_id = %s,
                consumer_name = %s,
                status = %s,
                venue = %s,
                date_appoint = %s,
                slot = %s
            WHERE appointment_id = %s;
        """
        appointment_values = (
            update_data["provider_id"],
            update_data["provider_name"],
            update_data["consumer_id"],
            update_data["consumer_name"],
            update_data["status"],
            update_data["venue"],
            update_data["date_appoint"],
            update_data["slot"],
            appointment_id
        )

        # Define the SQL query to update the service details
        service_query = """
            UPDATE salon_service
            SET service_name = %s,
                service_duration = %s,
                service_price = %s
            WHERE appointment_id = %s;
        """
        service_values = (
            update_data["service_name"],
            update_data["service_duration"],
            update_data["service_price"],
            appointment_id
        )

        # Execute both the appointment and service update queries
        with self.cursor() as cur:
            cur.execute(appointment_query, appointment_values)  # Update the appointment details
            cur.execute(service_query, service_values)  # Update the service details



    def delete_appointment(self, appt_id):
        """
        Delete an appointment and its associated service entry by appointment ID.

        Args:
            appt_id (int): The unique identifier of the appointment to delete.

        Returns:
            None: This method deletes the appointment and its associated service data from the database.
        """
        
        # Define the SQL query to delete the associated service for the given appointment ID
        delete_service_query = "DELETE FROM salon_service WHERE appointment_id = %s"
        
        # Define the SQL query to delete the appointment from the salon_appointment table
        delete_appointment_query = "DELETE FROM salon_appointment WHERE appointment_id = %s"
        
        # Execute the delete queries within a database transaction
        with self.cursor() as cur:
            cur.execute(delete_service_query, (appt_id,))  # Delete the associated service
            cur.execute(delete_appointment_query, (appt_id,))  # Delete the appointment


#---------------------REPORT METHODS
    def add_report(self, report_data):
        """
        Insert a new report linked to an appointment and return the report ID.

        Args:
            report_data (dict): A dictionary containing the report details, such as:
                                - 'appointment_id' (int): The ID of the associated appointment.
                                - 'status' (str, optional): The status of the report (default is 'inactive').
                                - 'feedback_professional' (str, optional): The professional's feedback (optional).
                                - 'feedback_client' (str, optional): The client's feedback (optional).

        Returns:
            int: The report ID of the newly created report.
        """
        # Define the SQL query to insert a new report into the salon_report table
        query = """
            INSERT INTO salon_report (
                appointment_id, status, feedback_professional, feedback_client
            ) VALUES (%s, %s, %s, %s)
            RETURNING report_id;
        """
        
        # Prepare the values to be inserted into the database
        values = (
            report_data["appointment_id"],  # Appointment ID (required)
            report_data.get("status", "inactive"),  # Default status is 'inactive'
            report_data.get("feedback_professional"),  # Professional feedback (optional)
            report_data.get("feedback_client")  # Client feedback (optional)
        )
        
        # Call the method to insert the values into the database and return the report ID
        return self.insert_and_return_id(query, values)



    def get_report_by_appointment(self, appointment_id):
        """
        Retrieve a report by its associated appointment ID.

        Args:
            appointment_id (int): The unique identifier of the appointment to retrieve the report for.

        Returns:
            dict or None: A dictionary containing the report details if found, or None if no report is found.
        """
        # Define the SQL query to retrieve the report based on the appointment ID
        query = "SELECT * FROM salon_report WHERE appointment_id = %s"
        
        # Execute the query and return the result
        return self.fetchone(query, (appointment_id,))


    def get_report_by_id(self, report_id):
        """
        Retrieve a report and related appointment information by report ID.

        Args:
            report_id (int): The unique identifier of the report to retrieve.

        Returns:
            dict or None: A dictionary containing the report and associated appointment details if found,
                        or None if no report is found.
        """
        # Define the SQL query to retrieve the report and related appointment info by report ID
        query = """
            SELECT r.report_id, r.appointment_id, r.status, r.date_report,
                r.feedback_professional, r.feedback_client, r.flagged_by_professional,
                a.consumer_name, a.provider_name
            FROM salon_report r
            JOIN salon_appointment a ON r.appointment_id = a.appointment_id
            WHERE r.report_id = %s
        """
        
        # Execute the query and fetch the result
        row = self.fetchone(query, (report_id,))
        
        # Return None if no result is found
        if not row:
            return None

        # Return the result as a dictionary
        return {
            "id": row[0],
            "appointment_id": row[1],
            "status": row[2],
            "date": row[3],
            "feedback_professional": row[4],
            "feedback_client": row[5],
            "flagged_by_professional": row[6],
            "consumer_name": row[7],
            "provider_name": row[8]
        }



    def update_report(self, report_id, updates):
        """
        Safely update specified fields of a report without overwriting missing data.

        Args:
            report_id (int): The unique identifier of the report to update.
            updates (dict): A dictionary of field-value pairs to update in the report.
                            Only the fields provided in the dictionary will be updated.
                            The keys should be the column names in the report table, 
                            and the values should be the new values to set.

        Returns:
            None: This method updates the report in the database and does not return a value.
        """
        # If there are no updates, do nothing
        if not updates:
            return

        # Build the set clause and values from the updates dictionary
        set_clause, values = self.build_update_clause(updates)

        # Define the SQL query to update the report based on the provided updates
        query = f"UPDATE salon_report SET {set_clause} WHERE report_id = %s"

        # Execute the query to update the report
        self.execute_commit(query, values + [report_id])


    def delete_report(self, report_id):
        """
        Delete a report by its ID, only if it exists.

        Args:
            report_id (int): The unique identifier of the report to delete.

        Returns:
            bool: True if the report was deleted successfully, False if no such report exists.
        """
        # Check if the report exists before attempting to delete
        if not self.exists("SELECT 1 FROM salon_report WHERE report_id = %s", (report_id,)):
            return False  # Return False if the report does not exist

        # Execute the SQL query to delete the report
        self.execute_commit("DELETE FROM salon_report WHERE report_id = %s", (report_id,))

        # Return True to indicate that the report was deleted
        return True

    
    def get_all_report(self):
        """
        Retrieve all reports from the salon_report table.

        Returns:
            list: A list of dictionaries, each representing a report from the salon_report table.
        """
        # Define the SQL query to retrieve all reports
        query = "SELECT * FROM salon_report"
        
        # Execute the query and fetch all results
        return self.fetchall(query)


    def get_reports_by_user(self, user_id):
        """
        Retrieve reports associated with a specific user (either as a consumer or provider).

        Args:
            user_id (int): The unique identifier of the user whose reports are to be retrieved.

        Returns:
            list: A list of dictionaries, each containing the report details for the user,
                including feedback from the client and professional, and appointment information.
        """
        # Define the SQL query to retrieve reports related to the given user (either consumer or provider)
        query = """
            SELECT r.report_id, r.appointment_id, r.status,
                r.feedback_client, r.feedback_professional, r.date_report
            FROM salon_report r
            JOIN salon_appointment a ON r.appointment_id = a.appointment_id
            WHERE a.consumer_id = %s OR a.provider_id = %s
            ORDER BY r.date_report DESC
        """
        
        # Execute the query and fetch all results as a list of dictionaries
        return self.fetchall_dict(query, (user_id, user_id))


    
    def has_report_for_appointment(self, appointment_id):
        """
        Check whether a report exists for the given appointment ID.

        Args:
            appointment_id (int): The unique identifier of the appointment to check.

        Returns:
            bool: True if a report exists for the appointment, False otherwise.
        """
        try:
            # Define the SQL query to check if a report exists for the given appointment_id
            query = 'SELECT 1 FROM salon_report WHERE appointment_id = %s LIMIT 1'
            
            # Execute the query and check if a report exists
            return self.exists(query, (appointment_id,))
        except Exception:
            # Log the exception if an error occurs
            logger.exception("Error checking report for appointment_id=%s", appointment_id)
            return False


    def get_pending_reports_for_professional(self, professional_id):
        """
        Get all client-submitted reports that the professional has not yet responded to.

        Args:
            professional_id (int): The unique identifier of the professional to retrieve pending reports for.

        Returns:
            list: A list of dictionaries representing reports that have client feedback but no professional response.
        """
        # Define the SQL query to retrieve all reports where the professional has not responded yet
        query = """
            SELECT r.*
            FROM salon_report r
            JOIN salon_appointment a ON r.appointment_id = a.appointment_id
            WHERE a.provider_id = %s
            AND r.feedback_client IS NOT NULL
            AND (r.feedback_professional IS NULL OR r.feedback_professional = '')
        """
        
        # Execute the query and fetch all matching reports as dictionaries
        return self.fetchall_dict(query, (professional_id,))


    def get_reports_with_new_professional_feedback(self, client_id):
        """
        Get reports that have new professional feedback unseen by the client.

        Args:
            client_id (int): The unique identifier of the client to retrieve reports for.

        Returns:
            list: A list of dictionaries containing report IDs that have professional feedback 
                and are marked as unseen by the client.
        """
        # Define the SQL query to retrieve reports with new professional feedback that the client hasn't seen
        query = """
            SELECT r.report_id
            FROM salon_report r
            JOIN salon_appointment a ON r.appointment_id = a.appointment_id
            WHERE a.consumer_id = %s
            AND r.feedback_professional IS NOT NULL
            AND (r.client_seen IS NULL OR r.client_seen = FALSE)
        """
        
        # Execute the query and fetch the results as dictionaries
        return self.fetchall_dict(query, (client_id,))


    def mark_reports_as_seen_by_client(self, report_ids):
        """
        Mark multiple reports as seen by the client.

        Args:
            report_ids (list): A list of report IDs to be marked as seen by the client.

        Returns:
            None: This method updates the 'client_seen' field for the provided report IDs.
        """
        # Define the SQL query to mark reports as seen by the client
        query = """
            UPDATE salon_report
            SET client_seen = TRUE
            WHERE report_id = ANY(%s)
        """
        
        # Execute the query to update the 'client_seen' field for the given report IDs
        self.update_many(query, report_ids)

    
    def mark_report_client_notified(self, report_id):
        """
        Mark a single report as having new feedback unseen by the client.

        Args:
            report_id (int): The unique identifier of the report to be marked.
        
        Returns:
            None: This method updates the 'client_seen' field for the specified report.
        """
        # Define the SQL query to mark the report as unseen by the client
        query = """
            UPDATE salon_report
            SET client_seen = FALSE
            WHERE report_id = %s
        """
        
        # Execute the query to mark the report as unseen by the client
        self.execute_commit(query, (report_id,))


    def get_reports_by_client(self, client_id):
        """
        Retrieve all reports submitted by a specific client.

        Args:
            client_id (int): The unique identifier of the client whose reports are to be retrieved.

        Returns:
            list: A list of dictionaries, each containing the report details for the specified client,
                including client and professional feedback and the report date.
        """
        # Define the SQL query to retrieve all reports submitted by the specified client
        query = """
            SELECT r.report_id, r.appointment_id, r.status,
                r.feedback_client, r.feedback_professional, r.date_report
            FROM salon_report r
            JOIN salon_appointment a ON r.appointment_id = a.appointment_id
            WHERE a.consumer_id = %s
            ORDER BY r.date_report DESC
        """
        
        # Execute the query and fetch the results as a list of dictionaries
        return self.fetchall_dict(query, (client_id,))

    
    def get_reports_by_professional(self, professional_id):
        """
        Retrieve all reports assigned to a specific professional.

        Args:
            professional_id (int): The unique identifier of the professional to retrieve reports for.

        Returns:
            list: A list of dictionaries representing the reports assigned to the specified professional.
        """
        # Define the SQL query to retrieve all reports assigned to the specified professional
        query = """
            SELECT r.*, a.provider_id
            FROM salon_report r
            JOIN salon_appointment a ON r.appointment_id = a.appointment_id
            WHERE a.provider_id = %s
            ORDER BY r.date_report DESC
        """
        
        # Execute the query and fetch the results as a list of dictionaries
        return self.fetchall_dict(query, (professional_id,))


    def check_if_report_exists(self, appointment_id):
        """
        Check if a report exists for a specific appointment.

        Args:
            appointment_id (int): The unique identifier of the appointment to check for an associated report.

        Returns:
            bool: True if a report exists for the appointment, False otherwise.
        """
        # Define the SQL query to check if a report exists for the given appointment ID
        query = "SELECT 1 FROM salon_report WHERE appointment_id = %s LIMIT 1"
        
        # Execute the query to check for the existence of the report
        return self.exists(query, (appointment_id,))

    
    def get_all_reports_with_details(self):
        """
        Retrieve all reports joined with appointment details.

        This method retrieves all reports from the salon_report table and includes additional appointment details
        (such as consumer and provider names) by joining with the salon_appointment table.

        Returns:
            list: A list of dictionaries, each containing detailed information about the report and the associated appointment.
        """
        # Define the SQL query to retrieve all reports along with associated appointment details
        query = """
            SELECT r.report_id, r.appointment_id, r.feedback_client, r.feedback_professional,
                r.status, r.date_report, r.flagged_by_professional,
                a.consumer_name, a.provider_name
            FROM salon_report r
            JOIN salon_appointment a ON r.appointment_id = a.appointment_id
            ORDER BY r.date_report DESC
        """
        
        # Execute the query and fetch all results
        rows = self.fetchall(query)

        # Return the results as a list of dictionaries, each containing report and appointment details
        return [
            {
                "id": r[0],
                "appointment_id": r[1],
                "client_feedback": r[2],
                "professional_response": r[3],
                "status": r[4],
                "date": r[5],
                "flagged_by_professional": r[6],
                "client_name": r[7],
                "professional_name": r[8]
            }
            for r in rows
        ]

    
    def flag_report_by_professional(self, report_id):
        """
        Mark a report as flagged by the professional for admin attention.

        Args:
            report_id (int): The unique identifier of the report to flag.

        Returns:
            None: This method updates the 'flagged_by_professional' field in the database to TRUE.
        """
        # Define the SQL query to update the report's 'flagged_by_professional' field to TRUE
        query = """
            UPDATE salon_report
            SET flagged_by_professional = TRUE
            WHERE report_id = %s
        """
        
        # Execute the query to flag the report
        self.execute_commit(query, (report_id,))


    def unflag_report_by_professional(self, report_id):
        """
        Remove the professional flag from a report.

        Args:
            report_id (int): The unique identifier of the report to unflag.

        Returns:
            None: This method updates the 'flagged_by_professional' field in the database to FALSE.
        """
        # Define the SQL query to update the report's 'flagged_by_professional' field to FALSE
        query = """
            UPDATE salon_report
            SET flagged_by_professional = FALSE
            WHERE report_id = %s
        """
        
        # Execute the query to unflag the report
        self.execute_commit(query, (report_id,))


    def get_report_by_appointment_id(self, appointment_id):
        """
        Retrieve a report by its associated appointment ID.

        Args:
            appointment_id (int): The unique identifier of the appointment to retrieve the report for.

        Returns:
            dict or None: The report details as a dictionary if found, or None if no report exists for the appointment.
        """
        # Define the SQL query to retrieve the report associated with the given appointment ID
        query = "SELECT * FROM salon_report WHERE appointment_id = %s"
        
        # Execute the query and fetch the result
        return self.fetchone(query, (appointment_id,))


# --------------EXTRAS

    def log_admin_action(self, action_text, action_by):
        """
        Log an admin action to the salon_log table.

        Args:
            action_text (str): A description of the action performed by the admin.
            action_by (str): The username or identifier of the admin performing the action.

        Returns:
            None: This method logs the admin action into the salon_log table.
        """
        # Define the SQL query to insert the admin action into the salon_log table
        query = "INSERT INTO salon_log (user_action, action_by) VALUES (%s, %s)"
        
        # Execute the query to log the admin action
        self.execute_commit(query, (action_text, action_by))


    def get_service_choices(self):
        """
        Get a list of distinct service options formatted for dropdowns.

        Returns:
            list: A list of tuples, where each tuple contains an index and a formatted string with service details
                (service name, service duration, and service price).
        """
        # Define the SQL query to retrieve distinct service options from the salon_service table
        query = """
            SELECT DISTINCT service_name, service_duration, service_price
            FROM salon_service
            ORDER BY service_name;
        """
        
        # Execute the query and fetch all the rows
        rows = self.fetchall(query)

        # Return a list of tuples with the formatted service information
        return [(i, f"{r[0]} - {r[1]} mins - ${r[2]:.2f}") for i, r in enumerate(rows)]


    def get_client_choices(self):
        """
        Return a list of client (user_id, full name) tuples for dropdown menus.

        Returns:
            list: A list of tuples, where each tuple contains a client user ID and the client's full name.
        """
        # Define the SQL query to retrieve all clients, ordered by their first name
        query = """
            SELECT user_id, fname, lname 
            FROM salon_user 
            WHERE user_type = 'client'
            ORDER BY fname;
        """
        
        # Execute the query and fetch all the rows
        rows = self.fetchall(query)

        # Return the results as a list of tuples with the client user ID and full name
        return [(r[0], f"{r[1]} {r[2]}") for r in rows]


    def get_provider_choices(self):
        """
        Return a list of professional (user_id, full name) tuples for dropdown menus.

        Returns:
            list: A list of tuples, where each tuple contains a professional user ID and the professional's full name.
        """
        # Define the SQL query to retrieve all professionals, ordered by their first name
        query = """
            SELECT user_id, fname, lname 
            FROM salon_user 
            WHERE user_type = 'professional'
            ORDER BY fname;
        """
        
        # Execute the query and fetch all the rows
        rows = self.fetchall(query)

        # Return the results as a list of tuples with the professional user ID and full name
        return [(r[0], f"{r[1]} {r[2]}") for r in rows]
    

    def insert_returning_id(self, query, values):
        """
        Execute an INSERT query with a RETURNING clause and return the generated ID.

        Args:
            query (str): The SQL query to execute, expected to include an INSERT statement.
            values (tuple): A tuple of values to insert into the query.

        Returns:
            int: The ID of the newly inserted row, typically the 'appointment_id' or equivalent.
        """
        # Remove any leading or trailing whitespace from the query
        full_query = query.strip()
        
        # Ensure the query includes the "RETURNING appointment_id" clause if not already present
        if not full_query.lower().endswith("returning appointment_id"):
            full_query += " RETURNING appointment_id"

        # Execute the query with the provided values and return the generated ID
        with self.cursor() as cur:
            cur.execute(full_query, values)  # Execute the query with values
            return cur.fetchone()[0]  # Return the generated ID (first value in the result)

    
# -------------------UTILITY

    def fetchone(self, query, params=None):
        """
        Execute a query and fetch a single result.

        Args:
            query (str): The SQL query to execute.
            params (tuple, optional): A tuple of parameters to pass with the query.

        Returns:
            tuple or None: A single row from the query result, or None if no result is found.
        """
        with self.cursor() as cur:
            cur.execute(query, params)  # Execute the query with parameters
            return cur.fetchone()  # Return the first result (or None if no result)


    def fetchall(self, query, params=None):
        """
        Execute a query and fetch all results.

        Args:
            query (str): The SQL query to execute.
            params (tuple, optional): A tuple of parameters to pass with the query.

        Returns:
            list: A list of rows from the query result.
        """
        with self.cursor() as cur:
            cur.execute(query, params)  # Execute the query with parameters
            return cur.fetchall()  # Return all results


    def execute_commit(self, query, params=None):
        """
        Execute a query and commit the transaction.

        Args:
            query (str): The SQL query to execute.
            params (tuple, optional): A tuple of parameters to pass with the query.

        Returns:
            None: This method does not return any value but commits the transaction.
        """
        with self.cursor() as cur:
            cur.execute(query, params)  # Execute the query with parameters


    def insert_and_return_id(self, query, values):
        """
        Execute an INSERT query with values and return the generated ID.

        Args:
            query (str): The SQL INSERT query to execute.
            values (tuple): A tuple of values to insert into the query.

        Returns:
            int: The ID of the newly inserted row (typically the 'appointment_id' or equivalent).
        """
        with self.cursor() as cur:
            cur.execute(query, values)  # Execute the query with the provided values
            return cur.fetchone()[0]  # Return the generated ID (first value in the result)


    def build_update_clause(self, data):
        """
        Build an SQL UPDATE clause from a dictionary of column-value pairs.

        Args:
            data (dict): A dictionary of column names as keys and values to update as values.

        Returns:
            tuple: A tuple containing the SET clause (string) and a list of values.
        """
        set_clause = ", ".join(f"{k} = %s" for k in data)  # Create the SET clause
        values = list(data.values())  # Extract the values from the dictionary
        return set_clause, values  # Return the set_clause and values


    def exists(self, query, params):
        """
        Check if a record exists based on the provided query.

        Args:
            query (str): The SQL query to execute.
            params (tuple): A tuple of parameters to pass with the query.

        Returns:
            bool: True if a record exists, False otherwise.
        """
        return self.fetchone(query, params) is not None  # Return True if the record exists, otherwise False


    def update_many(self, query, ids):
        """
        Execute an update query for multiple records.

        Args:
            query (str): The SQL query to execute.
            ids (tuple): A tuple of IDs to update.

        Returns:
            None: This method executes the update query and commits the transaction.
        """
        if ids:  # Only execute if IDs are provided
            self.execute_commit(query, (ids,))  # Execute the query to update multiple records


    def fetchall_dict(self, query, params=None):
        """
        Execute a query and fetch all results as a list of dictionaries.

        Args:
            query (str): The SQL query to execute.
            params (tuple, optional): A tuple of parameters to pass with the query.

        Returns:
            list: A list of dictionaries, each representing a row in the query result.
        """
        with self.__connection.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)  # Execute the query with parameters
            return cur.fetchall()  # Return all results as a list of dictionaries



# ----------------- Messages Methods

    def create_message(self, message_data):
        """
        Insert a new message into the Messages table and return the new message ID.

        Args:
            message_data (dict): A dictionary containing the message data to be inserted.
                            Expected keys: group_name, members, sender_id, sender_username, contents.

        Returns:
            int: The message ID of the newly inserted message.
        """
        # Define the SQL query for inserting a new message into the Messages table
        query = """
        INSERT INTO MESSAGES (group_name, sender_id, sender_username, members , contents)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING message_id;
        """

        # Prepare the values to insert into the database
        values = (
            message_data["group_name"], # Group name (required)
            message_data["sender_id"],  # Set to Logged user
            message_data["sender_username"],  # Sender Username (required)
            message_data["members"],  # Members (required), always include Logged User + another user (minimum)
            message_data["contents"],  # Content (required)
        )

        # Insert the new message and return the message_id of the newly created message
        return self.insert_and_return_id(query, values)



    def get_all_messages(self):
        """
        Retrieve all messages with basic identifying information from the database.

        This method fetches the message ID, group_name, sender_id and time_sent for every message in the system.

        Returns:
            list: A list of dictionaries, each containing the 'id', 'group_name', sender_id and 'time_sent' of a message.
        """
        # Define the SQL query to retrieve basic user details
        query = "SELECT message_id, group_name, sender_id, sender_username, time_sent FROM messages;"

        # Execute the query and fetch all rows
        rows = self.fetchall(query)

        # Return a list of dictionaries with user information
        return [{"id": r[0], "group_name": r[1], "sender_id": r[2], "sender_username": r[3], "time_sent": r[4]} for r in rows]



    def get_message_by_id(self, message_id):
        """
        Retrieve a message record from the database by their unique message ID.

        Args:
            message_id (int): The unique identifier of the message to retrieve.

        Returns:
            dict or None: A dictionary containing the message's information if found, 
                        or None if the message does not exist.
        """
        # Define the SQL query to retrieve the message's details based on their message_id
        query = """
            SELECT
            message_id,
            group_name,
            members,
            sender_id,
            sender_username,
            time_sent,
            contents
            FROM messages
            WHERE message_id = %s;
        """

        # Execute the query and return the first result as a dictionary
        return self.fetchone(query, (message_id,))
    

    def get_messages_by_group_name(self, group_name):
        """
        Retrieve all messages that match a specific group name.

        Args:
            group_name (str): The group name to filter by (e.g., 'rix_andrew', 'funtime2025').

        Returns:
            list: A list of dictionaries, each containing the details of a message with the specified group_name.
        """
        # Define the SQL query to retrieve messages with the specified group_name
        query = """
            SELECT DISTINCT 
            m.sender_username, m.contents, m.time_sent, m.members
            FROM messages m
            JOIN messages as m2 on m.group_name = m2.group_name
            WHERE m.group_name = %s
            ORDER BY m.time_sent ASC;
        """

        # Execute the query and return all matching results as a list of dictionaries
        return self.fetchall(query, (group_name,))
    

    def get_group_name_by_member(self, member):
        """
        Retrieve all Groups name that match a specific member.

        Args:
            member (str): The username of an existing user to filter by (e.g., 'rix', 'andrew').

        Returns:
            list: A list of dictionaries, each containing the details of a message with the specified group_name.
        """
        # Define the SQL query to retrieve the group_name with the specified member
        query = f"""
            SELECT DISTINCT group_name from messages
            WHERE members LIKE '%{member}%';
        """

        # Execute the query and return all matching results as a list of dictionaries
        return self.fetchall(query)




class DatabaseConnectionError(Exception):
    """
    Custom exception for database connection failures.

    This exception is raised when a connection to the database cannot be established.
    It helps to differentiate database connection issues from other types of exceptions.
    """
    pass  # No additional implementation needed for this custom exception


# Create an instance of the Database class
db = Database()

if __name__ == '__main__':
    # Uncomment the line below to start the debugger if needed
    # pdb.set_trace()
    
    # Run an SQL script to initialize the database schema or data
    db.run_sql_script('./sec1-database.sql')


class UserType:
    """
    Class to define constants for different user types in the system.

    These constants are used for distinguishing between different roles such as 'client', 'professional', and 'admin'.
    """
    CLIENT = 'client'  # Represents a client user type
    PROFESSIONAL = 'professional'  # Represents a professional user type
    ADMIN_SUPER = 'admin_super'  # Represents a super admin user type


class AppointmentStatus:
    """
    Class to define constants for various appointment statuses.

    These constants are used to represent the current status of an appointment (requested, accepted, cancelled).
    """
    REQUESTED = 'requested'  # Appointment has been requested but not yet accepted
    ACCEPTED = 'accepted'  # Appointment has been accepted by the provider
    CANCELLED = 'cancelled'  # Appointment has been cancelled

