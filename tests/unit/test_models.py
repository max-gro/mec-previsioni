"""
Unit Tests - Models
===================
Test per i modelli SQLAlchemy.
"""

import pytest
from datetime import datetime, timezone

from models import (
    User, FileAnagrafica, FileRottura, FileOrdine,
    Modello, Componente, Controparte, Rottura,
    UtenteRottura, Rivenditore
)


# ============================================================================
# Test User Model
# ============================================================================

@pytest.mark.unit
def test_user_creation(db):
    """Test creazione utente."""
    user = User(
        username='testuser',
        email='test@example.com',
        role='user',
        active=True,
        created_by=0
    )
    user.set_password('password123')

    db.session.add(user)
    db.session.commit()

    assert user.id is not None
    assert user.username == 'testuser'
    assert user.email == 'test@example.com'
    assert user.role == 'user'
    assert user.active is True
    assert user.created_at is not None


@pytest.mark.unit
def test_user_password_hashing(db):
    """Test hashing password."""
    user = User(username='test', email='test@test.com', created_by=0)
    password = 'mypassword123'
    user.set_password(password)

    # Password dovrebbe essere hashata
    assert user.password_hash != password
    assert len(user.password_hash) > 0

    # Check password dovrebbe funzionare
    assert user.check_password(password) is True
    assert user.check_password('wrongpassword') is False


@pytest.mark.unit
def test_user_is_admin(db):
    """Test metodo is_admin()."""
    admin = User(username='admin', email='admin@test.com', role='admin', created_by=0)
    user = User(username='user', email='user@test.com', role='user', created_by=0)

    assert admin.is_admin() is True
    assert user.is_admin() is False


@pytest.mark.unit
def test_user_unique_constraints(db):
    """Test constraint di unicità su username e email."""
    user1 = User(username='test', email='test@test.com', created_by=0)
    user1.set_password('pass')
    db.session.add(user1)
    db.session.commit()

    # Stesso username dovrebbe fallire
    user2 = User(username='test', email='different@test.com', created_by=0)
    user2.set_password('pass')
    db.session.add(user2)

    with pytest.raises(Exception):  # IntegrityError
        db.session.commit()

    db.session.rollback()

    # Stessa email dovrebbe fallire
    user3 = User(username='different', email='test@test.com', created_by=0)
    user3.set_password('pass')
    db.session.add(user3)

    with pytest.raises(Exception):  # IntegrityError
        db.session.commit()


# ============================================================================
# Test FileAnagrafica Model
# ============================================================================

@pytest.mark.unit
def test_file_anagrafica_creation(db):
    """Test creazione FileAnagrafica."""
    file_ana = FileAnagrafica(
        anno=2024,
        marca='TESTBRAND',
        filename='test.xlsx',
        filepath='/test/path/test.xlsx',
        esito='Da processare',
        created_by=1
    )

    db.session.add(file_ana)
    db.session.commit()

    assert file_ana.id is not None
    assert file_ana.anno == 2024
    assert file_ana.marca == 'TESTBRAND'
    assert file_ana.filename == 'test.xlsx'
    assert file_ana.esito == 'Da processare'
    assert file_ana.data_acquisizione is not None


@pytest.mark.unit
def test_file_anagrafica_defaults(db):
    """Test valori di default FileAnagrafica."""
    file_ana = FileAnagrafica(
        anno=2024,
        marca='TEST',
        filename='test.xlsx',
        filepath='/path',
        created_by=1
    )

    db.session.add(file_ana)
    db.session.commit()

    # Verifica defaults
    assert file_ana.esito == 'Da processare'
    assert file_ana.data_acquisizione is not None
    assert file_ana.data_elaborazione is None
    assert file_ana.created_at is not None


# ============================================================================
# Test FileRottura Model
# ============================================================================

@pytest.mark.unit
def test_file_rottura_creation(db):
    """Test creazione FileRottura."""
    file_rot = FileRottura(
        anno=2024,
        filename='rotture_2024.xlsx',
        filepath='/test/rotture_2024.xlsx',
        esito='Processato',
        created_by=1
    )

    db.session.add(file_rot)
    db.session.commit()

    assert file_rot.id is not None
    assert file_rot.anno == 2024
    assert file_rot.esito == 'Processato'


# ============================================================================
# Test FileOrdine Model
# ============================================================================

@pytest.mark.unit
def test_file_ordine_creation(db):
    """Test creazione FileOrdine."""
    # Prima crea controparti
    seller = Controparte(
        cod_controparte='SELL01',
        controparte='Seller Company',
        created_by=1
    )
    buyer = Controparte(
        cod_controparte='BUY01',
        controparte='Buyer Company',
        created_by=1
    )
    db.session.add_all([seller, buyer])
    db.session.commit()

    # Poi crea file ordine
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

    assert file_ord.id is not None
    assert file_ord.seller.controparte == 'Seller Company'
    assert file_ord.buyer.controparte == 'Buyer Company'


# ============================================================================
# Test Modello
# ============================================================================

@pytest.mark.unit
def test_modello_creation(db):
    """Test creazione Modello."""
    modello = Modello(
        cod_modello='MOD001',
        cod_modello_norm='MOD001',
        nome_modello='Test Model',
        marca='TESTBRAND',
        created_by=1
    )

    db.session.add(modello)
    db.session.commit()

    assert modello.cod_modello == 'MOD001'
    assert modello.nome_modello == 'Test Model'
    assert modello.created_at is not None


@pytest.mark.unit
def test_modello_unique_constraint(db):
    """Test constraint unicità cod_modello_norm."""
    modello1 = Modello(
        cod_modello='MOD001',
        cod_modello_norm='MOD_NORM',
        created_by=1
    )
    db.session.add(modello1)
    db.session.commit()

    # Stesso cod_modello_norm dovrebbe fallire
    modello2 = Modello(
        cod_modello='MOD002',
        cod_modello_norm='MOD_NORM',
        created_by=1
    )
    db.session.add(modello2)

    with pytest.raises(Exception):
        db.session.commit()


# ============================================================================
# Test Componente
# ============================================================================

@pytest.mark.unit
def test_componente_creation(db):
    """Test creazione Componente."""
    comp = Componente(
        cod_componente='COMP001',
        cod_componente_norm='COMP001',
        part_name_it='Componente Test',
        unit_price_eur=10.50,
        created_by=1
    )

    db.session.add(comp)
    db.session.commit()

    assert comp.cod_componente == 'COMP001'
    assert comp.part_name_it == 'Componente Test'
    assert float(comp.unit_price_eur) == 10.50


# ============================================================================
# Test Relationships
# ============================================================================

@pytest.mark.unit
def test_user_file_relationship(db):
    """Test relationship User -> FileAnagrafica."""
    user = User(username='creator', email='creator@test.com', created_by=0)
    user.set_password('pass')
    db.session.add(user)
    db.session.commit()

    file_ana = FileAnagrafica(
        anno=2024,
        marca='TEST',
        filename='test.xlsx',
        filepath='/path',
        created_by=user.id
    )
    db.session.add(file_ana)
    db.session.commit()

    # Verifica relationship
    assert file_ana.creator.username == 'creator'
    assert user.file_anagrafiche_created[0].filename == 'test.xlsx'


@pytest.mark.unit
def test_modello_componente_relationship(db):
    """Test relationship Modello -> Componente (BOM)."""
    from models import ModelloComponente

    # Crea modello e componente
    modello = Modello(
        cod_modello='MOD001',
        cod_modello_norm='MOD001',
        created_by=1
    )
    componente = Componente(
        cod_componente='COMP001',
        cod_componente_norm='COMP001',
        created_by=1
    )
    db.session.add_all([modello, componente])
    db.session.commit()

    # Crea file anagrafica (richiesto da FK)
    file_ana = FileAnagrafica(
        anno=2024,
        marca='TEST',
        filename='test.xlsx',
        filepath='/path',
        created_by=1
    )
    db.session.add(file_ana)
    db.session.commit()

    # Crea relazione BOM
    bom = ModelloComponente(
        cod_modello_componente='MOD001|COMP001',
        id_file_anagrafiche=file_ana.id,
        cod_modello='MOD001',
        cod_componente='COMP001',
        qta=2,
        created_by=1
    )
    db.session.add(bom)
    db.session.commit()

    # Verifica relationship
    assert len(modello.componenti_bom) == 1
    assert modello.componenti_bom[0].cod_componente == 'COMP001'
    assert modello.componenti_bom[0].qta == 2
