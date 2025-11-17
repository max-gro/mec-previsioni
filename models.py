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
    __tablename__ = 'ordini_acquisto'
    
    id = db.Column('id_file_ordini_acquisto', db.Integer, primary_key=True)
    anno = db.Column(db.Integer, nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(500), nullable=False)
    data_acquisizione = db.Column(db.Date, nullable=False, default=lambda: datetime.utcnow().date())
    data_elaborazione = db.Column(db.DateTime)  # Popolato dopo elaborazione
    esito = db.Column(db.String(50), default='Da processare')  # Da processare, Processato, Errore
    note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
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
    created_by = db.Column(db.String(80))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = db.Column(db.String(80))

    def __repr__(self):
        return f'<AnagraficaFile {self.marca} - {self.filename}>'


class Modello(db.Model):
    """Modello Anagrafica Modelli (aggiornato da pipeline ordini, rotture, anagrafiche)"""
    __tablename__ = 'modelli'

    cod_modello = db.Column(db.String(100), primary_key=True)
    cod_modello_norm = db.Column(db.String(100), unique=True, nullable=False, index=True)
    cod_modello_fabbrica = db.Column(db.String(100))
    nome_modello = db.Column(db.String(200))
    nome_modello_it = db.Column(db.String(200))

    # Campi aggiornati da pipeline rotture
    divisione = db.Column(db.String(100))
    marca = db.Column(db.String(100))
    desc_modello = db.Column(db.Text)
    produttore = db.Column(db.String(200))
    famiglia = db.Column(db.String(100))
    tipo = db.Column(db.String(100))

    # Audit
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(80))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = db.Column(db.String(80))
    updated_from = db.Column(db.String(10))  # 'ord', 'ana', 'rot'

    def __repr__(self):
        return f'<Modello {self.cod_modello}>'


class Componente(db.Model):
    """Modello Anagrafica Componenti (CRU da pipeline anagrafiche)"""
    __tablename__ = 'componenti'

    cod_componente = db.Column(db.String(100), primary_key=True)
    cod_componente_norm = db.Column(db.String(100), unique=True, nullable=False, index=True)
    desc_componente_it = db.Column(db.Text)
    cod_alt = db.Column(db.String(100))
    cod_alt_2 = db.Column(db.String(100))
    pos_no = db.Column(db.String(50))
    part_no = db.Column(db.String(100))
    part_name_en = db.Column(db.String(200))
    part_name_cn = db.Column(db.String(200))
    part_name_it = db.Column(db.String(200))
    cod_ean = db.Column(db.String(50))
    barcode = db.Column(db.String(10))  # 'N', '1', 'Q'

    # Prezzi
    unit_price_usd = db.Column(db.Numeric(10, 2))
    unit_price_notra_noiva_netto_eur = db.Column(db.Numeric(10, 2))
    unit_price_tra_noiva_netto_eur = db.Column(db.Numeric(10, 2))
    unit_price_public_eur = db.Column(db.Numeric(10, 2))

    stat = db.Column(db.String(50))
    softech_stat = db.Column(db.String(50))

    # Audit
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(80))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = db.Column(db.String(80))

    def __repr__(self):
        return f'<Componente {self.cod_componente}>'


class ModelloComponente(db.Model):
    """Modello relazione Modelli-Componenti (CRUD da pipeline anagrafiche)"""
    __tablename__ = 'modelli_componenti'

    modello_componente = db.Column(db.String(200), primary_key=True)  # "cod_modello|cod_componente"
    id_file_anagrafiche = db.Column(db.Integer, db.ForeignKey('anagrafiche_file.id_file_anagrafiche'), nullable=False)
    cod_modello = db.Column(db.String(100), db.ForeignKey('modelli.cod_modello'), nullable=False)
    cod_componente = db.Column(db.String(100), db.ForeignKey('componenti.cod_componente'), nullable=False)
    qta = db.Column(db.Integer, nullable=False)

    # Audit
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(80))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = db.Column(db.String(80))

    # Relationships
    file_anagrafica = db.relationship('AnagraficaFile', backref='modelli_componenti')
    modello = db.relationship('Modello', backref='componenti_associati')
    componente = db.relationship('Componente', backref='modelli_associati')

    def __repr__(self):
        return f'<ModelloComponente {self.modello_componente}>'