"""
Script di test standalone per la pipeline ordini
Evita dipendenze non necessarie (matplotlib, lifelines, ecc.)
"""
import os
import sys

# Setup path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Setup environment
os.environ['FLASK_ENV'] = 'development'

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import DevelopmentConfig

# Crea app Flask minimale
app = Flask(__name__)
app.config.from_object(DevelopmentConfig)

# Inizializza DB
from models import db
db.init_app(app)

# Importa modelli
from models import (
    User, FileOrdini, Controparte, Modello, Ordine,
    TraceElaborazioneFile, TraceElaborazioneRecord
)

# Importa servizi pipeline
from services.ordini_parser import leggi_ordine_excel_to_tsv
from services.ordini_db_inserter import inserisci_ordine_da_tsv
from services.file_manager import completa_elaborazione_ordine

def test_pipeline():
    """Test completo della pipeline ordini"""

    with app.app_context():
        # 1. Crea database
        print("="*60)
        print("STEP 1: Creazione Database")
        print("="*60)

        db.create_all()
        print("✓ Tabelle create")

        # Crea utente admin
        admin = User(
            username='admin',
            email='admin@example.com',
            role='admin',
            active=True
        )
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print(f"✓ Utente admin creato (ID: {admin.id})")

        # 2. Crea record file_ordine
        print("\n" + "="*60)
        print("STEP 2: Creazione Record FileOrdini")
        print("="*60)

        base_dir = os.path.abspath(os.path.dirname(__file__))
        input_file = os.path.join(base_dir, 'INPUT', 'po', '2024', 'ordine_test_2024.xlsx')

        if not os.path.exists(input_file):
            print(f"✗ File test non trovato: {input_file}")
            print("Esegui prima: python create_test_ordini.py")
            return False

        file_ordine = FileOrdini(
            anno=2024,
            filename='ordine_test_2024.xlsx',
            filepath=input_file,
            data_acquisizione=datetime(2024, 1, 15, 10, 0, 0),
            esito='Da processare',
            created_by=admin.id,
            updated_by=admin.id
        )
        db.session.add(file_ordine)
        db.session.commit()
        print(f"✓ FileOrdini creato (ID: {file_ordine.id})")

        # 3. Test parsing Excel → TSV
        print("\n" + "="*60)
        print("STEP 3: Parsing Excel → TSV")
        print("="*60)

        output_elab_dir = os.path.join(base_dir, 'OUTPUT_ELAB', 'po')

        success, tsv_path, error, stats = leggi_ordine_excel_to_tsv(
            file_ordine.id,
            input_file,
            output_elab_dir
        )

        if not success:
            print(f"✗ Parsing fallito: {error}")
            return False

        print(f"✓ TSV generato: {tsv_path}")
        print(f"  - Righe: {stats['n_righe']}")
        print(f"  - Ordini: {stats['n_ordini_unici']}")
        print(f"  - Modelli: {stats['n_modelli_unici']}")

        # 4. Test inserimento DB
        print("\n" + "="*60)
        print("STEP 4: Inserimento Database")
        print("="*60)

        success, db_stats, error = inserisci_ordine_da_tsv(
            file_ordine.id,
            tsv_path,
            admin.id
        )

        if not success:
            print(f"✗ Inserimento DB fallito: {error}")
            return False

        print(f"✓ Dati inseriti nel database")
        print(f"  - Ordini: {db_stats['n_ordini']}")
        print(f"  - Modelli inseriti: {db_stats['n_modelli_inseriti']}")
        print(f"  - Modelli aggiornati: {db_stats['n_modelli_aggiornati']}")

        # 5. Verifica dati nel DB
        print("\n" + "="*60)
        print("STEP 5: Verifica Dati nel Database")
        print("="*60)

        # Controparti
        controparti = Controparte.query.all()
        print(f"\n✓ Controparti ({len(controparti)}):")
        for c in controparti:
            print(f"  - {c.controparte}")

        # Modelli
        modelli = Modello.query.all()
        print(f"\n✓ Modelli ({len(modelli)}):")
        for m in modelli[:5]:  # Prime 5
            print(f"  - {m.cod_modello_norm} ({m.nome_modello})")

        # Ordini
        ordini = Ordine.query.all()
        print(f"\n✓ Ordini ({len(ordini)}):")
        for o in ordini[:5]:  # Primi 5
            print(f"  - {o.ordine_modello_pk}: {o.item} x{o.qta} = €{o.importo_eur}")

        # Trace
        traces = TraceElaborazioneFile.query.filter_by(id_file_ordine=file_ordine.id).all()
        print(f"\n✓ Trace Elaborazione ({len(traces)}):")
        for t in traces:
            stato_icon = '✓' if t.stato == 'success' else '✗'
            print(f"  {stato_icon} {t.step}: {t.messaggio[:50]}...")

        # 6. Test spostamento file
        print("\n" + "="*60)
        print("STEP 6: Spostamento File INPUT → OUTPUT")
        print("="*60)

        output_dir = os.path.join(base_dir, 'OUTPUT', 'po', '2024')
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, 'ordine_test_2024.xlsx')

        success, error = completa_elaborazione_ordine(
            file_ordine.id,
            input_file,
            output_path
        )

        if not success:
            print(f"✗ Spostamento fallito: {error}")
            return False

        print(f"✓ File spostato in OUTPUT")

        # Verifica stato file
        file_ordine = FileOrdini.query.get(file_ordine.id)
        print(f"✓ Stato file: {file_ordine.esito}")
        print(f"✓ Data elaborazione: {file_ordine.data_elaborazione}")

        # 7. Riepilogo finale
        print("\n" + "="*60)
        print("✅ PIPELINE COMPLETATA CON SUCCESSO!")
        print("="*60)
        print(f"\nDatabase: {os.path.join(base_dir, 'instance', 'mec.db')}")
        print(f"Controparti: {Controparte.query.count()}")
        print(f"Modelli: {Modello.query.count()}")
        print(f"Ordini: {Ordine.query.count()}")
        print(f"File Ordini: {FileOrdini.query.count()}")
        print(f"Trace: {TraceElaborazioneFile.query.count()}")

        return True


if __name__ == '__main__':
    try:
        success = test_pipeline()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ ERRORE: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
