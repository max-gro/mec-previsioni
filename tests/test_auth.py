"""
Test Authentication Routes
"""

import pytest
from flask import url_for


class TestLogin:
    """Test login functionality"""

    def test_login_page_loads(self, client):
        """Test che la pagina di login carichi correttamente"""
        response = client.get('/login')
        assert response.status_code == 200
        assert b'login' in response.data.lower()

    def test_login_success(self, client, regular_user):
        """Test login con credenziali corrette"""
        response = client.post('/login', data={
            'username': regular_user.username,
            'password': 'testpassword123'
        }, follow_redirects=True)

        assert response.status_code == 200
        # Dopo login redirect a index
        assert b'dashboard' in response.data.lower() or b'previsioni' in response.data.lower()

    def test_login_invalid_credentials(self, client, regular_user):
        """Test login con password errata"""
        response = client.post('/login', data={
            'username': regular_user.username,
            'password': 'wrongpassword'
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b'non validi' in response.data.lower() or b'invalid' in response.data.lower()

    def test_login_rate_limit(self, client, regular_user):
        """Test rate limiting sul login"""
        # Effettua 6 tentativi di login (limit è 5/minute)
        for i in range(6):
            response = client.post('/login', data={
                'username': regular_user.username,
                'password': 'wrongpassword'
            })

        # Il 6° tentativo dovrebbe essere bloccato
        assert response.status_code == 429  # Too Many Requests


class TestLogout:
    """Test logout functionality"""

    def test_logout(self, authenticated_client):
        """Test logout"""
        response = authenticated_client.get('/logout', follow_redirects=True)
        assert response.status_code == 200
        # Redirect a login page
        assert b'login' in response.data.lower()


class TestProtectedRoutes:
    """Test protezione routes autenticate"""

    def test_index_requires_login(self, client):
        """Test che index richieda login"""
        response = client.get('/', follow_redirects=False)
        assert response.status_code == 302  # Redirect a login

    def test_index_accessible_when_authenticated(self, authenticated_client):
        """Test che index sia accessibile dopo login"""
        response = authenticated_client.get('/')
        assert response.status_code == 200
