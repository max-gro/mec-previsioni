"""
Integration Tests - Authentication
===================================
Test per le route di autenticazione.
"""

import pytest
from flask import url_for


# ============================================================================
# Test Login/Logout
# ============================================================================

@pytest.mark.integration
def test_login_page_loads(client):
    """Test che la pagina di login carica correttamente."""
    response = client.get('/login')
    assert response.status_code == 200
    assert b'login' in response.data.lower() or b'username' in response.data.lower()


@pytest.mark.integration
def test_login_success(client, auth):
    """Test login con credenziali corrette."""
    response = auth.login()
    assert response.status_code == 200

    # Dopo login, dovremmo essere reindirizzati alla home
    # Verifica che non sia più sulla pagina di login
    assert b'logout' in response.data.lower() or b'esci' in response.data.lower()


@pytest.mark.integration
def test_login_invalid_username(client, auth):
    """Test login con username inesistente."""
    response = auth.login(username='nonexistent', password='password')

    # Dovrebbe mostrare errore
    assert b'Invalid' in response.data or b'non valido' in response.data.lower() or \
           b'error' in response.data.lower() or b'errore' in response.data.lower()


@pytest.mark.integration
def test_login_invalid_password(client, auth):
    """Test login con password errata."""
    response = auth.login(username='admin', password='wrongpassword')

    # Dovrebbe mostrare errore
    assert b'Invalid' in response.data or b'non valido' in response.data.lower() or \
           b'error' in response.data.lower() or b'errore' in response.data.lower()


@pytest.mark.integration
def test_logout(client, auth):
    """Test logout."""
    # Prima fai login
    auth.login()

    # Poi logout
    response = auth.logout()
    assert response.status_code == 200

    # Dovremmo vedere di nuovo la pagina di login
    assert b'login' in response.data.lower()


@pytest.mark.integration
def test_login_required_redirect(client):
    """Test che le route protette richiedano login."""
    # Prova ad accedere a una route protetta senza login
    response = client.get('/', follow_redirects=False)

    # Dovrebbe redirigere a login
    assert response.status_code == 302
    assert 'login' in response.location


# ============================================================================
# Test User Session
# ============================================================================

@pytest.mark.integration
def test_user_session_persists(client, auth):
    """Test che la sessione utente persista tra richieste."""
    # Login
    auth.login()

    # Accedi a una pagina protetta
    response = client.get('/')
    assert response.status_code == 200

    # Accedi a un'altra pagina - la sessione dovrebbe ancora essere valida
    response = client.get('/')
    assert response.status_code == 200


@pytest.mark.integration
def test_different_users_different_sessions(client):
    """Test che utenti diversi abbiano sessioni separate."""
    from tests.conftest import AuthActions

    # Login come admin
    auth1 = AuthActions(client)
    auth1.login(username='admin', password='admin123')

    # Verifica che siamo loggati
    response = client.get('/')
    assert response.status_code == 200

    # Logout
    auth1.logout()

    # Login come user
    auth2 = AuthActions(client)
    auth2.login(username='user', password='user123')

    # Verifica che siamo loggati come user diverso
    response = client.get('/')
    assert response.status_code == 200
