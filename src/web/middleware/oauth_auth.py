"""
OAuth2/OIDC authentication module for Flask
Supports Azure AD, Google Workspace, Okta, and generic OIDC providers
"""

import os
from typing import Optional, Dict, Any
from functools import wraps
from datetime import datetime, timedelta

from flask import request, jsonify, redirect, session, url_for
from authlib.integrations.flask_client import OAuth
from authlib.integrations.base_client import OAuthError
import jwt
from loguru import logger


class OAuthProvider:
    """OAuth2/OIDC provider configuration"""

    AZURE_AD = "azure"
    GOOGLE = "google"
    OKTA = "okta"
    GENERIC = "generic"


class OIDCAuthenticator:
    """
    OAuth2/OIDC authentication handler

    Features:
    - Multiple provider support (Azure AD, Google, Okta)
    - Token validation and refresh
    - Role-based access control (RBAC)
    - Session management
    """

    def __init__(self, app=None):
        self.app = app
        self.oauth = OAuth()
        self.providers = {}

        if app:
            self.init_app(app)

    def init_app(self, app):
        """Initialize OAuth with Flask app"""
        self.app = app
        self.oauth.init_app(app)

        # Configure session
        app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "dev-secret-key-change-in-prod")
        app.config["SESSION_TYPE"] = "filesystem"

        # Register providers
        self._register_providers()

    def _register_providers(self):
        """Register OAuth providers based on environment variables"""

        # Azure AD / Microsoft Entra ID
        if os.getenv("AZURE_CLIENT_ID"):
            self.providers["azure"] = self.oauth.register(
                name="azure",
                client_id=os.getenv("AZURE_CLIENT_ID"),
                client_secret=os.getenv("AZURE_CLIENT_SECRET"),
                server_metadata_url=f"https://login.microsoftonline.com/{os.getenv('AZURE_TENANT_ID')}/.well-known/openid-configuration",
                client_kwargs={"scope": "openid email profile User.Read"},
            )
            logger.info("Azure AD OAuth provider registered")

        # Google Workspace
        if os.getenv("GOOGLE_CLIENT_ID"):
            self.providers["google"] = self.oauth.register(
                name="google",
                client_id=os.getenv("GOOGLE_CLIENT_ID"),
                client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
                server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
                client_kwargs={"scope": "openid email profile"},
            )
            logger.info("Google OAuth provider registered")

        # Okta
        if os.getenv("OKTA_CLIENT_ID"):
            okta_domain = os.getenv("OKTA_DOMAIN")
            self.providers["okta"] = self.oauth.register(
                name="okta",
                client_id=os.getenv("OKTA_CLIENT_ID"),
                client_secret=os.getenv("OKTA_CLIENT_SECRET"),
                server_metadata_url=f"https://{okta_domain}/.well-known/openid-configuration",
                client_kwargs={"scope": "openid email profile"},
            )
            logger.info("Okta OAuth provider registered")

        # Generic OIDC provider
        if os.getenv("OIDC_CLIENT_ID"):
            self.providers["generic"] = self.oauth.register(
                name="generic",
                client_id=os.getenv("OIDC_CLIENT_ID"),
                client_secret=os.getenv("OIDC_CLIENT_SECRET"),
                server_metadata_url=os.getenv("OIDC_DISCOVERY_URL"),
                client_kwargs={"scope": "openid email profile"},
            )
            logger.info("Generic OIDC provider registered")

    def login(self, provider: str = "azure"):
        """
        Initiate OAuth login flow

        Args:
            provider: OAuth provider (azure, google, okta, generic)

        Returns:
            Redirect to OAuth provider
        """
        if provider not in self.providers:
            return jsonify({"error": f"Provider {provider} not configured"}), 400

        redirect_uri = url_for("auth_callback", provider=provider, _external=True)
        return self.providers[provider].authorize_redirect(redirect_uri)

    def callback(self, provider: str):
        """
        Handle OAuth callback

        Args:
            provider: OAuth provider name

        Returns:
            User info and tokens
        """
        if provider not in self.providers:
            return jsonify({"error": f"Provider {provider} not configured"}), 400

        try:
            # Get access token
            token = self.providers[provider].authorize_access_token()

            # Get user info
            if provider == "azure":
                resp = self.providers[provider].get("https://graph.microsoft.com/v1.0/me")
                user_info = resp.json()

                user_data = {
                    "id": user_info.get("id"),
                    "email": user_info.get("mail") or user_info.get("userPrincipalName"),
                    "name": user_info.get("displayName"),
                    "provider": provider,
                }

            elif provider == "google":
                user_info = token.get("userinfo")

                user_data = {
                    "id": user_info.get("sub"),
                    "email": user_info.get("email"),
                    "name": user_info.get("name"),
                    "provider": provider,
                }

            else:
                # Generic OIDC or Okta
                user_info = token.get("userinfo")

                user_data = {
                    "id": user_info.get("sub"),
                    "email": user_info.get("email"),
                    "name": user_info.get("name"),
                    "provider": provider,
                }

            # Store in session
            session["user"] = user_data
            session["access_token"] = token.get("access_token")
            session["refresh_token"] = token.get("refresh_token")

            # Generate JWT for API access
            jwt_token = self._generate_jwt(user_data)

            logger.info(f"User {user_data['email']} logged in via {provider}")

            return {"user": user_data, "jwt_token": jwt_token, "expires_in": 3600}

        except OAuthError as e:
            logger.error(f"OAuth error: {e}")
            return jsonify({"error": "Authentication failed", "details": str(e)}), 401

    def _generate_jwt(self, user_data: Dict[str, Any]) -> str:
        """Generate JWT token for API access"""
        payload = {
            "sub": user_data["id"],
            "email": user_data["email"],
            "name": user_data["name"],
            "provider": user_data["provider"],
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(hours=1),
            "roles": self._get_user_roles(user_data["email"]),
        }

        secret = self.app.config["SECRET_KEY"]
        return jwt.encode(payload, secret, algorithm="HS256")

    def _get_user_roles(self, email: str) -> list:
        """
        Get user roles from database or config
        Default implementation - override with your RBAC logic
        """
        # TODO: Query from database or directory
        # For now, simple email-based rules
        if email.endswith("@admin.com"):
            return ["admin", "engineer", "viewer"]
        elif email.endswith("@company.com"):
            return ["engineer", "viewer"]
        else:
            return ["viewer"]

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify JWT token

        Args:
            token: JWT token string

        Returns:
            Decoded token payload or None
        """
        try:
            secret = self.app.config["SECRET_KEY"]
            payload = jwt.decode(token, secret, algorithms=["HS256"])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None

    def logout(self):
        """Clear session and logout user"""
        user = session.get("user")
        if user:
            logger.info(f"User {user.get('email')} logged out")

        session.clear()
        return {"message": "Logged out successfully"}


# Flask decorators for route protection


def require_auth(f):
    """
    Decorator to require authentication

    Usage:
        @app.route('/api/protected')
        @require_auth
        def protected():
            return {'data': 'secret'}
    """

    @wraps(f)
    def decorated(*args, **kwargs):
        # Check session first
        if "user" in session:
            return f(*args, **kwargs)

        # Check JWT token in Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return jsonify({"error": "No authentication provided"}), 401

        try:
            # Extract token (format: "Bearer <token>")
            token = auth_header.split(" ")[1]

            # Verify token
            authenticator = request.app.extensions.get("oidc_auth")
            if not authenticator:
                return jsonify({"error": "Auth not configured"}), 500

            payload = authenticator.verify_token(token)
            if not payload:
                return jsonify({"error": "Invalid or expired token"}), 401

            # Attach user info to request
            request.user = payload

            return f(*args, **kwargs)

        except (IndexError, AttributeError):
            return jsonify({"error": "Invalid authorization header"}), 401

    return decorated


def require_role(*required_roles):
    """
    Decorator to require specific roles

    Usage:
        @app.route('/api/admin')
        @require_auth
        @require_role('admin')
        def admin_only():
            return {'data': 'admin-only'}
    """

    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            # Get user from session or request
            user = session.get("user") or getattr(request, "user", None)

            if not user:
                return jsonify({"error": "Authentication required"}), 401

            # Get user roles
            user_roles = user.get("roles", [])

            # Check if user has required role
            if not any(role in user_roles for role in required_roles):
                return jsonify({"error": "Insufficient permissions"}), 403

            return f(*args, **kwargs)

        return decorated

    return decorator


# Example Flask app integration
"""
from flask import Flask
from oauth_auth import OIDCAuthenticator, require_auth, require_role

app = Flask(__name__)

# Initialize OAuth
oidc_auth = OIDCAuthenticator(app)
app.extensions['oidc_auth'] = oidc_auth

# Login route
@app.route('/auth/login/<provider>')
def login(provider):
    return oidc_auth.login(provider)

# Callback route
@app.route('/auth/callback/<provider>')
def auth_callback(provider):
    result = oidc_auth.callback(provider)
    if isinstance(result, dict):
        # Successful login
        return jsonify(result)
    return result  # Error response

# Logout route
@app.route('/auth/logout')
def logout():
    return jsonify(oidc_auth.logout())

# Protected routes
@app.route('/api/profile')
@require_auth
def profile():
    user = session.get('user') or request.user
    return jsonify(user)

@app.route('/api/admin/users')
@require_auth
@require_role('admin')
def admin_users():
    return jsonify({'users': [...]})

@app.route('/api/engineer/designs')
@require_auth
@require_role('engineer', 'admin')
def engineer_designs():
    return jsonify({'designs': [...]})
"""
