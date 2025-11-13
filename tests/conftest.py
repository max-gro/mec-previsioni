"""
Pytest Configuration and Fixtures
"""

import pytest
from app import create_app
from extensions import db as _db
from models import User


@pytest.fixture(scope='session')
def app():
    """
    Crea una Flask app per testing

    Returns:
        Flask app configurata per testing
    """
    app = create_app('testing')

    with app.app_context():
        yield app


@pytest.fixture(scope='function')
def db(app):
    """
    Crea un database pulito per ogni test

    Args:
        app: Flask app fixture

    Yields:
        Database instance
    """
    with app.app_context():
        _db.create_all()
        yield _db
        _db.session.remove()
        _db.drop_all()


@pytest.fixture(scope='function')
def client(app, db):
    """
    Crea un test client Flask

    Args:
        app: Flask app fixture
        db: Database fixture

    Returns:
        Flask test client
    """
    return app.test_client()


@pytest.fixture(scope='function')
def admin_user(db):
    """
    Crea un utente admin per testing

    Args:
        db: Database fixture

    Returns:
        User object (admin)
    """
    user = User(
        username='admin_test',
        email='admin@test.com',
        role='admin',
        active=True
    )
    user.set_password('testpassword123')
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture(scope='function')
def regular_user(db):
    """
    Crea un utente normale per testing

    Args:
        db: Database fixture

    Returns:
        User object (user role)
    """
    user = User(
        username='user_test',
        email='user@test.com',
        role='user',
        active=True
    )
    user.set_password('testpassword123')
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture(scope='function')
def authenticated_client(client, regular_user):
    """
    Client autenticato con utente normale

    Args:
        client: Flask test client
        regular_user: User fixture

    Returns:
        Authenticated Flask test client
    """
    with client:
        client.post('/login', data={
            'username': regular_user.username,
            'password': 'testpassword123'
        })
        yield client
