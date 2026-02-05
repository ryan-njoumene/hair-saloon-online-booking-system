import os
import secrets

class Config:
    """
    Configuration class for the application.

    This class stores configuration settings such as the secret key for the application
    and database connection parameters. Configuration values can be fetched from environment
    variables, and if they are not set, default values are used.
    """
    
    # Secret key for the application (used for signing sessions, cookies, etc.)
    SECRET_KEY = os.environ.get("SECRET_KEY", secrets.token_hex())  # Default to a generated key if not set
    
    # Database connection settings (using environment variables with defaults)
    DATABASE_HOST = os.environ.get("DATABASE_HOST", "db")  # Default to 'db' if not set
    DATABASE_NAME = os.environ.get("DATABASE_NAME", "python_project")  # Default to 'python_project' if not set
    DATABASE_USER = os.environ.get("DATABASE_USER", "andrew")  # Default to 'andrew' if not set
    DATABASE_PASSWORD = os.environ.get("DATABASE_PASSWORD", "password")  # Default to 'password' if not set
    DATABASE_PORT = int(os.environ.get("DATABASE_PORT", 5432))  # Default to port 5432 if not set

# For debugging: Print the database configuration to verify the values
print(Config.DATABASE_HOST, Config.DATABASE_NAME, Config.DATABASE_USER, Config.DATABASE_PASSWORD, Config.DATABASE_PORT)