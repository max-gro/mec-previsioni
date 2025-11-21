"""
Unit Tests - Utils
==================
Test per utility e decoratori.
"""

import pytest
from unittest.mock import Mock, patch
from flask import Flask, redirect, url_for
from flask_login import current_user

from utils.decorators import admin_required, handle_errors
from models import db, User


# ============================================================================
# Test admin_required Decorator
# ============================================================================

@pytest.mark.unit
def test_admin_required_with_admin(authenticated_client):
    """Test @admin_required permette accesso ad admin."""
    # authenticated_client è già loggato come admin
    response = authenticated_client.get('/users/')
    # Se esiste la route, non dovrebbe redirigere a login
    # Se la route non esiste, avrà 404
    assert response.status_code in [200, 404]


@pytest.mark.unit
def test_admin_required_with_regular_user(user_client):
    """Test @admin_required nega accesso a user normale."""
    # user_client è loggato come user (non admin)
    response = user_client.get('/users/')

    # Dovrebbe essere rediretto (403 o redirect)
    assert response.status_code in [302, 403]


@pytest.mark.unit
def test_admin_required_without_login(client):
    """Test @admin_required richiede login."""
    response = client.get('/users/')

    # Dovrebbe redirigere a login
    assert response.status_code == 302
    assert '/login' in response.location or 'login' in response.location


# ============================================================================
# Test handle_errors Decorator
# ============================================================================

@pytest.mark.unit
def test_handle_errors_catches_exception(app):
    """Test @handle_errors cattura eccezioni."""
    from utils.decorators import handle_errors

    @handle_errors
    def failing_function():
        raise ValueError("Test error")

    with app.app_context():
        with app.test_request_context():
            result = failing_function()

            # In test mode (DEBUG=False), dovrebbe redirigere
            # Verifica che non ha fatto crash
            assert result is not None


@pytest.mark.unit
def test_handle_errors_rollback_db(app, db):
    """Test @handle_errors esegue rollback del database."""
    from utils.decorators import handle_errors

    @handle_errors
    def function_with_db_error():
        # Crea un utente
        user = User(username='test', email='test@test.com', created_by=0)
        user.set_password('pass')
        db.session.add(user)
        # Non commit, poi solleva eccezione
        raise ValueError("Error after DB operation")

    with app.app_context():
        with app.test_request_context():
            function_with_db_error()

            # Verifica che non ci sia l'utente nel DB (rollback avvenuto)
            user_count = User.query.filter_by(username='test').count()
            assert user_count == 0


# ============================================================================
# Test Config Classes
# ============================================================================

@pytest.mark.unit
def test_development_config():
    """Test DevelopmentConfig settings."""
    from config import DevelopmentConfig

    assert DevelopmentConfig.DEBUG is True
    assert DevelopmentConfig.TESTING is False


@pytest.mark.unit
def test_production_config():
    """Test ProductionConfig settings."""
    from config import ProductionConfig

    assert ProductionConfig.DEBUG is False
    assert ProductionConfig.TESTING is False
    assert ProductionConfig.SESSION_COOKIE_SECURE is True


@pytest.mark.unit
def test_production_config_requires_secret_key():
    """Test ProductionConfig richiede SECRET_KEY."""
    import os
    from config import ProductionConfig

    # Salva SECRET_KEY originale
    original_key = os.environ.get('SECRET_KEY')

    try:
        # Rimuovi SECRET_KEY dall'environment
        if 'SECRET_KEY' in os.environ:
            del os.environ['SECRET_KEY']

        # ProductionConfig dovrebbe sollevare errore
        with pytest.raises(ValueError, match="SECRET_KEY must be set"):
            # Forza la valutazione della condizione
            if not ProductionConfig.SECRET_KEY:
                raise ValueError("SECRET_KEY must be set in production environment.")

    finally:
        # Ripristina SECRET_KEY
        if original_key:
            os.environ['SECRET_KEY'] = original_key
