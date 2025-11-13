"""
Ordine Acquisto Model - Gestione Ordini di Acquisto
"""

from extensions import db
from datetime import datetime
from typing import Optional


class OrdineAcquisto(db.Model):
    """
    Modello Ordini di Acquisto

    Attributes:
        id: ID file ordine (primary key)
        anno: Anno di riferimento
        filename: Nome file PDF
        filepath: Path completo file
        data_acquisizione: Data acquisizione file
        data_elaborazione: Data elaborazione file (nullable)
        esito: Stato elaborazione ('Da processare', 'Processato', 'Errore')
        note: Note aggiuntive (opzionale)
        created_at: Data creazione record
        updated_at: Data ultimo aggiornamento
    """

    __tablename__ = 'ordini_acquisto'

    id = db.Column('id_file_ordini_acquisto', db.Integer, primary_key=True)
    anno = db.Column(db.Integer, nullable=False, index=True)
    filename = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(500), nullable=False, unique=True)
    data_acquisizione = db.Column(
        db.Date,
        nullable=False,
        default=lambda: datetime.utcnow().date()
    )
    data_elaborazione = db.Column(db.DateTime)
    esito = db.Column(
        db.String(50),
        default='Da processare',
        nullable=False,
        index=True
    )
    note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    def __repr__(self) -> str:
        return f'<OrdineAcquisto {self.anno} - {self.filename}>'

    def mark_as_processed(self) -> None:
        """Marca l'ordine come processato"""
        self.esito = 'Processato'
        self.data_elaborazione = datetime.utcnow()

    def mark_as_error(self, error_message: Optional[str] = None) -> None:
        """
        Marca l'ordine come errore

        Args:
            error_message: Messaggio di errore da salvare nelle note
        """
        self.esito = 'Errore'
        self.data_elaborazione = datetime.utcnow()
        if error_message:
            self.note = error_message if not self.note else f"{self.note}\n{error_message}"

    @staticmethod
    def get_by_anno(anno: int) -> list['OrdineAcquisto']:
        """
        Recupera tutti gli ordini per un anno specifico

        Args:
            anno: Anno di riferimento

        Returns:
            Lista di oggetti OrdineAcquisto
        """
        return OrdineAcquisto.query.filter_by(anno=anno).order_by(OrdineAcquisto.created_at.desc()).all()

    @staticmethod
    def get_pending() -> list['OrdineAcquisto']:
        """
        Recupera tutti gli ordini in attesa di elaborazione

        Returns:
            Lista di oggetti OrdineAcquisto con esito 'Da processare'
        """
        return OrdineAcquisto.query.filter_by(esito='Da processare').order_by(OrdineAcquisto.created_at).all()

    def to_dict(self) -> dict:
        """
        Converte l'oggetto OrdineAcquisto in dizionario

        Returns:
            Dizionario con dati ordine
        """
        return {
            'id': self.id,
            'anno': self.anno,
            'filename': self.filename,
            'filepath': self.filepath,
            'data_acquisizione': self.data_acquisizione.isoformat() if self.data_acquisizione else None,
            'data_elaborazione': self.data_elaborazione.isoformat() if self.data_elaborazione else None,
            'esito': self.esito,
            'note': self.note,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
