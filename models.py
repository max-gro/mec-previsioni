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

    def __repr__(self):
        return f'<FileRottura {self.anno} - {self.filename}>'


class FileOrdine(db.Model):
    """Modello File Ordini di Acquisto"""
    __tablename__ = 'file_ordini'

    id = db.Column('id_file_ordini', db.Integer, primary_key=True)
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

    def __repr__(self):
        return f'<FileOrdine {self.anno} - {self.filename}>'


class FileAnagrafica(db.Model):
    """Modello File Anagrafiche (Excel)"""
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

    def __repr__(self):
        return f'<FileAnagrafica {self.marca} - {self.filename}>'


# ============================================================================
# TABELLE ANAGRAFICHE (MASTER DATA)
# ============================================================================

class Modello(db.Model):
    """Modello Anagrafica Modelli Prodotti"""
    __tablename__ = 'modelli'

    cod_modello = db.Column(db.String(100), primary_key=True)
    cod_modello_norm = db.Column(db.String(100), nullable=False, unique=True, index=True)
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
    updated_from = db.Column(db.String(10))  # 'ordini', 'rotture', 'anagrafiche'

    def __repr__(self):
        return f'<Modello {self.cod_modello}>'


class Componente(db.Model):
    """Modello Anagrafica Componenti"""
    __tablename__ = 'componenti'

    cod_componente = db.Column(db.String(100), primary_key=True)
    cod_componente_norm = db.Column(db.String(100), nullable=False, unique=True, index=True)
    desc_componente_it = db.Column(db.String(500))
    cod_alt = db.Column(db.String(100))
    cod_alt_2 = db.Column(db.String(100))
    pos_no = db.Column(db.String(50))
    part_no = db.Column(db.String(100))
    part_name_en = db.Column(db.String(500))
    part_name_cn = db.Column(db.String(500))
    part_name_it = db.Column(db.String(500))
    cod_ean = db.Column(db.String(50))
    barcode = db.Column(db.String(10))  # N, 1, Q
    unit_price_usd = db.Column(db.Numeric(10, 2))
    unit_price_notra_noiva_netto_eur = db.Column(db.Numeric(10, 2))
    unit_price_tra_noiva_netto_eur = db.Column(db.Numeric(10, 2))
    unit_price_public_eur = db.Column(db.Numeric(10, 2))
    stat = db.Column(db.String(50))
    softech_stat = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id_user'))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id_user'))

    def __repr__(self):
        return f'<Componente {self.cod_componente}>'


class Utente(db.Model):
    """Modello Anagrafica Utenti (clienti finali)"""
    __tablename__ = 'utenti'

    cod_utente = db.Column(db.String(100), primary_key=True)
    pv_utente = db.Column(db.String(200))
    comune_utente = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id_user'))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id_user'))

    def __repr__(self):
        return f'<Utente {self.cod_utente}>'


class Rivenditore(db.Model):
    """Modello Anagrafica Rivenditori"""
    __tablename__ = 'rivenditori'

    cod_rivenditore = db.Column(db.String(100), primary_key=True)
    pv_rivenditore = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id_user'))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id_user'))

    def __repr__(self):
        return f'<Rivenditore {self.cod_rivenditore}>'


# ============================================================================
# TABELLE DATI TRANSAZIONALI (ROTTURE)
# ============================================================================

class Rottura(db.Model):
    """Modello Singola Rottura (riga estratta da file Excel)"""
    __tablename__ = 'rotture'

    id_rottura = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_file_rotture = db.Column(db.Integer, db.ForeignKey('file_rotture.id_file_rotture'), nullable=False, index=True)

    # Dati identificativi
    prot = db.Column(db.String(100), nullable=False, index=True)  # Natural key
    cod_modello = db.Column(db.String(100), db.ForeignKey('modelli.cod_modello'), index=True)
    cod_rivenditore = db.Column(db.String(100), db.ForeignKey('rivenditori.cod_rivenditore'), index=True)
    cod_utente = db.Column(db.String(100), db.ForeignKey('utenti.cod_utente'), index=True)

    # Dati prodotto
    piattaforma = db.Column(db.String(100))
    cat = db.Column(db.String(100))  # C.A.T.
    flag_consumer = db.Column(db.String(1))  # S/N
    flag_da_fatturare = db.Column(db.String(1))  # S/N
    cod_matricola = db.Column(db.String(100))
    cod_modello_fabbrica = db.Column(db.String(100))

    # Date
    data_competenza = db.Column(db.Date)
    data_acquisto = db.Column(db.Date)
    data_apertura = db.Column(db.Date)
    data_1 = db.Column(db.Date)
    data_2 = db.Column(db.Date)
    data_3 = db.Column(db.Date)
    data_4 = db.Column(db.Date)
    data_5 = db.Column(db.Date)
    data_6 = db.Column(db.Date)
    data_7 = db.Column(db.Date)

    # Dettagli rottura
    difetto = db.Column(db.Text)
    problema_segnalato = db.Column(db.Text)
    riparazione = db.Column(db.Text)
    gg_vita_prodotto = db.Column(db.Integer)
    qta = db.Column(db.Integer)

    # Dati rivenditore/utente (denormalizzati per performance)
    pv_rivenditore = db.Column(db.String(200))
    pv_utente = db.Column(db.String(200))
    comune_utente = db.Column(db.String(200))

    # Dati modello (per update)
    divisione = db.Column(db.String(100))
    marca = db.Column(db.String(100))
    desc_modello = db.Column(db.Text)
    produttore = db.Column(db.String(200))
    famiglia = db.Column(db.String(100))
    tipo = db.Column(db.String(100))

    # Audit
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id_user'))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id_user'))

    def __repr__(self):
        return f'<Rottura {self.prot}>'


class RotturaComponente(db.Model):
    """Modello Relazione Rottura-Componente (M:N)"""
    __tablename__ = 'rotture_componenti'

    id_rottura = db.Column(db.Integer, db.ForeignKey('rotture.id_rottura'), primary_key=True)
    cod_componente = db.Column(db.String(100), db.ForeignKey('componenti.cod_componente'), primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id_user'))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id_user'))

    def __repr__(self):
        return f'<RotturaComponente {self.id_rottura}-{self.cod_componente}>'


# ============================================================================
# TABELLE TRACE (LOGGING ELABORAZIONI)
# ============================================================================

class TraceElaborazioneFile(db.Model):
    """Modello Trace Elaborazione File (livello file)"""
    __tablename__ = 'trace_elaborazioni_file'

    id_trace = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_file = db.Column(db.Integer, nullable=False, index=True)
    tipo_file = db.Column(db.String(10), nullable=False)  # 'ordini', 'rotture', 'anagrafiche'
    step = db.Column(db.String(50), nullable=False)  # 'upload', 'parse', 'validate', 'insert', 'complete'
    stato = db.Column(db.String(20), nullable=False)  # 'start', 'success', 'error', 'warning'
    messaggio = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f'<TraceElaborazioneFile {self.tipo_file}/{self.id_file} - {self.step}>'


class TraceElaborazioneRecord(db.Model):
    """Modello Trace Elaborazione Record (livello riga file)"""
    __tablename__ = 'trace_elaborazioni_record'

    id_trace_record = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_trace_file = db.Column(db.Integer, db.ForeignKey('trace_elaborazioni_file.id_trace'), nullable=False, index=True)
    riga_file = db.Column(db.Integer)
    tipo_record = db.Column(db.String(20))  # 'rottura', 'componente', 'utente', 'rivenditore'
    record_key = db.Column(db.String(200))  # Chiave del record (es. prot, cod_componente)
    record_data = db.Column(db.JSON)  # Dati del record (opzionale)
    errore = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f'<TraceElaborazioneRecord {self.tipo_record} - {self.record_key}>'


# ============================================================================
# BACKWARD COMPATIBILITY (ALIAS)
# ============================================================================

# Alias per backward compatibility con codice esistente
OrdineAcquisto = FileOrdine
AnagraficaFile = FileAnagrafica