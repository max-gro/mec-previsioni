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
    role = db.Column(db.String(20), default='Utente')
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    created_by = db.Column(db.Integer, default=0, nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        return self.role == 'Amministratore'


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
    data_acquisizione = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    data_elaborazione = db.Column(db.DateTime)
    esito = db.Column(db.String(50), default='Da processare')
    note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id_user'), default=0, nullable=False)
    updated_at = db.Column(db.DateTime)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id_user'), default=0)

    # Relationships
    creator = db.relationship('User', foreign_keys=[created_by], backref='file_rotture_created')
    updater = db.relationship('User', foreign_keys=[updated_by], backref='file_rotture_updated')

    def __repr__(self):
        return f'<FileRottura {self.anno} - {self.filename}>'


class FileOrdine(db.Model):
    """Modello File Ordini di Acquisto (PDF)"""
    __tablename__ = 'file_ordini'

    id = db.Column('id_file_ordine', db.Integer, primary_key=True)
    anno = db.Column(db.Integer, nullable=False)
    marca = db.Column(db.String(100))
    filename = db.Column(db.String(255), nullable=False, unique=True)
    filepath = db.Column(db.String(500), nullable=False)
    data_acquisizione = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    data_elaborazione = db.Column(db.DateTime)
    esito = db.Column(db.String(50), default='Da processare')
    note = db.Column(db.Text)
    cod_seller = db.Column(db.String(100), db.ForeignKey('controparti.cod_controparte'))
    cod_buyer = db.Column(db.String(100), db.ForeignKey('controparti.cod_controparte'))
    data_ordine = db.Column(db.Date)
    oggetto_ordine = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id_user'), default=0, nullable=False)
    updated_at = db.Column(db.DateTime)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id_user'), default=0)

    # Relationships
    seller = db.relationship('Controparte', foreign_keys=[cod_seller], backref='ordini_as_seller')
    buyer = db.relationship('Controparte', foreign_keys=[cod_buyer], backref='ordini_as_buyer')
    creator = db.relationship('User', foreign_keys=[created_by], backref='file_ordini_created')
    updater = db.relationship('User', foreign_keys=[updated_by], backref='file_ordini_updated')

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
    data_acquisizione = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    data_elaborazione = db.Column(db.DateTime)
    esito = db.Column(db.String(50), default='Da processare')
    note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id_user'), default=0, nullable=False)
    updated_at = db.Column(db.DateTime)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id_user'), default=0)

    # Relationships
    creator = db.relationship('User', foreign_keys=[created_by], backref='file_anagrafiche_created')
    updater = db.relationship('User', foreign_keys=[updated_by], backref='file_anagrafiche_updated')

    def __repr__(self):
        return f'<FileAnagrafica {self.marca} - {self.filename}>'


# ============================================================================
# TABELLE BUSINESS - ENTITÀ COMUNI
# ============================================================================

class Controparte(db.Model):
    """Modello Controparti (Seller/Buyer)"""
    __tablename__ = 'controparti'

    cod_controparte = db.Column(db.String(100), primary_key=True)
    controparte = db.Column(db.String(200), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id_user'), default=0, nullable=False)
    updated_at = db.Column(db.DateTime)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id_user'), default=0)

    # Relationships
    creator = db.relationship('User', foreign_keys=[created_by], backref='controparti_created')
    updater = db.relationship('User', foreign_keys=[updated_by], backref='controparti_updated')

    def __repr__(self):
        return f'<Controparte {self.cod_controparte} - {self.controparte}>'


class Modello(db.Model):
    """Modello Modelli Prodotto - TABELLA CENTRALE"""
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
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id_user'), default=0, nullable=False)
    updated_at = db.Column(db.DateTime)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id_user'), default=0)
    updated_from = db.Column(db.String(10))  # 'ORD', 'ANA', 'ROT'

    # Relationships
    creator = db.relationship('User', foreign_keys=[created_by], backref='modelli_created')
    updater = db.relationship('User', foreign_keys=[updated_by], backref='modelli_updated')

    def __repr__(self):
        return f'<Modello {self.cod_modello} - {self.nome_modello}>'


class Componente(db.Model):
    """Modello Componenti"""
    __tablename__ = 'componenti'

    cod_componente = db.Column(db.String(100), primary_key=True)
    cod_componente_norm = db.Column(db.String(100), nullable=False, unique=True)
    componente_it = db.Column(db.Text)
    cod_alt = db.Column(db.String(100))
    cod_alt_2 = db.Column(db.String(100))
    pos_no = db.Column(db.String(50))
    part_no = db.Column(db.String(100))
    part_name_en = db.Column(db.String(200))
    part_name_cn = db.Column(db.String(200))
    part_name_it = db.Column(db.String(200))
    cod_ean = db.Column(db.String(50))
    barcode = db.Column(db.String(10))
    unit_price_usd = db.Column(db.Numeric(10, 2))
    unit_price_notra_noiva_netto_eur = db.Column(db.Numeric(10, 2))
    unit_price_tra_noiva_netto_eur = db.Column(db.Numeric(10, 2))
    unit_price_public_eur = db.Column(db.Numeric(10, 2))
    stat = db.Column(db.String(50))
    softech_stat = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id_user'), default=0, nullable=False)
    updated_at = db.Column(db.DateTime)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id_user'), default=0)

    # Relationships
    creator = db.relationship('User', foreign_keys=[created_by], backref='componenti_created')
    updater = db.relationship('User', foreign_keys=[updated_by], backref='componenti_updated')

    def __repr__(self):
        return f'<Componente {self.cod_componente} - {self.part_name_it}>'


# ============================================================================
# PIPELINE ORDINI
# ============================================================================

class Ordine(db.Model):
    """Modello Righe Ordini (dettaglio componenti per ordine)"""
    __tablename__ = 'ordini'

    ordine_modello = db.Column(db.String(200), primary_key=True)  # cod_ordine|cod_modello
    id_file_ordine = db.Column(db.Integer, db.ForeignKey('file_ordini.id_file_ordine'), nullable=False, index=True)
    cod_ordine = db.Column(db.String(100), nullable=False, index=True)
    cod_modello = db.Column(db.String(100), db.ForeignKey('modelli.cod_modello'), nullable=False, index=True)
    brand = db.Column(db.String(100))
    item = db.Column(db.String(200))
    ean = db.Column(db.String(50))
    prezzo_eur = db.Column(db.Numeric(10, 2))
    qta = db.Column('qtà', db.Integer)
    importo_eur = db.Column(db.Numeric(12, 2))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id_user'), default=0, nullable=False)
    updated_at = db.Column(db.DateTime)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id_user'), default=0)

    # Relationships
    file_ordine = db.relationship('FileOrdine', backref='righe_ordini')
    modello = db.relationship('Modello', backref='ordini')
    creator = db.relationship('User', foreign_keys=[created_by], backref='ordini_created')
    updater = db.relationship('User', foreign_keys=[updated_by], backref='ordini_updated')

    # Constraint UNIQUE
    __table_args__ = (
        db.UniqueConstraint('cod_ordine', 'cod_modello', name='uq_ordine_modello'),
    )

    def __repr__(self):
        return f'<Ordine {self.cod_ordine} - {self.cod_modello}>'


# ============================================================================
# PIPELINE ANAGRAFICHE (BOM - Bill of Materials)
# ============================================================================

class ModelloComponente(db.Model):
    """Modello Modelli-Componenti (BOM - Bill of Materials)"""
    __tablename__ = 'modelli_componenti'

    cod_modello_componente = db.Column(db.String(200), primary_key=True)  # cod_modello|cod_componente
    id_file_anagrafiche = db.Column(db.Integer, db.ForeignKey('file_anagrafiche.id_file_anagrafiche'), nullable=False)
    cod_modello = db.Column(db.String(100), db.ForeignKey('modelli.cod_modello'), nullable=False)
    cod_componente = db.Column(db.String(100), db.ForeignKey('componenti.cod_componente'), nullable=False)
    qta = db.Column('qtà', db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id_user'), default=0, nullable=False)
    updated_at = db.Column(db.DateTime)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id_user'), default=0)

    # Relationships
    file_anagrafica = db.relationship('FileAnagrafica', backref='modelli_componenti')
    modello = db.relationship('Modello', backref='componenti_bom')
    componente = db.relationship('Componente', backref='modelli_bom')
    creator = db.relationship('User', foreign_keys=[created_by], backref='modelli_componenti_created')
    updater = db.relationship('User', foreign_keys=[updated_by], backref='modelli_componenti_updated')

    def __repr__(self):
        return f'<ModelloComponente {self.cod_modello} - {self.cod_componente}>'


# ============================================================================
# PIPELINE ROTTURE
# ============================================================================

class UtenteRottura(db.Model):
    """Modello Utenti Rotture (clienti finali)"""
    __tablename__ = 'utenti_rotture'

    cod_utente_rottura = db.Column(db.String(100), primary_key=True)
    pv_utente_rottura = db.Column(db.String(100))
    comune_utente_rottura = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id_user'), default=0, nullable=False)
    updated_at = db.Column(db.DateTime)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id_user'), default=0)

    # Relationships
    creator = db.relationship('User', foreign_keys=[created_by], backref='utenti_rotture_created')
    updater = db.relationship('User', foreign_keys=[updated_by], backref='utenti_rotture_updated')

    def __repr__(self):
        return f'<UtenteRottura {self.cod_utente_rottura}>'


class Rivenditore(db.Model):
    """Modello Rivenditori"""
    __tablename__ = 'rivenditori'

    cod_rivenditore = db.Column(db.String(100), primary_key=True)
    pv_rivenditore = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id_user'), default=0, nullable=False)
    updated_at = db.Column(db.DateTime)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id_user'), default=0)

    # Relationships
    creator = db.relationship('User', foreign_keys=[created_by], backref='rivenditori_created')
    updater = db.relationship('User', foreign_keys=[updated_by], backref='rivenditori_updated')

    def __repr__(self):
        return f'<Rivenditore {self.cod_rivenditore}>'


class Rottura(db.Model):
    """Modello Rotture (eventi di guasto)"""
    __tablename__ = 'rotture'

    cod_rottura = db.Column(db.String(100), primary_key=True)  # id_file_rotture|prot
    id_file_rotture = db.Column(db.Integer, db.ForeignKey('file_rotture.id_file_rotture'), nullable=False)
    prot = db.Column(db.String(100), nullable=False)
    cod_modello = db.Column(db.String(100), db.ForeignKey('modelli.cod_modello'), nullable=False)
    cod_rivenditore = db.Column(db.String(100), db.ForeignKey('rivenditori.cod_rivenditore'), nullable=False)
    cod_utente = db.Column(db.String(100), db.ForeignKey('utenti_rotture.cod_utente_rottura'), nullable=False)
    cat = db.Column(db.String(100))
    flag_consumer = db.Column(db.String(1))
    flag_da_fatturare = db.Column(db.String(1))
    data_competenza = db.Column(db.Date)
    cod_matricola = db.Column(db.String(100))
    cod_modello_fabbrica = db.Column(db.String(100))
    data_acquisto = db.Column(db.Date)
    data_apertura = db.Column(db.Date)
    difetto = db.Column(db.String(200))
    problema_segnalato = db.Column(db.String(100))
    riparazione = db.Column(db.String(200))
    qta = db.Column('qtà', db.Integer)
    gg_vita_prodotto = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id_user'), default=0, nullable=False)
    updated_at = db.Column(db.DateTime)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id_user'), default=0)

    # Relationships
    file_rottura = db.relationship('FileRottura', backref='rotture')
    modello = db.relationship('Modello', backref='rotture')
    rivenditore = db.relationship('Rivenditore', backref='rotture')
    utente = db.relationship('UtenteRottura', backref='rotture')
    creator = db.relationship('User', foreign_keys=[created_by], backref='rotture_created')
    updater = db.relationship('User', foreign_keys=[updated_by], backref='rotture_updated')

    def __repr__(self):
        return f'<Rottura {self.cod_rottura} - {self.prot}>'


class RotturaComponente(db.Model):
    """Modello Rotture-Componenti (componenti sostituiti in una rottura)"""
    __tablename__ = 'rotture_componenti'

    cod_rottura = db.Column(db.String(100), db.ForeignKey('rotture.cod_rottura'), primary_key=True)
    cod_componente = db.Column(db.String(100), db.ForeignKey('componenti.cod_componente'), primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id_user'), default=0, nullable=False)
    updated_at = db.Column(db.DateTime)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id_user'), default=0)

    # Relationships
    rottura = db.relationship('Rottura', backref='componenti_sostituiti')
    componente = db.relationship('Componente', backref='rotture_componenti')
    creator = db.relationship('User', foreign_keys=[created_by], backref='rotture_componenti_created')
    updater = db.relationship('User', foreign_keys=[updated_by], backref='rotture_componenti_updated')

    def __repr__(self):
        return f'<RotturaComponente {self.cod_rottura} - {self.cod_componente}>'


# ============================================================================
# TABELLE TRACCIAMENTO ELABORAZIONI (NUOVO SISTEMA)
# ============================================================================

class TraceElab(db.Model):
    """Tracciamento Elaborazioni File - livello file"""
    __tablename__ = 'trace_elab'

    id_trace = db.Column(db.Integer, primary_key=True)
    id_file = db.Column(db.Integer, nullable=False, index=True)
    tipo_file = db.Column(db.String(10), nullable=False)  # 'ORD', 'ANA', 'ROT'
    step = db.Column(db.String(50), nullable=False, default='PROCESS')  # 'INIZIO ETL', 'FINE ETL', 'INIZIO UPD DB', 'FINE UPD DB', 'PROCESS'
    stato = db.Column(db.String(20), nullable=False, default='OK')  # 'OK', 'KO'
    messaggio = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationship con i dettagli
    dettagli = db.relationship('TraceElabDett', backref='elaborazione', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<TraceElab {self.tipo_file} #{self.id_file} - {self.step} - {self.stato}>'


class TraceElabDett(db.Model):
    """Tracciamento Elaborazioni Dettaglio - livello record"""
    __tablename__ = 'trace_elab_dett'

    id_trace_dett = db.Column(db.Integer, primary_key=True)
    id_trace = db.Column(db.Integer, db.ForeignKey('trace_elab.id_trace'), nullable=False, index=True)
    record_pos = db.Column(db.Integer)  # Numero riga/record
    record_data = db.Column(db.JSON)  # Dati del record
    messaggio = db.Column(db.Text)
    stato = db.Column(db.String(20), nullable=False, default='OK')  # 'OK', 'KO'
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f'<TraceElabDett Trace:{self.id_trace} Record:{self.record_pos} - {self.stato}>'


# ============================================================================
# COMPATIBILITY ALIASES (per non rompere il codice esistente)
# ============================================================================

# Alias per retrocompatibilità con il codice esistente
OrdineAcquisto = FileOrdine
AnagraficaFile = FileAnagrafica
