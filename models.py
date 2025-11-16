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


class Controparte(db.Model):
    """Modello Controparti (Seller/Buyer)"""
    __tablename__ = 'controparti'

    id = db.Column('cod_controparte', db.Integer, primary_key=True)
    controparte = db.Column(db.String(200), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id_user'))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id_user'))

    def __repr__(self):
        return f'<Controparte {self.controparte}>'


class Modello(db.Model):
    """Modello Catalogo Modelli"""
    __tablename__ = 'modelli'

    id = db.Column('cod_modello', db.Integer, primary_key=True)
    cod_modello_norm = db.Column(db.String(100), unique=True, nullable=False, index=True)
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
    updated_from = db.Column(db.String(10))  # 'ord', 'ana', 'rot'

    def __repr__(self):
        return f'<Modello {self.cod_modello_norm}>'


class FileOrdini(db.Model):
    """Modello File Ordini di Acquisto"""
    __tablename__ = 'file_ordini'

    id = db.Column('id_file_ordine', db.Integer, primary_key=True)
    anno = db.Column(db.Integer, nullable=False)
    marca = db.Column(db.String(100))
    filename = db.Column(db.String(255), unique=True, nullable=False)  # Il filename è unico in assoluto
    filepath = db.Column(db.String(500), nullable=False)
    data_acquisizione = db.Column(db.Date, nullable=False, default=lambda: datetime.utcnow().date())
    data_elaborazione = db.Column(db.DateTime)
    esito = db.Column(db.String(50), default='Da processare')  # Da processare, Elaborato, Errore
    note = db.Column(db.Text)

    # Nuovi campi per dati ordine
    cod_seller = db.Column(db.Integer, db.ForeignKey('controparti.cod_controparte'))
    cod_buyer = db.Column(db.Integer, db.ForeignKey('controparti.cod_controparte'))
    data_ordine = db.Column(db.Date)
    oggetto_ordine = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id_user'))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id_user'))

    # Relationships
    seller = db.relationship('Controparte', foreign_keys=[cod_seller], backref='ordini_as_seller')
    buyer = db.relationship('Controparte', foreign_keys=[cod_buyer], backref='ordini_as_buyer')
    ordini = db.relationship('Ordine', backref='file_ordine', cascade='all, delete-orphan')
    traces = db.relationship('TraceElaborazioneFile', backref='file_ordine', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<FileOrdini {self.anno} - {self.filename}>'


class Ordine(db.Model):
    """Modello Righe Ordini (relazione N:N ordine-modelli)"""
    __tablename__ = 'ordini'

    # PK composta: cod_ordine + '|' + cod_modello
    ordine_modello_pk = db.Column(db.String(200), primary_key=True)

    id_file_ordine = db.Column(db.Integer, db.ForeignKey('file_ordini.id_file_ordine'), nullable=False, index=True)
    cod_ordine = db.Column(db.String(100), nullable=False, index=True)
    cod_modello = db.Column(db.Integer, db.ForeignKey('modelli.cod_modello'), nullable=False, index=True)

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
    modello = db.relationship('Modello', backref='ordini')

    # Unique constraint
    __table_args__ = (
        db.UniqueConstraint('cod_ordine', 'cod_modello', name='uq_ordine_modello'),
    )

    def __repr__(self):
        return f'<Ordine {self.cod_ordine} | {self.cod_modello}>'


class TraceElaborazioneFile(db.Model):
    """Trace elaborazione a livello file"""
    __tablename__ = 'trace_elaborazioni_file'

    id = db.Column('id_trace', db.Integer, primary_key=True)
    id_file_ordine = db.Column(db.Integer, db.ForeignKey('file_ordini.id_file_ordine'), nullable=False, index=True)
    tipo_file = db.Column(db.String(10), nullable=False)  # 'ord', 'ana', 'rot'
    step = db.Column(db.String(50), nullable=False)  # lettura, parsing, inserimento_db, spostamento, completato
    stato = db.Column(db.String(20), nullable=False)  # success, error, warning
    messaggio = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    trace_records = db.relationship('TraceElaborazioneRecord', backref='trace_file', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<TraceFile {self.id_file_ordine} - {self.step} - {self.stato}>'


class TraceElaborazioneRecord(db.Model):
    """Trace elaborazione a livello record (per errori dettagliati)"""
    __tablename__ = 'trace_elaborazioni_record'

    id = db.Column('id_trace_record', db.Integer, primary_key=True)
    id_trace_file = db.Column(db.Integer, db.ForeignKey('trace_elaborazioni_file.id_trace'), nullable=False, index=True)
    riga_file = db.Column(db.Integer)  # Numero riga TSV
    tipo_record = db.Column(db.String(20))  # 'ordine', 'controparte', 'modello'
    record_key = db.Column(db.String(200))  # Chiave identificativa (es: cod_ordine|cod_modello)
    record_data = db.Column(db.JSON)  # Dati record per debugging
    errore = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f'<TraceRecord riga {self.riga_file} - {self.tipo_record}>'


# Manteniamo OrdineAcquisto come alias per compatibilità con codice esistente
OrdineAcquisto = FileOrdini


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