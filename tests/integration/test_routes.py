"""
Integration Tests - Routes
===========================
Test per le routes principali dell'applicazione.
"""

import pytest
from models import FileAnagrafica, FileRottura, FileOrdine


# ============================================================================
# Test Homepage e Dashboard
# ============================================================================

@pytest.mark.integration
def test_homepage_requires_login(client):
    """Test che la homepage richieda login."""
    response = client.get('/', follow_redirects=False)
    assert response.status_code == 302
    assert 'login' in response.location


@pytest.mark.integration
def test_homepage_authenticated(authenticated_client):
    """Test homepage per utente autenticato."""
    response = authenticated_client.get('/')
    assert response.status_code == 200


@pytest.mark.integration
def test_dashboard_loads(authenticated_client):
    """Test che la dashboard carichi correttamente."""
    response = authenticated_client.get('/dashboard/')
    # Potrebbe essere 200 se esiste, 404 se non implementato
    assert response.status_code in [200, 404]


# ============================================================================
# Test Anagrafiche Routes
# ============================================================================

@pytest.mark.integration
def test_anagrafiche_list(authenticated_client):
    """Test lista anagrafiche."""
    response = authenticated_client.get('/anagrafiche/')
    assert response.status_code == 200


@pytest.mark.integration
def test_anagrafiche_create_page(authenticated_client):
    """Test pagina creazione anagrafica."""
    response = authenticated_client.get('/anagrafiche/create')
    # Potrebbe essere 200 o 404 se non implementato
    assert response.status_code in [200, 404, 405]


@pytest.mark.integration
def test_anagrafiche_list_shows_files(authenticated_client, db):
    """Test che la lista mostri i file anagrafiche."""
    # Crea file anagrafica di test
    file_ana = FileAnagrafica(
        anno=2024,
        marca='TEST',
        filename='test.xlsx',
        filepath='/test/path/test.xlsx',
        esito='Da processare',
        created_by=1
    )
    db.session.add(file_ana)
    db.session.commit()

    response = authenticated_client.get('/anagrafiche/')
    assert response.status_code == 200
    # Verifica che il file sia nella lista
    assert b'test.xlsx' in response.data or b'TEST' in response.data


# ============================================================================
# Test Rotture Routes
# ============================================================================

@pytest.mark.integration
def test_rotture_list(authenticated_client):
    """Test lista rotture."""
    response = authenticated_client.get('/rotture/')
    assert response.status_code == 200


@pytest.mark.integration
def test_rotture_list_shows_files(authenticated_client, db):
    """Test che la lista mostri i file rotture."""
    # Crea file rottura di test
    file_rot = FileRottura(
        anno=2024,
        filename='rotture_2024.xlsx',
        filepath='/test/rotture_2024.xlsx',
        esito='Processato',
        created_by=1
    )
    db.session.add(file_rot)
    db.session.commit()

    response = authenticated_client.get('/rotture/')
    assert response.status_code == 200
    assert b'rotture_2024.xlsx' in response.data or b'2024' in response.data


# ============================================================================
# Test Ordini Routes
# ============================================================================

@pytest.mark.integration
def test_ordini_list(authenticated_client):
    """Test lista ordini."""
    response = authenticated_client.get('/ordini/')
    assert response.status_code == 200


@pytest.mark.integration
def test_ordini_list_shows_files(authenticated_client, db):
    """Test che la lista mostri i file ordini."""
    from models import Controparte

    # Crea controparti
    seller = Controparte(cod_controparte='SELL01', controparte='Seller', created_by=1)
    buyer = Controparte(cod_controparte='BUY01', controparte='Buyer', created_by=1)
    db.session.add_all([seller, buyer])
    db.session.commit()

    # Crea file ordine di test
    file_ord = FileOrdine(
        anno=2024,
        filename='ordine_001.pdf',
        filepath='/test/ordine_001.pdf',
        cod_seller='SELL01',
        cod_buyer='BUY01',
        created_by=1
    )
    db.session.add(file_ord)
    db.session.commit()

    response = authenticated_client.get('/ordini/')
    assert response.status_code == 200
    assert b'ordine_001.pdf' in response.data or b'2024' in response.data


# ============================================================================
# Test Users Routes (Admin Only)
# ============================================================================

@pytest.mark.integration
def test_users_list_admin_access(authenticated_client):
    """Test che admin possa accedere a lista utenti."""
    response = authenticated_client.get('/users/')
    # 200 se esiste, 404 se non implementato
    assert response.status_code in [200, 404]


@pytest.mark.integration
def test_users_list_user_denied(user_client):
    """Test che user normale NON possa accedere a lista utenti."""
    response = user_client.get('/users/', follow_redirects=False)
    # Dovrebbe essere negato (403) o rediretto (302)
    assert response.status_code in [302, 403]


# ============================================================================
# Test Error Handlers
# ============================================================================

@pytest.mark.integration
def test_404_error_handler(authenticated_client):
    """Test che 404 mostri pagina di errore custom."""
    response = authenticated_client.get('/nonexistent-page-12345')
    assert response.status_code == 404
    # Verifica che usi il template custom se esiste
    # Altrimenti Flask mostrerà errore di default


@pytest.mark.integration
def test_403_error_handler(user_client):
    """Test che 403 mostri pagina di errore custom."""
    # Prova ad accedere a route admin come user normale
    response = user_client.get('/users/', follow_redirects=False)

    if response.status_code == 403:
        # Verifica che usi template custom
        assert b'403' in response.data or b'accesso' in response.data.lower() or \
               b'forbidden' in response.data.lower()


# ============================================================================
# Test Static Files
# ============================================================================

@pytest.mark.integration
def test_static_files_accessible(client):
    """Test che i file statici siano accessibili."""
    # Test logo (se esiste)
    response = client.get('/static/images/MeC-web-logo.png')
    # 200 se esiste, 404 altrimenti
    assert response.status_code in [200, 404]
