"""
Test Models - User, Rottura, Ordine, Anagrafica
"""

import pytest
from models import User, Rottura, OrdineAcquisto, AnagraficaFile
from datetime import datetime, date


class TestUserModel:
    """Test User model"""

    def test_create_user(self, db):
        """Test creazione utente"""
        user = User(username='testuser', email='test@example.com')
        user.set_password('password123')

        db.session.add(user)
        db.session.commit()

        assert user.id is not None
        assert user.username == 'testuser'
        assert user.email == 'test@example.com'
        assert user.check_password('password123')
        assert not user.check_password('wrongpassword')

    def test_user_is_admin(self, db):
        """Test verifica ruolo admin"""
        admin = User(username='admin', email='admin@test.com', role='admin')
        user = User(username='user', email='user@test.com', role='user')

        assert admin.is_admin()
        assert not user.is_admin()

    def test_user_get_by_username(self, db, regular_user):
        """Test recupero utente per username"""
        found = User.get_by_username(regular_user.username)
        assert found is not None
        assert found.id == regular_user.id

    def test_user_to_dict(self, db, regular_user):
        """Test conversione user a dizionario"""
        data = regular_user.to_dict()
        assert 'id' in data
        assert 'username' in data
        assert 'password_hash' not in data  # Password non deve essere esposta


class TestRotturaModel:
    """Test Rottura model"""

    def test_create_rottura(self, db):
        """Test creazione rottura"""
        rottura = Rottura(
            anno=2024,
            filename='test.xlsx',
            filepath='/path/to/test.xlsx',
            esito='Da processare'
        )

        db.session.add(rottura)
        db.session.commit()

        assert rottura.id is not None
        assert rottura.anno == 2024
        assert rottura.esito == 'Da processare'

    def test_mark_as_processed(self, db):
        """Test mark as processed"""
        rottura = Rottura(
            anno=2024,
            filename='test.xlsx',
            filepath='/path/to/test2.xlsx'
        )
        db.session.add(rottura)
        db.session.commit()

        rottura.mark_as_processed()
        db.session.commit()

        assert rottura.esito == 'Processato'
        assert rottura.data_elaborazione is not None

    def test_mark_as_error(self, db):
        """Test mark as error"""
        rottura = Rottura(
            anno=2024,
            filename='test.xlsx',
            filepath='/path/to/test3.xlsx'
        )
        db.session.add(rottura)
        db.session.commit()

        rottura.mark_as_error("Test error")
        db.session.commit()

        assert rottura.esito == 'Errore'
        assert 'Test error' in rottura.note


class TestOrdineAcquistoModel:
    """Test OrdineAcquisto model"""

    def test_create_ordine(self, db):
        """Test creazione ordine"""
        ordine = OrdineAcquisto(
            anno=2024,
            filename='ordine.pdf',
            filepath='/path/to/ordine.pdf'
        )

        db.session.add(ordine)
        db.session.commit()

        assert ordine.id is not None
        assert ordine.filename == 'ordine.pdf'


class TestAnagraficaFileModel:
    """Test AnagraficaFile model"""

    def test_create_anagrafica(self, db):
        """Test creazione anagrafica"""
        anagrafica = AnagraficaFile(
            anno=2024,
            marca='TestBrand',
            filename='anagrafica.xlsx',
            filepath='/path/to/anagrafica.xlsx'
        )

        db.session.add(anagrafica)
        db.session.commit()

        assert anagrafica.id is not None
        assert anagrafica.marca == 'TestBrand'

    def test_get_marche_list(self, db):
        """Test recupero lista marche"""
        AnagraficaFile(
            anno=2024,
            marca='Brand1',
            filename='test1.xlsx',
            filepath='/path/to/test1.xlsx'
        )
        AnagraficaFile(
            anno=2024,
            marca='Brand2',
            filename='test2.xlsx',
            filepath='/path/to/test2.xlsx'
        )
        db.session.commit()

        marche = AnagraficaFile.get_marche_list()
        assert len(marche) == 2
        assert 'Brand1' in marche
        assert 'Brand2' in marche
