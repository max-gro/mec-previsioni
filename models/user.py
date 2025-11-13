"""
User Model - Gestione Utenti e Autenticazione
"""

from extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from typing import Optional


class User(UserMixin, db.Model):
    """
    Modello Utente per autenticazione e autorizzazione

    Attributes:
        id: ID utente (primary key)
        username: Nome utente univoco
        email: Email utente univoca
        password_hash: Password hashata (bcrypt)
        role: Ruolo utente ('admin' o 'user')
        active: Flag attivazione account
        created_at: Data creazione account
    """

    __tablename__ = 'users'

    id = db.Column('id_user', db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='user', nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f'<User {self.username}>'

    def set_password(self, password: str) -> None:
        """
        Imposta la password dell'utente (hashing automatico)

        Args:
            password: Password in chiaro
        """
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """
        Verifica la password dell'utente

        Args:
            password: Password in chiaro da verificare

        Returns:
            True se la password è corretta, False altrimenti
        """
        return check_password_hash(self.password_hash, password)

    def is_admin(self) -> bool:
        """
        Verifica se l'utente è amministratore

        Returns:
            True se l'utente ha ruolo 'admin', False altrimenti
        """
        return self.role == 'admin'

    @staticmethod
    def get_by_username(username: str) -> Optional['User']:
        """
        Recupera un utente dal username

        Args:
            username: Username da cercare

        Returns:
            Oggetto User se trovato, None altrimenti
        """
        return User.query.filter_by(username=username).first()

    @staticmethod
    def get_by_email(email: str) -> Optional['User']:
        """
        Recupera un utente dall'email

        Args:
            email: Email da cercare

        Returns:
            Oggetto User se trovato, None altrimenti
        """
        return User.query.filter_by(email=email).first()

    def to_dict(self) -> dict:
        """
        Converte l'oggetto User in dizionario (senza password)

        Returns:
            Dizionario con dati utente
        """
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'active': self.active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
