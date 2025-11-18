from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

# ============================================================================
# TABELLE DI AUTENTICAZIONE E SISTEMA
# ============================================================================

class User(UserMixin, db.Model):
    """Modello Utente per autenticazione sistema"""
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


# ============================================================================
# TABELLE FILE (GESTIONE UPLOAD E STATO ELABORAZIONE)
# ============================================================================

class FileRottura(db.Model):
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
        return f'<FileRottura {self.anno} - {self.filename}>'


class FileOrdine(db.Model):
    """Modello File Ordini di Acquisto"""
    __tablename__ = 'file_ordini'

class OrdineAcquisto(db.Model):
    """Modello Ordini di Acquisto"""
    __tablename__ = 'ordini_acquisto'

    id = db.Column('id_file_ordini_acquisto', db.Integer, primary_key=True)
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
    creator = db.relationship('User', foreign_keys=[created_by], backref='ordini_acquisto_create')
    updater = db.relationship('User', foreign_keys=[updated_by], backref='ordini_acquisto_update')

    def __repr__(self):
        return f'<FileOrdine {self.anno} - {self.filename}>'


class FileAnagrafica(db.Model):
    """Modello File Anagrafiche (Excel)"""
    __tablename__ = 'file_anagrafiche'

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
    created_by = db.Column(db.Integer, db.ForeignKey('users.id_user'))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<AnagraficaFile {self.marca} - {self.filename}>'


class TraceElaborazione(db.Model):
    """Modello Tracciamento Elaborazioni - un file può avere più elaborazioni"""
    __tablename__ = 'trace_elaborazioni'

    id = db.Column(db.Integer, primary_key=True)

    # Riferimento al file (polimorfismo)
    tipo_pipeline = db.Column(db.String(20), nullable=False)  # 'ordini' | 'anagrafiche' | 'rotture'
    id_file = db.Column(db.Integer, nullable=False)

    # Timing elaborazione
    ts_inizio = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    ts_fine = db.Column(db.DateTime)
    durata_secondi = db.Column(db.Integer)

    # Esito
    esito = db.Column(db.String(50), nullable=False)  # 'In corso' | 'Successo' | 'Errore' | 'Warning'

    # Statistiche elaborazione
    righe_totali = db.Column(db.Integer, default=0)
    righe_ok = db.Column(db.Integer, default=0)
    righe_errore = db.Column(db.Integer, default=0)
    righe_warning = db.Column(db.Integer, default=0)

    # Note generali
    messaggio_globale = db.Column(db.Text)

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship con i dettagli
    dettagli = db.relationship('TraceElaborazioneDettaglio', backref='elaborazione', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<TraceElaborazione {self.tipo_pipeline} #{self.id_file} - {self.esito}>'

    def get_file_object(self):
        """Restituisce l'oggetto file associato (OrdineAcquisto, AnagraficaFile o Rottura)"""
        if self.tipo_pipeline == 'ordini':
            return OrdineAcquisto.query.get(self.id_file)
        elif self.tipo_pipeline == 'anagrafiche':
            return AnagraficaFile.query.get(self.id_file)
        elif self.tipo_pipeline == 'rotture':
            return Rottura.query.get(self.id_file)
        return None

    def percentuale_successo(self):
        """Calcola la percentuale di righe processate con successo"""
        if self.righe_totali == 0:
            return 0
        return round((self.righe_ok / self.righe_totali) * 100, 1)


class TraceElaborazioneDettaglio(db.Model):
    """Modello Dettaglio Righe Elaborazione - anomalie/errori/warning per singola riga"""
    __tablename__ = 'trace_elaborazioni_dettaglio'

    id = db.Column(db.Integer, primary_key=True)

    # FK all'elaborazione
    id_elaborazione = db.Column(db.Integer, db.ForeignKey('trace_elaborazioni.id'), nullable=False)

    # Dettaglio riga/anomalia
    riga_numero = db.Column(db.Integer)
    tipo_messaggio = db.Column(db.String(20))  # 'ERRORE' | 'WARNING' | 'INFO'
    codice_errore = db.Column(db.String(50))
    messaggio = db.Column(db.Text, nullable=False)

    # Contesto aggiuntivo
    campo = db.Column(db.String(100))
    valore_originale = db.Column(db.Text)
    valore_corretto = db.Column(db.Text)

    # Timestamp
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<TraceDettaglio Riga:{self.riga_numero} {self.tipo_messaggio} - {self.codice_errore}>'
