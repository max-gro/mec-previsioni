"""
Pytest Configuration and Fixtures
==================================
Questo file contiene fixtures comuni per tutti i test.

Fixtures disponibili:
- app: Flask app configurata per testing
- client: Flask test client
- db: Database per testing
- runner: Flask CLI runner
- auth: Helper per autenticazione nei test
"""

import pytest
import os
import tempfile
from datetime import datetime, timezone

from app import create_app
from models import db as _db, User
from config import Config


class TestConfig(Config):
    """Configurazione per ambiente di test."""
    TESTING = True
    DEBUG = False

    # Database in-memory per test veloci
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

    # Secret key per test
    SECRET_KEY = 'test-secret-key-do-not-use-in-production'

    # Disable CSRF per semplificare test
    WTF_CSRF_ENABLED = False

    # Server name per url_for nei test
    SERVER_NAME = 'localhost'


@pytest.fixture(scope='function')
def app():
    """
    Crea e configura una nuova app per ogni test.

    Yields:
        Flask app configurata per testing
    """
    app = create_app(TestConfig)

    # Setup app context
    with app.app_context():
        _db.create_all()

        # Crea utenti di test
        admin = User(
            username='admin',
            email='admin@test.com',
            role='admin',
            active=True,
            created_by=0
        )
        admin.set_password('admin123')
        _db.session.add(admin)

        user = User(
            username='user',
            email='user@test.com',
            role='user',
            active=True,
            created_by=0
        )
        user.set_password('user123')
        _db.session.add(user)

        _db.session.commit()

    yield app

    # Cleanup
    with app.app_context():
        _db.session.remove()
        _db.drop_all()


@pytest.fixture(scope='function')
def client(app):
    """
    Crea un test client per l'app.

    Args:
        app: Flask app fixture

    Yields:
        Flask test client
    """
    return app.test_client()


@pytest.fixture(scope='function')
def runner(app):
    """
    Crea un CLI runner per testare comandi Flask.

    Args:
        app: Flask app fixture

    Yields:
        Flask CLI runner
    """
    return app.test_cli_runner()


@pytest.fixture(scope='function')
def db(app):
    """
    Fornisce accesso al database per i test.

    Args:
        app: Flask app fixture

    Yields:
        SQLAlchemy database instance
    """
    with app.app_context():
        yield _db


class AuthActions:
    """Helper class per azioni di autenticazione nei test."""

    def __init__(self, client):
        self._client = client

    def login(self, username='admin', password='admin123'):
        """
        Esegue login.

        Args:
            username: Username (default: 'admin')
            password: Password (default: 'admin123')

        Returns:
            Response del login
        """
        return self._client.post(
            '/login',
            data={'username': username, 'password': password},
            follow_redirects=True
        )

    def logout(self):
        """
        Esegue logout.

        Returns:
            Response del logout
        """
        return self._client.get('/logout', follow_redirects=True)


@pytest.fixture
def auth(client):
    """
    Fornisce helper per autenticazione nei test.

    Args:
        client: Flask test client fixture

    Returns:
        AuthActions instance

    Example:
        def test_login(auth):
            response = auth.login()
            assert response.status_code == 200
    """
    return AuthActions(client)


@pytest.fixture
def authenticated_client(client, auth):
    """
    Client già autenticato come admin.

    Args:
        client: Flask test client fixture
        auth: Auth helper fixture

    Yields:
        Authenticated Flask test client
    """
    auth.login()
    yield client
    auth.logout()


@pytest.fixture
def user_client(client, auth):
    """
    Client autenticato come user normale (non admin).

    Args:
        client: Flask test client fixture
        auth: Auth helper fixture

    Yields:
        Authenticated Flask test client (user role)
    """
    auth.login(username='user', password='user123')
    yield client
    auth.logout()


# ============================================================================
# Markers per categorizzare test
# ============================================================================

def pytest_configure(config):
    """Configura markers personalizzati."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
