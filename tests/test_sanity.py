"""
Sanity Tests
============
Test base per verificare che l'ambiente di test funzioni correttamente.
"""

import pytest


@pytest.mark.unit
def test_sanity():
    """Test di base per verificare che pytest funzioni."""
    assert True


@pytest.mark.unit
def test_python_version():
    """Verifica versione Python >= 3.9."""
    import sys
    assert sys.version_info >= (3, 9), "Python 3.9+ richiesto"


@pytest.mark.unit
def test_imports():
    """Verifica che i moduli principali siano importabili."""
    # Flask
    import flask
    assert hasattr(flask, 'Flask')

    # SQLAlchemy
    import flask_sqlalchemy
    assert hasattr(flask_sqlalchemy, 'SQLAlchemy')

    # Pandas
    import pandas
    assert hasattr(pandas, 'DataFrame')

    # NumPy
    import numpy
    assert hasattr(numpy, 'array')


@pytest.mark.unit
def test_app_imports():
    """Verifica che i moduli dell'app siano importabili."""
    # Models
    from models import db, User, FileAnagrafica
    assert db is not None
    assert User is not None

    # Config
    from config import Config, DevelopmentConfig, ProductionConfig
    assert Config is not None

    # App
    from app import create_app
    assert create_app is not None


@pytest.mark.unit
def test_fixtures_available(app, client, db):
    """Verifica che le fixtures base siano disponibili."""
    assert app is not None
    assert client is not None
    assert db is not None


@pytest.mark.integration
def test_app_creation(app):
    """Verifica che l'app si crei correttamente."""
    assert app is not None
    assert app.config['TESTING'] is True
    assert app.config['SECRET_KEY'] == 'test-secret-key-do-not-use-in-production'


@pytest.mark.integration
def test_database_connection(db):
    """Verifica connessione al database di test."""
    # Il database dovrebbe essere SQLite in-memory
    assert 'sqlite:///:memory:' in str(db.engine.url)


@pytest.mark.integration
def test_test_users_created(db):
    """Verifica che gli utenti di test siano stati creati."""
    from models import User

    admin = User.query.filter_by(username='admin').first()
    user = User.query.filter_by(username='user').first()

    assert admin is not None
    assert admin.role == 'admin'
    assert admin.check_password('admin123') is True

    assert user is not None
    assert user.role == 'user'
    assert user.check_password('user123') is True
