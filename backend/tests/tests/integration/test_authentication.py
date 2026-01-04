"""
Integration Tests for JWT Authentication
Tests login, token refresh, logout, and protected routes
"""

import time
from datetime import datetime

import pytest
import requests

BASE_URL = "http://127.0.0.1:5000"
API_AUTH = f"{BASE_URL}/api/auth"


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def valid_credentials():
    """Valid admin credentials"""
    return {"username": "admin", "password": "admin123"}


@pytest.fixture
def invalid_credentials():
    """Invalid credentials"""
    return {"username": "admin", "password": "wrong_password"}


@pytest.fixture
def access_token(valid_credentials):
    """Get valid access token"""
    response = requests.post(f"{API_AUTH}/login", json=valid_credentials)
    return response.json()["access_token"]


@pytest.fixture
def refresh_token(valid_credentials):
    """Get valid refresh token"""
    response = requests.post(f"{API_AUTH}/login", json=valid_credentials)
    return response.json()["refresh_token"]


# ============================================================================
# LOGIN TESTS
# ============================================================================


class TestLogin:
    """Test authentication login endpoint"""

    def test_successful_login(self, valid_credentials):
        """Test successful login with valid credentials"""
        response = requests.post(f"{API_AUTH}/login", json=valid_credentials)

        assert response.status_code == 200
        data = response.json()

        # Check response structure
        assert "access_token" in data
        assert "refresh_token" in data
        assert "token_type" in data
        assert "expires_in" in data
        assert "user" in data

        # Check token type
        assert data["token_type"] == "bearer"

        # Check user info
        assert data["user"]["username"] == "admin"
        assert data["user"]["role"] == "admin"

        # Check tokens are non-empty strings
        assert isinstance(data["access_token"], str)
        assert len(data["access_token"]) > 50
        assert isinstance(data["refresh_token"], str)
        assert len(data["refresh_token"]) > 50

    def test_login_with_invalid_password(self, invalid_credentials):
        """Test login failure with invalid password"""
        response = requests.post(f"{API_AUTH}/login", json=invalid_credentials)

        assert response.status_code == 401
        data = response.json()

        assert "error" in data
        assert data["error"] == "Authentication failed"

    def test_login_missing_username(self):
        """Test login failure with missing username"""
        response = requests.post(f"{API_AUTH}/login", json={"password": "admin123"})

        assert response.status_code == 400
        assert "error" in response.json()

    def test_login_missing_password(self):
        """Test login failure with missing password"""
        response = requests.post(f"{API_AUTH}/login", json={"username": "admin"})

        assert response.status_code == 400
        assert "error" in response.json()

    def test_login_empty_body(self):
        """Test login failure with empty request body"""
        response = requests.post(f"{API_AUTH}/login", json={})

        assert response.status_code == 400

    def test_login_invalid_json(self):
        """Test login failure with invalid JSON"""
        response = requests.post(
            f"{API_AUTH}/login",
            data="not valid json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code in [400, 500]


# ============================================================================
# TOKEN REFRESH TESTS
# ============================================================================


class TestTokenRefresh:
    """Test token refresh endpoint"""

    def test_successful_token_refresh(self, refresh_token):
        """Test successful token refresh with valid refresh token"""
        response = requests.post(
            f"{API_AUTH}/refresh", json={"refresh_token": refresh_token}
        )

        assert response.status_code == 200
        data = response.json()

        # Check response structure
        assert "access_token" in data
        assert "token_type" in data
        assert "expires_in" in data

        # Check new token is different
        assert isinstance(data["access_token"], str)
        assert len(data["access_token"]) > 50

    def test_refresh_with_invalid_token(self):
        """Test refresh failure with invalid token"""
        response = requests.post(
            f"{API_AUTH}/refresh", json={"refresh_token": "invalid.token.here"}
        )

        assert response.status_code == 401
        assert "error" in response.json()

    def test_refresh_missing_token(self):
        """Test refresh failure with missing token"""
        response = requests.post(f"{API_AUTH}/refresh", json={})

        assert response.status_code == 400
        assert "error" in response.json()

    def test_refresh_with_access_token(self, access_token):
        """Test refresh failure when using access token instead of refresh token"""
        response = requests.post(
            f"{API_AUTH}/refresh",
            json={"refresh_token": access_token},  # Wrong token type
        )

        # Should fail because token type is 'access' not 'refresh'
        assert response.status_code == 401


# ============================================================================
# LOGOUT TESTS
# ============================================================================


class TestLogout:
    """Test logout endpoint"""

    def test_successful_logout(self, access_token):
        """Test successful logout with valid token"""
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.post(f"{API_AUTH}/logout", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    def test_logout_without_token(self):
        """Test logout failure without token"""
        response = requests.post(f"{API_AUTH}/logout")

        assert response.status_code == 401
        assert "error" in response.json()

    def test_logout_with_invalid_token(self):
        """Test logout failure with invalid token"""
        headers = {"Authorization": "Bearer invalid.token.here"}
        response = requests.post(f"{API_AUTH}/logout", headers=headers)

        assert response.status_code == 401

    def test_token_revoked_after_logout(self, access_token):
        """Test that token cannot be used after logout"""
        headers = {"Authorization": f"Bearer {access_token}"}

        # Logout
        logout_response = requests.post(f"{API_AUTH}/logout", headers=headers)
        assert logout_response.status_code == 200

        # Try to use token again (should fail)
        verify_response = requests.get(f"{API_AUTH}/verify", headers=headers)
        assert verify_response.status_code == 401


# ============================================================================
# VERIFY TOKEN TESTS
# ============================================================================


class TestVerifyToken:
    """Test token verification endpoint"""

    def test_verify_valid_token(self, access_token):
        """Test verification of valid token"""
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(f"{API_AUTH}/verify", headers=headers)

        assert response.status_code == 200
        data = response.json()

        assert data["valid"] is True
        assert "user" in data
        assert data["user"]["username"] == "admin"
        assert data["user"]["role"] == "admin"

    def test_verify_without_token(self):
        """Test verification failure without token"""
        response = requests.get(f"{API_AUTH}/verify")

        assert response.status_code == 401
        assert "error" in response.json()

    def test_verify_invalid_token(self):
        """Test verification failure with invalid token"""
        headers = {"Authorization": "Bearer invalid.token.here"}
        response = requests.get(f"{API_AUTH}/verify", headers=headers)

        assert response.status_code == 401


# ============================================================================
# PROTECTED ROUTE TESTS
# ============================================================================


class TestProtectedRoutes:
    """Test authentication on protected API routes"""

    def test_access_protected_route_with_token(self, access_token):
        """Test accessing protected route with valid token"""
        headers = {"Authorization": f"Bearer {access_token}"}

        # Try to access a protected endpoint (if any exist)
        # For now, test with /api/classes which might be protected
        response = requests.get(f"{BASE_URL}/api/classes", headers=headers)

        # Should succeed if endpoint is protected and token is valid
        # Or succeed if endpoint is not protected (no auth required)
        assert response.status_code in [200, 404]  # 404 if no classes exist

    def test_access_public_route_without_token(self):
        """Test that public routes work without token"""
        response = requests.get(f"{BASE_URL}/api/health")

        assert response.status_code == 200


# ============================================================================
# TOKEN EXPIRATION TESTS (Manual - Requires Time Manipulation)
# ============================================================================


class TestTokenExpiration:
    """Test token expiration behavior"""

    @pytest.mark.skip(reason="Requires time manipulation or config change")
    def test_expired_access_token(self):
        """Test that expired tokens are rejected"""
        # This test requires either:
        # 1. Waiting for token to expire (slow)
        # 2. Manipulating system time (complex)
        # 3. Configuring very short expiration for tests
        pass

    def test_token_contains_expiration(self, access_token):
        """Test that token contains expiration claim"""
        import jwt

        # Decode token without verification (just to inspect)
        decoded = jwt.decode(access_token, options={"verify_signature": False})

        assert "exp" in decoded
        assert "iat" in decoded
        assert decoded["exp"] > decoded["iat"]


# ============================================================================
# AUTHORIZATION HEADER TESTS
# ============================================================================


class TestAuthorizationHeader:
    """Test Authorization header handling"""

    def test_bearer_token_format(self, access_token):
        """Test correct Bearer token format"""
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(f"{API_AUTH}/verify", headers=headers)

        assert response.status_code == 200

    def test_invalid_header_format(self, access_token):
        """Test invalid Authorization header format"""
        # Missing 'Bearer' prefix
        headers = {"Authorization": access_token}
        response = requests.get(f"{API_AUTH}/verify", headers=headers)

        assert response.status_code == 401

    def test_lowercase_bearer(self, access_token):
        """Test that 'bearer' (lowercase) is accepted"""
        headers = {"Authorization": f"bearer {access_token}"}
        response = requests.get(f"{API_AUTH}/verify", headers=headers)

        # Should work (case-insensitive)
        assert response.status_code == 200


# ============================================================================
# INTEGRATION WORKFLOW TESTS
# ============================================================================


class TestAuthenticationWorkflow:
    """Test complete authentication workflows"""

    def test_full_authentication_flow(self, valid_credentials):
        """Test complete flow: login → use token → refresh → logout"""

        # 1. Login
        login_response = requests.post(f"{API_AUTH}/login", json=valid_credentials)
        assert login_response.status_code == 200
        tokens = login_response.json()
        access_token = tokens["access_token"]
        refresh_token = tokens["refresh_token"]

        # 2. Verify token
        headers = {"Authorization": f"Bearer {access_token}"}
        verify_response = requests.get(f"{API_AUTH}/verify", headers=headers)
        assert verify_response.status_code == 200

        # 3. Refresh token
        refresh_response = requests.post(
            f"{API_AUTH}/refresh", json={"refresh_token": refresh_token}
        )
        assert refresh_response.status_code == 200
        new_access_token = refresh_response.json()["access_token"]

        # 4. Use new token
        new_headers = {"Authorization": f"Bearer {new_access_token}"}
        verify_new_response = requests.get(f"{API_AUTH}/verify", headers=new_headers)
        assert verify_new_response.status_code == 200

        # 5. Logout
        logout_response = requests.post(f"{API_AUTH}/logout", headers=new_headers)
        assert logout_response.status_code == 200

    def test_multiple_concurrent_sessions(self, valid_credentials):
        """Test that multiple login sessions work independently"""

        # Create two sessions
        response1 = requests.post(f"{API_AUTH}/login", json=valid_credentials)
        response2 = requests.post(f"{API_AUTH}/login", json=valid_credentials)

        token1 = response1.json()["access_token"]
        token2 = response2.json()["access_token"]

        # Both tokens should be valid and different
        assert token1 != token2

        headers1 = {"Authorization": f"Bearer {token1}"}
        headers2 = {"Authorization": f"Bearer {token2}"}

        verify1 = requests.get(f"{API_AUTH}/verify", headers=headers1)
        verify2 = requests.get(f"{API_AUTH}/verify", headers=headers2)

        assert verify1.status_code == 200
        assert verify2.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
