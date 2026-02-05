"""Import FLASK Module, Database and BLUEPRINTS"""
from flask import Flask, render_template
from flask_login import LoginManager
from flask_caching import Cache
from flask_jwt_extended import JWTManager
from config import Config
from models.database import db

# Initialize Flask extensions
login_manager = LoginManager()
login_manager.login_view = 'bp_auth.login'  # Redirect to login page if user is not logged in
cache = Cache(config={'CACHE_TYPE': 'SimpleCache'})  # Simple cache configuration
jwt = JWTManager()  # JWT manager for handling JSON Web Tokens



@login_manager.user_loader
def load_user(user_id):
    """
    Callback function to load a user by their ID.

    Args:
        user_id (int): The ID of the user to load.

    Returns:
        User: The User object associated with the given ID, or None if not found.
    """
    from app.bp_auth.user import User
    return User.get_user_by_id(user_id)

def create_app():
    """
    Create and configure the Flask application.

    Initializes various Flask extensions and registers blueprints for the application.

    Returns:
        Flask app: The configured Flask application instance.
    """
    # Create a new Flask application instance
    app = Flask(__name__)

    # Load the configuration settings from the Config class
    app.config.from_object(Config)

    # Set up the secret key for JWT (for encoding and decoding tokens)
    app.config["JWT_SECRET_KEY"] = "super-secret-key"  
    jwt.init_app(app)  # Initialize JWT manager with the app

    # Initialize the Flask extensions with the app
    login_manager.init_app(app)
    cache.init_app(app)

    # Import blueprints for different parts of the application
    from app.bp_main.routes import bp_main
    from app.bp_admin.routes import bp_admin
    from app.bp_appointment.routes import bp_appointment
    from app.bp_api.routes import bp_api
    from app.bp_auth.routes import bp_auth
    from app.bp_report.routes import bp_report
    from app.bp_auth.api_auth import bp_api_auth

    # Register all the blueprints with the app
    app.register_blueprint(bp_main)
    app.register_blueprint(bp_admin)
    app.register_blueprint(bp_appointment)
    app.register_blueprint(bp_api, url_prefix="/api")  # API routes prefixed with /api
    app.register_blueprint(bp_auth)
    app.register_blueprint(bp_report)
    app.register_blueprint(bp_api_auth)

    @app.errorhandler(404)
    def page_not_found(e):
        """Render a custom 404 error page."""
        return render_template("404page.html"), 404

    return app
