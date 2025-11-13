"""
Anagrafica File Model - Gestione File Anagrafiche Excel
"""

from extensions import db
from datetime import datetime
from typing import Optional


class AnagraficaFile(db.Model):
    """
    Modello Anagrafiche File (Excel)

    Attributes:
        id: ID file anagrafica (primary key)
        anno: Anno di riferimento
        marca: Marca prodotto
        filename: Nome file Excel
        filepath: Path completo file
        data_acquisizione: Data acquisizione file
        data_elaborazione: Data elaborazione file (nullable)
        esito: Stato elaborazione ('Da processare', 'Processato', 'Errore')
        note: Note aggiuntive (opzionale)
        created_at: Data creazione record
        updated_at: Data ultimo aggiornamento
    """

    __tablename__ = 'anagrafiche_file'

    id = db.Column('id_file_anagrafiche', db.Integer, primary_key=True)
    anno = db.Column(db.Integer, nullable=False, index=True)
    marca = db.Column(db.String(100), nullable=False, index=True)
    filename = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(500), nullable=False, unique=True)
    data_acquisizione = db.Column(
        db.Date,
        nullable=False,
        default=lambda: datetime.utcnow().date()
    )
    data_elaborazione = db.Column(db.Date)
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
        return f'<AnagraficaFile {self.marca} - {self.filename}>'

    def mark_as_processed(self) -> None:
        """Marca il file come processato"""
        self.esito = 'Processato'
        self.data_elaborazione = datetime.utcnow().date()

    def mark_as_error(self, error_message: Optional[str] = None) -> None:
        """
        Marca il file come errore

        Args:
            error_message: Messaggio di errore da salvare nelle note
        """
        self.esito = 'Errore'
        self.data_elaborazione = datetime.utcnow().date()
        if error_message:
            self.note = error_message if not self.note else f"{self.note}\n{error_message}"

    @staticmethod
    def get_by_anno(anno: int) -> list['AnagraficaFile']:
        """
        Recupera tutte le anagrafiche per un anno specifico

        Args:
            anno: Anno di riferimento

        Returns:
            Lista di oggetti AnagraficaFile
        """
        return AnagraficaFile.query.filter_by(anno=anno).order_by(AnagraficaFile.created_at.desc()).all()

    @staticmethod
    def get_by_marca(marca: str) -> list['AnagraficaFile']:
        """
        Recupera tutte le anagrafiche per una marca specifica

        Args:
            marca: Marca da cercare

        Returns:
            Lista di oggetti AnagraficaFile
        """
        return AnagraficaFile.query.filter_by(marca=marca).order_by(AnagraficaFile.anno.desc()).all()

    @staticmethod
    def get_pending() -> list['AnagraficaFile']:
        """
        Recupera tutte le anagrafiche in attesa di elaborazione

        Returns:
            Lista di oggetti AnagraficaFile con esito 'Da processare'
        """
        return AnagraficaFile.query.filter_by(esito='Da processare').order_by(AnagraficaFile.created_at).all()

    @staticmethod
    def get_marche_list() -> list[str]:
        """
        Recupera lista distinta di tutte le marche

        Returns:
            Lista di marche (sorted alfabeticamente)
        """
        marche = db.session.query(AnagraficaFile.marca).distinct().order_by(AnagraficaFile.marca).all()
        return [m[0] for m in marche]

    def to_dict(self) -> dict:
        """
        Converte l'oggetto AnagraficaFile in dizionario

        Returns:
            Dizionario con dati anagrafica
        """
        return {
            'id': self.id,
            'anno': self.anno,
            'marca': self.marca,
            'filename': self.filename,
            'filepath': self.filepath,
            'data_acquisizione': self.data_acquisizione.isoformat() if self.data_acquisizione else None,
            'data_elaborazione': self.data_elaborazione.isoformat() if self.data_elaborazione else None,
            'esito': self.esito,
            'note': self.note,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
