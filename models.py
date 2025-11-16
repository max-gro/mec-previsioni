from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    """Modello Utente per autenticazione"""
    __tablename__ = 'users'
    
    id = db.Column('id_user', db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='user')
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        return self.role == 'admin'


# class Componente(db.Model):
    # """Modello Anagrafica Componenti"""
    # __tablename__ = 'componenti'
    
    # id = db.Column(db.Integer, primary_key=True)
    # codice = db.Column(db.String(50), unique=True, nullable=False)
    # descrizione = db.Column(db.String(200))
    # descrizione_en = db.Column(db.String(200))
    # price = db.Column(db.Float, default=0.0)
    # stat = db.Column(db.String(50))
    # fornitore = db.Column(db.String(100))
    # note = db.Column(db.Text)
    # created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # # ✅ RIMOSSA la relationship con Rottura perché ora Rottura gestisce file Excel


class Rottura(db.Model):
    """Modello Gestione File Rotture Excel"""
    __tablename__ = 'rotture'
    
    id = db.Column('id_file_rotture', db.Integer, primary_key=True)
    anno = db.Column(db.Integer, nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(500), nullable=False)
    data_acquisizione = db.Column(db.Date, nullable=False, default=lambda: datetime.utcnow().date())
    data_elaborazione = db.Column(db.DateTime)
    esito = db.Column(db.String(50), default='Da processare')  # Da processare, Processato, Errore
    note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Rottura {self.anno} - {self.filename}>'


class OrdineAcquisto(db.Model):
    """Modello Ordini di Acquisto"""
    __tablename__ = 'file_ordini'

    id = db.Column('id_file_ordine', db.Integer, primary_key=True)
    anno = db.Column(db.Integer, nullable=False)
    marca = db.Column(db.String(100))
    filename = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(500), nullable=False, unique=True)
    data_acquisizione = db.Column(db.Date, nullable=False, default=lambda: datetime.utcnow().date())
    data_elaborazione = db.Column(db.DateTime)
    esito = db.Column(db.String(50), default='Da processare')  # Da processare, Processato, Errore
    note = db.Column(db.Text)
    cod_seller = db.Column(db.String(100))
    cod_buyer = db.Column(db.String(100))
    data_ordine = db.Column(db.Date)
    oggetto_ordine = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(100))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = db.Column(db.String(100))

    def __repr__(self):
        return f'<OrdineAcquisto {self.anno} - {self.filename}>'


class AnagraficaFile(db.Model):
    """Modello Anagrafiche File (Excel)"""
    __tablename__ = 'anagrafiche_file'
    
    id = db.Column('id_file_anagrafiche', db.Integer, primary_key=True)
    anno = db.Column(db.Integer, nullable=False) 
    marca = db.Column(db.String(100), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(500), nullable=False)
    data_acquisizione = db.Column(db.Date, nullable=False, default=lambda: datetime.utcnow().date())
    data_elaborazione = db.Column(db.Date)
    esito = db.Column(db.String(50), default='Da processare')  # Da processare, Processato, Errore
    note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<AnagraficaFile {self.marca} - {self.filename}>'