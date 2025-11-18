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
    __tablename__ = 'file_rotture'

    id = db.Column('id_file_rotture', db.Integer, primary_key=True)
    anno = db.Column(db.Integer, nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(500), nullable=False)
    data_acquisizione = db.Column(db.Date, nullable=False, default=lambda: datetime.utcnow().date())
    data_elaborazione = db.Column(db.DateTime)
    esito = db.Column(db.String(50), default='Da processare')  # Da processare, Processato, Errore
    note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id_user'))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id_user'))

    # Relationships
    creator = db.relationship('User', foreign_keys=[created_by], backref='rotture_create')
    updater = db.relationship('User', foreign_keys=[updated_by], backref='rotture_update')

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
    created_by = db.Column(db.Integer, db.ForeignKey('users.id_user'))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id_user'))

    # Relationships
    creator = db.relationship('User', foreign_keys=[created_by], backref='ordini_acquisto_create')
    updater = db.relationship('User', foreign_keys=[updated_by], backref='ordini_acquisto_update')

    def __repr__(self):
        return f'<OrdineAcquisto {self.anno} - {self.filename}>'


class AnagraficaFile(db.Model):
    """Modello Anagrafiche File (Excel)"""
    __tablename__ = 'file_anagrafiche'

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
    created_by = db.Column(db.Integer, db.ForeignKey('users.id_user'))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id_user'))

    # Relationships
    creator = db.relationship('User', foreign_keys=[created_by], backref='anagrafiche_create')
    updater = db.relationship('User', foreign_keys=[updated_by], backref='anagrafiche_update')

    def __repr__(self):
        return f'<AnagraficaFile {self.marca} - {self.filename}>'


class Controparte(db.Model):
    """Modello Controparti (Clienti/Fornitori)"""
    __tablename__ = 'controparti'

    cod_controparte = db.Column(db.String(50), primary_key=True)
    controparte = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id_user'))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id_user'))

    # Relationships
    creator = db.relationship('User', foreign_keys=[created_by], backref='controparti_create')
    updater = db.relationship('User', foreign_keys=[updated_by], backref='controparti_update')

    def __repr__(self):
        return f'<Controparte {self.cod_controparte} - {self.controparte}>'


class Modello(db.Model):
    """Modello Modelli/Prodotti"""
    __tablename__ = 'modelli'

    cod_modello = db.Column(db.String(50), primary_key=True)
    cod_modello_norm = db.Column(db.String(100), nullable=False)
    cod_modello_fabbrica = db.Column(db.String(100))
    nome_modello = db.Column(db.String(200))
    nome_modello_it = db.Column(db.String(200))
    divisione = db.Column(db.String(100))
    marca = db.Column(db.String(100))
    desc_modello = db.Column(db.Text)
    produttore = db.Column(db.String(200))
    famiglia = db.Column(db.String(100))
    tipo = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id_user'))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id_user'))
    updated_from = db.Column(db.String(10))

    # Relationships
    creator = db.relationship('User', foreign_keys=[created_by], backref='modelli_create')
    updater = db.relationship('User', foreign_keys=[updated_by], backref='modelli_update')

    def __repr__(self):
        return f'<Modello {self.cod_modello} - {self.nome_modello}>'


class FileOrdine(db.Model):
    """Modello File Ordini"""
    __tablename__ = 'file_ordini'

    id_file_ordine = db.Column(db.Integer, primary_key=True)
    anno = db.Column(db.Integer, nullable=False)
    marca = db.Column(db.String(100))
    filename = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(500), nullable=False)
    data_acquisizione = db.Column(db.Date, nullable=False, default=lambda: datetime.utcnow().date())
    data_elaborazione = db.Column(db.DateTime)
    esito = db.Column(db.String(50), default='Da processare')
    note = db.Column(db.Text)
    cod_seller = db.Column(db.String(50), db.ForeignKey('controparti.cod_controparte'))
    cod_buyer = db.Column(db.String(50), db.ForeignKey('controparti.cod_controparte'))
    data_ordine = db.Column(db.Date)
    oggetto_ordine = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id_user'))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id_user'))

    # Relationships
    seller = db.relationship('Controparte', foreign_keys=[cod_seller], backref='ordini_vendita')
    buyer = db.relationship('Controparte', foreign_keys=[cod_buyer], backref='ordini_acquisto')
    creator = db.relationship('User', foreign_keys=[created_by], backref='fileordini_create')
    updater = db.relationship('User', foreign_keys=[updated_by], backref='fileordini_update')

    def __repr__(self):
        return f'<FileOrdine {self.anno} - {self.filename}>'


class Ordine(db.Model):
    """Modello Ordini - Dettaglio righe ordine"""
    __tablename__ = 'ordini'

    ordine_modello_pk = db.Column(db.String(200), primary_key=True)
    id_file_ordine = db.Column(db.Integer, db.ForeignKey('file_ordini.id_file_ordine'), nullable=False)
    cod_ordine = db.Column(db.String(100), nullable=False)
    cod_modello = db.Column(db.String(50), db.ForeignKey('modelli.cod_modello'), nullable=False)
    brand = db.Column(db.String(100))
    item = db.Column(db.String(200))
    ean = db.Column(db.String(50))
    prezzo_eur = db.Column(db.Numeric(10, 2))
    qta = db.Column(db.Integer)
    importo_eur = db.Column(db.Numeric(12, 2))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id_user'))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id_user'))

    # Relationships
    file_ordine = db.relationship('FileOrdine', backref='ordini')
    modello = db.relationship('Modello', backref='ordini')
    creator = db.relationship('User', foreign_keys=[created_by], backref='ordini_create')
    updater = db.relationship('User', foreign_keys=[updated_by], backref='ordini_update')

    def __repr__(self):
        return f'<Ordine {self.cod_ordine} - {self.cod_modello}>'


class TraceElaborazioneFile(db.Model):
    """Modello Trace Elaborazioni File"""
    __tablename__ = 'trace_elaborazioni_file'

    id_trace = db.Column(db.Integer, primary_key=True)
    id_file_ordine = db.Column(db.Integer, db.ForeignKey('file_ordini.id_file_ordine'), nullable=False)
    tipo_file = db.Column(db.String(10), nullable=False)
    step = db.Column(db.String(50), nullable=False)
    stato = db.Column(db.String(20), nullable=False)
    messaggio = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    file_ordine = db.relationship('FileOrdine', backref='trace_elaborazioni')

    def __repr__(self):
        return f'<TraceElaborazioneFile {self.id_trace} - {self.tipo_file} - {self.step}>'


class TraceElaborazioneRecord(db.Model):
    """Modello Trace Elaborazioni Record"""
    __tablename__ = 'trace_elaborazioni_record'

    id_trace_record = db.Column(db.Integer, primary_key=True)
    id_trace_file = db.Column(db.Integer, db.ForeignKey('trace_elaborazioni_file.id_trace'), nullable=False)
    riga_file = db.Column(db.Integer)
    tipo_record = db.Column(db.String(20))
    record_key = db.Column(db.String(200))
    record_data = db.Column(db.JSON)
    errore = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    trace_file = db.relationship('TraceElaborazioneFile', backref='trace_records')

    def __repr__(self):
        return f'<TraceElaborazioneRecord {self.id_trace_record} - {self.tipo_record}>'