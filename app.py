"""
Flask App - Sistema MEC Previsioni
Applicazione multi-pagina con autenticazione
"""

from flask import Flask, render_template, redirect, url_for
from flask_login import LoginManager, login_required, current_user
from models import db, User
from config import DevelopmentConfig, ProductionConfig
import os
from sqlalchemy import text


def create_app(config_class=DevelopmentConfig):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Assicurati che la cartella instance esista
    instance_path = os.path.join(app.root_path, 'instance')
    if not os.path.exists(instance_path):
        os.makedirs(instance_path)
    
    # Inizializza estensioni
    db.init_app(app)

    # Stampa informazioni sul database
    with app.app_context():
        eng = db.engine
        print(f"[DB] Dialect: {eng.dialect.name}  Driver: {eng.dialect.driver}")
        print(f"[DB] URL effettivo: {eng.url}")

        # Versione database (solo per PostgreSQL)
        if eng.dialect.name == 'postgresql':
            print("[DB] Versione:", db.session.execute(text("select version()")).scalar())
        else:
            print("[DB] Versione: SQLite (locale)")

        db.create_all()

    # Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Effettua il login per accedere a questa pagina.'
    login_manager.login_message_category = 'warning'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Crea database se non esiste
    with app.app_context():
        db.create_all()
        # Crea utente admin di default se non esiste
        if User.query.count() == 0:
            admin = User(username='admin', email='admin@example.com', role='admin', active=True)
            admin.set_password('123admin123')  # CAMBIARE IN PRODUZIONE!
            db.session.add(admin)
            
            demo = User(username='demo', email='demo@example.com', role='user', active=True)
            demo.set_password('123demo123')
            db.session.add(demo)
            
            db.session.commit()
            print("✓ Utenti di default creati: admin/admin123 e demo/demo123")
    
    # Registra blueprints
    from routes.auth import auth_bp
    from routes.previsioni import previsioni_bp
    #from routes.anagrafica import anagrafica_bp
    from routes.rotture import rotture_bp
    from routes.users import users_bp
    from routes.ordini import ordini_bp  # 👈 NUOVO
    from routes.anagrafiche import anagrafiche_bp  # Gestione file anagrafiche Excel
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(previsioni_bp, url_prefix='/previsioni')
    #app.register_blueprint(anagrafica_bp, url_prefix='/anagrafica')
    app.register_blueprint(rotture_bp, url_prefix='/rotture')
    app.register_blueprint(users_bp, url_prefix='/users')
    app.register_blueprint(ordini_bp, url_prefix='/ordini')  # 👈 NUOVO
    app.register_blueprint(anagrafiche_bp, url_prefix='/anagrafiche')  # Gestione file anagrafiche                                                                                              
    
    # Homepage/Dashboard - PROTETTA DA LOGIN
    @app.route('/')
    @login_required
    def index():
        """Dashboard principale - richiede login"""
        return render_template('index.html')
    
    # Context processor per rendere current_user disponibile in tutti i template
    @app.context_processor
    def inject_user():
        return dict(current_user=current_user)
    
    return app

if __name__ == '__main__':
    app = create_app()
    print("\n" + "="*60)
    print("🚀 SERVER AVVIATO")
    print("="*60)
    print("\n📍 Vai su: http://localhost:5010")
    print("\n🔐 Credenziali di accesso:")
    print("   Admin: admin / admin123")
    print("   Demo:  demo / demo123")
    print("\n" + "="*60 + "\n")
    app.run(debug=True, host='0.0.0.0', port=5010)
