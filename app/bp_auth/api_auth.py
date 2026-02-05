from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token
from app.bp_auth.user import User
from models.database import db

bp_api_auth = Blueprint("bp_api_auth", __name__)

@bp_api_auth.route("/api/login", methods=["POST"])
def api_login():
    """
    API endpoint for JWT-based user login.

    Accepts a JSON body with 'user_name' and 'password'. If credentials are valid,
    returns a JWT access token that includes the user's ID and username as claims.

    Request JSON:
        {
            "user_name": "example",
            "password": "secret"
        }

    Returns:
        JSON: JWT token on success (200), or error message on failure (401).
    """
    data = request.get_json()
    username = data.get("user_name")
    password = data.get("password")

    # Fetch user and validate password
    user = User.get_user_by_username(username)
    if user and db.check_password(username, password):
        # Generate JWT with user's ID and username as claims
        token = create_access_token(
            identity=str(user.id),
            additional_claims={"username": user.user_name}
        )
        return jsonify(access_token=token), 200

    # Invalid credentials
    return jsonify({"msg": "Invalid credentials"}), 401
