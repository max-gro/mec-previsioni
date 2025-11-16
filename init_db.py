"""
Script per inizializzare il database
Esegui con: python init_db.py
"""

import os
import sys

# Aggiungi la directory corrente al path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

def init_database():
    """Inizializza il database e crea le tabelle"""
    
    # 1. Crea la cartella instance PRIMA di importare l'app
    instance_path = os.path.join(os.path.dirname(__file__), 'instance')
    if not os.path.exists(instance_path):
        os.makedirs(instance_path)
        print(f"✓ Cartella instance creata: {instance_path}")
    else:
        print(f"✓ Cartella instance già esistente: {instance_path}")
    
    # 2. ADESSO importa l'app
    from app import create_app
    from models import (
        db, User, Rottura, OrdineAcquisto, AnagraficaFile,
        Controparte, Modello, FileOrdini, Ordine,
        TraceElaborazioneFile, TraceElaborazioneRecord
    ) 
    
    app = create_app()
    
    with app.app_context():
        # Mostra il path del database
        db_uri = app.config['SQLALCHEMY_DATABASE_URI']
        print(f"\nDatabase URI: {db_uri}")
        
        # Estrai il path del file db
        if db_uri.startswith('sqlite:///'):
            db_path = db_uri.replace('sqlite:///', '')
            # Su Windows, converti in path locale
            if sys.platform == 'win32' and ':' not in db_path:
                db_path = os.path.abspath(db_path)
            print(f"Database path: {db_path}")
        
        # Elimina database esistente (solo per sviluppo!)
        db_file = os.path.join(instance_path, 'mec.db')
        if os.path.exists(db_file):
            try:
                os.remove(db_file)
                print(f"✓ Database esistente rimosso: {db_file}")
            except Exception as e:
                print(f"⚠ Impossibile rimuovere database: {e}")
        
        # Crea tutte le tabelle
        try:
            db.create_all()
            print("✓ Tabelle database create con successo!")
        except Exception as e:
            print(f"✗ Errore nella creazione delle tabelle: {e}")
            return
        
        # Crea utente admin di default
        try:
            if not User.query.filter_by(username='admin').first():
                admin = User(
                    username='admin',
                    email='admin@example.com',
                    role='admin',
                    active=True
                )
                admin.set_password('admin123')
                db.session.add(admin)
                db.session.commit()
                print("✓ Utente admin creato (username: admin, password: admin123)")
            else:
                print("✓ Utente admin già esistente")
        except Exception as e:
            print(f"⚠ Errore creazione utente admin: {e}")
        
        # Crea utente demo
        try:
            if not User.query.filter_by(username='demo').first():
                demo = User(
                    username='demo',
                    email='demo@example.com',
                    role='user',
                    active=True
                )
                demo.set_password('demo123')
                db.session.add(demo)
                db.session.commit()
                print("✓ Utente demo creato (username: demo, password: demo123)")
            else:
                print("✓ Utente demo già esistente")
        except Exception as e:
            print(f"⚠ Errore creazione utente demo: {e}")
        
        print("\n" + "="*60)
        print("Database inizializzato con successo!")
        print("="*60)
        print(f"\nDatabase location: {db_file}")
        print(f"Database exists: {os.path.exists(db_file)}")
        if os.path.exists(db_file):
            print(f"Database size: {os.path.getsize(db_file)} bytes")
        
        print("\nCredenziali di accesso:")
        print("  Admin -> username: admin, password: admin123")
        print("  Demo  -> username: demo, password: demo123")
        print("\nAvvia l'app con: python app.py")
        print("Poi vai su: http://localhost:5010/login")

if __name__ == '__main__':
    try:
        init_database()
    except Exception as e:
        print(f"\n✗ ERRORE: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)