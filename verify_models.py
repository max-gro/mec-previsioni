#!/usr/bin/env python3
"""
Script di verifica modelli SQLAlchemy
Controlla che tutti i modelli siano definiti correttamente
"""

import sys
import os

# Aggiungi il path dell'app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def verify_models():
    """Verifica che tutti i modelli siano importabili e ben definiti"""
    print("=" * 80)
    print("  VERIFICA MODELLI SQLALCHEMY")
    print("=" * 80)

    try:
        from models import (
            db, User,
            FileRottura, FileOrdine, FileAnagrafica,
            Controparte, Modello, Componente,
            Ordine, ModelloComponente,
            UtenteRottura, Rivenditore, Rottura, RotturaComponente,
            TraceElab, TraceElabDett,
            TraceElaborazione, TraceElaborazioneDettaglio,  # Mantenuti per compatibilità
            OrdineAcquisto, AnagraficaFile  # Alias per retrocompatibilità
        )
        print("\n✓ Tutti i modelli importati correttamente\n")
    except ImportError as e:
        print(f"\n✗ ERRORE durante import modelli: {e}\n")
        return False

    # Verifica struttura modelli NUOVI (da creare nel DB)
    models_to_check = [
        ('User', User, 'users'),
        ('FileRottura', FileRottura, 'file_rotture'),
        ('FileOrdine', FileOrdine, 'file_ordini'),
        ('FileAnagrafica', FileAnagrafica, 'file_anagrafiche'),
        ('Controparte', Controparte, 'controparti'),
        ('Modello', Modello, 'modelli'),
        ('Componente', Componente, 'componenti'),
        ('Ordine', Ordine, 'ordini'),
        ('ModelloComponente', ModelloComponente, 'modelli_componenti'),
        ('UtenteRottura', UtenteRottura, 'utenti_rotture'),
        ('Rivenditore', Rivenditore, 'rivenditori'),
        ('Rottura', Rottura, 'rotture'),
        ('RotturaComponente', RotturaComponente, 'rotture_componenti'),
        ('TraceElab', TraceElab, 'trace_elab'),
        ('TraceElabDett', TraceElabDett, 'trace_elab_dett'),
    ]

    print("Modelli definiti:")
    print("-" * 80)

    all_ok = True
    for model_name, model_class, expected_table in models_to_check:
        try:
            tablename = model_class.__tablename__

            # Verifica tablename
            if tablename != expected_table:
                print(f"  ⚠ {model_name:30s} → {tablename:30s} (atteso: {expected_table})")
                all_ok = False
            else:
                print(f"  ✓ {model_name:30s} → {tablename}")

            # Verifica che abbia colonne
            if not hasattr(model_class, '__table__'):
                print(f"    ✗ ERRORE: {model_name} non ha __table__")
                all_ok = False
                continue

            # Conta colonne
            columns = model_class.__table__.columns
            print(f"    → {len(columns)} colonne definite")

        except Exception as e:
            print(f"  ✗ {model_name:30s} → ERRORE: {e}")
            all_ok = False

    # Verifica alias di retrocompatibilità
    print("\n" + "-" * 80)
    print("Alias di retrocompatibilità:")
    print("-" * 80)

    if OrdineAcquisto is FileOrdine:
        print("  ✓ OrdineAcquisto → FileOrdine")
    else:
        print("  ✗ OrdineAcquisto non è un alias di FileOrdine")
        all_ok = False

    if AnagraficaFile is FileAnagrafica:
        print("  ✓ AnagraficaFile → FileAnagrafica")
    else:
        print("  ✗ AnagraficaFile non è un alias di FileAnagrafica")
        all_ok = False

    # Report finale
    print("\n" + "=" * 80)
    if all_ok:
        print("✓ TUTTI I MODELLI SONO CORRETTI")
    else:
        print("✗ ALCUNI MODELLI HANNO PROBLEMI")
    print("=" * 80 + "\n")

    return all_ok


def show_relationships():
    """Mostra le relazioni tra i modelli"""
    print("=" * 80)
    print("  RELAZIONI TRA MODELLI")
    print("=" * 80 + "\n")

    from models import (
        FileOrdine, Ordine, Controparte, Modello,
        FileAnagrafica, ModelloComponente, Componente,
        FileRottura, Rottura, UtenteRottura, Rivenditore, RotturaComponente
    )

    relationships = [
        ("PIPELINE ORDINI", [
            "FileOrdine → Controparte (seller/buyer)",
            "FileOrdine ← Ordine (1:N)",
            "Ordine → Modello (N:1)",
        ]),
        ("PIPELINE ANAGRAFICHE", [
            "FileAnagrafica ← ModelloComponente (1:N)",
            "ModelloComponente → Modello (N:1)",
            "ModelloComponente → Componente (N:1)",
        ]),
        ("PIPELINE ROTTURE", [
            "FileRottura ← Rottura (1:N)",
            "Rottura → Modello (N:1)",
            "Rottura → UtenteRottura (N:1)",
            "Rottura → Rivenditore (N:1)",
            "Rottura ← RotturaComponente (1:N)",
            "RotturaComponente → Componente (N:1)",
        ]),
    ]

    for section, rels in relationships:
        print(f"{section}:")
        print("-" * 80)
        for rel in rels:
            print(f"  {rel}")
        print()


if __name__ == '__main__':
    if '--help' in sys.argv or '-h' in sys.argv:
        print("""
Uso: python verify_models.py [opzioni]

Opzioni:
  --relationships  Mostra anche le relazioni tra modelli
  -h, --help      Mostra questo messaggio di aiuto

Descrizione:
  Verifica che tutti i modelli SQLAlchemy siano definiti correttamente
  prima di eseguire la migrazione del database.
""")
        sys.exit(0)

    success = verify_models()

    if success and '--relationships' in sys.argv:
        show_relationships()

    sys.exit(0 if success else 1)
