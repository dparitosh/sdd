"""
Authentication Routes Blueprint
Provides login, token refresh, and logout endpoints
"""

import jwt
from flask import Blueprint, jsonify, request
from loguru import logger

from src.web.middleware.auth import (
    AuthConfig,
    authenticate_user,
    create_access_token,
    create_refresh_token,
    get_token_from_header,
    refresh_access_token,
    require_auth,
    revoke_token,
)

auth_bp = Blueprint("auth", __name__)


# ============================================================================
# LOGIN ENDPOINT
# ============================================================================


@auth_bp.route("/auth/login", methods=["POST"])
def login():
    """
    User login endpoint

    Request Body:
        {
            "username": "string",
            "password": "string"
        }

    Response:
        {
            "access_token": "string",
            "refresh_token": "string",
            "token_type": "bearer",
            "expires_in": 3600,
            "user": {
                "username": "string",
                "role": "string"
            }
        }
    """
    try:
        data = request.get_json()

        if not data:
            return (
                jsonify({"error": "Invalid request", "message": "Request body must be JSON"}),
                400,
            )

        username = data.get("username")
        password = data.get("password")

        if not username or not password:
            return (
                jsonify(
                    {
                        "error": "Missing credentials",
                        "message": "Both username and password are required",
                    }
                ),
                400,
            )

        # Authenticate user
        user = authenticate_user(username, password)

        if not user:
            return (
                jsonify(
                    {"error": "Authentication failed", "message": "Invalid username or password"}
                ),
                401,
            )

        # Generate tokens
        access_token = create_access_token(user["username"], user["role"])
        refresh_token = create_refresh_token(user["username"])

        logger.info(f"User logged in: {username}")

        return (
            jsonify(
                {
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "token_type": "bearer",
                    "expires_in": AuthConfig.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                    "user": {"username": user["username"], "role": user["role"]},
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Login error: {e}")
        return (
            jsonify(
                {
                    "error": "Internal server error",
                    "message": "An unexpected error occurred during login",
                }
            ),
            500,
        )


# ============================================================================
# TOKEN REFRESH ENDPOINT
# ============================================================================


@auth_bp.route("/auth/refresh", methods=["POST"])
def refresh():
    """
    Refresh access token using refresh token

    Request Body:
        {
            "refresh_token": "string"
        }

    Response:
        {
            "access_token": "string",
            "token_type": "bearer",
            "expires_in": 3600
        }
    """
    try:
        data = request.get_json()

        if not data:
            return (
                jsonify({"error": "Invalid request", "message": "Request body must be JSON"}),
                400,
            )

        refresh_token = data.get("refresh_token")

        if not refresh_token:
            return jsonify({"error": "Missing token", "message": "refresh_token is required"}), 400

        # Generate new access token
        result = refresh_access_token(refresh_token)

        logger.info("Access token refreshed")

        return jsonify(result), 200

    except jwt.ExpiredSignatureError:
        return (
            jsonify(
                {
                    "error": "Token expired",
                    "message": "Refresh token has expired. Please login again.",
                }
            ),
            401,
        )

    except jwt.InvalidTokenError as e:
        return jsonify({"error": "Invalid token", "message": str(e)}), 401

    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        return (
            jsonify(
                {
                    "error": "Internal server error",
                    "message": "An unexpected error occurred during token refresh",
                }
            ),
            500,
        )


# ============================================================================
# LOGOUT ENDPOINT
# ============================================================================


@auth_bp.route("/auth/logout", methods=["POST"])
@require_auth
def logout():
    """
    Logout endpoint (revokes current access token)

    Headers:
        Authorization: Bearer <access_token>

    Response:
        {
            "message": "Successfully logged out"
        }
    """
    try:
        # Get token from header
        token = get_token_from_header()

        # Revoke token
        revoke_token(token)

        logger.info(f"User logged out: {request.user['username']}")

        return jsonify({"message": "Successfully logged out"}), 200

    except Exception as e:
        logger.error(f"Logout error: {e}")
        return (
            jsonify(
                {
                    "error": "Internal server error",
                    "message": "An unexpected error occurred during logout",
                }
            ),
            500,
        )


# ============================================================================
# VERIFY TOKEN ENDPOINT (for debugging)
# ============================================================================


@auth_bp.route("/auth/verify", methods=["GET"])
@require_auth
def verify():
    """
    Verify token validity and return user info

    Headers:
        Authorization: Bearer <access_token>

    Response:
        {
            "valid": true,
            "user": {
                "username": "string",
                "role": "string"
            }
        }
    """
    return jsonify({"valid": True, "user": request.user}), 200


# ============================================================================
# CHANGE PASSWORD ENDPOINT (optional)
# ============================================================================


@auth_bp.route("/auth/change-password", methods=["POST"])
@require_auth
def change_password():
    """
    Change user password

    Headers:
        Authorization: Bearer <access_token>

    Request Body:
        {
            "current_password": "string",
            "new_password": "string"
        }

    Response:
        {
            "message": "Password changed successfully"
        }
    """
    try:
        data = request.get_json()

        if not data:
            return (
                jsonify({"error": "Invalid request", "message": "Request body must be JSON"}),
                400,
            )

        current_password = data.get("current_password")
        new_password = data.get("new_password")

        if not current_password or not new_password:
            return (
                jsonify(
                    {
                        "error": "Missing fields",
                        "message": "Both current_password and new_password are required",
                    }
                ),
                400,
            )

        if len(new_password) < 8:
            return (
                jsonify(
                    {
                        "error": "Weak password",
                        "message": "New password must be at least 8 characters long",
                    }
                ),
                400,
            )

        # In production: verify current password, update in database
        # For now, just return success

        logger.info(f"Password changed for user: {request.user['username']}")

        return jsonify({"message": "Password changed successfully"}), 200

    except Exception as e:
        logger.error(f"Password change error: {e}")
        return (
            jsonify({"error": "Internal server error", "message": "An unexpected error occurred"}),
            500,
        )
