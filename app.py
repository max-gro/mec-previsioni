"""
Flask App - Sistema MEC Previsioni
Applicazione multi-pagina con autenticazione
"""

from flask import Flask, render_template, redirect, url_for, request
from flask_login import LoginManager, login_required, current_user
from models import db, User
from config import get_config
import os
import logging
from logging.handlers import RotatingFileHandler
from sqlalchemy import text


def setup_logging(app):
    """
    Configura il sistema di logging per l'applicazione
    """
    # Livello di log dalla configurazione
    log_level = getattr(logging, app.config['LOG_LEVEL'].upper(), logging.INFO)

    # Formato del log
    formatter = logging.Formatter(
        app.config['LOG_FORMAT'],
        datefmt=app.config['LOG_DATE_FORMAT']
    )

    # Handler: file o stdout
    if app.config['LOG_FILE']:
        # Crea directory logs se non esiste
        log_dir = os.path.dirname(app.config['LOG_FILE'])
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)

        # Rotating file handler (max 10MB, 5 backup files)
        handler = RotatingFileHandler(
            app.config['LOG_FILE'],
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
    else:
        # Stream handler (stdout)
        handler = logging.StreamHandler()

    handler.setFormatter(formatter)
    handler.setLevel(log_level)

    # Configura logger dell'app
    app.logger.addHandler(handler)
    app.logger.setLevel(log_level)

    # Riduci verbosità librerie esterne
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

    app.logger.info(f"Logging configurato: level={app.config['LOG_LEVEL']}, file={app.config['LOG_FILE']}")


def create_app(config_name=None):
    """
    Application Factory Pattern

    Args:
        config_name: Nome della configurazione ('development', 'production', 'testing')
                    Se None, usa FLASK_ENV da variabili d'ambiente

    Returns:
        Flask app configurata
    """
    app = Flask(__name__)

    # Carica configurazione appropriata
    config_class = get_config(config_name)
    app.config.from_object(config_class)

    # Setup logging
    setup_logging(app)
    
    # Assicurati che la cartella instance esista
    instance_path = os.path.join(app.root_path, 'instance')
    if not os.path.exists(instance_path):
        os.makedirs(instance_path)
    
    # Inizializza estensioni
    db.init_app(app)

    # Stampa informazioni sul database
    with app.app_context():
        eng = db.engine
        app.logger.info(f"Database: {eng.dialect.name} (driver: {eng.dialect.driver})")
        app.logger.debug(f"Database URL: {eng.url}")

        # Verifica connessione database
        try:
            version = db.session.execute(text("select version()")).scalar()
            app.logger.info(f"Database version: {version}")
        except Exception as e:
            app.logger.warning(f"Impossibile verificare versione database: {e}")

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
            # Leggi credenziali da configurazione (variabili d'ambiente)
            admin_username = app.config.get('ADMIN_USERNAME', 'admin')
            admin_email = app.config.get('ADMIN_EMAIL', 'admin@example.com')
            admin_password = app.config.get('ADMIN_PASSWORD')

            if not admin_password:
                app.logger.warning(
                    "ADMIN_PASSWORD non settata! Creo utente admin con password temporanea. "
                    "CAMBIARE IMMEDIATAMENTE in produzione!"
                )
                admin_password = 'admin123'  # Fallback solo in development

            # Crea utente admin
            admin = User(
                username=admin_username,
                email=admin_email,
                role='admin',
                active=True
            )
            admin.set_password(admin_password)
            db.session.add(admin)
            app.logger.info(f"✓ Utente admin creato: {admin_username}")

            # Crea utente demo (opzionale)
            demo_username = app.config.get('DEMO_USERNAME')
            demo_password = app.config.get('DEMO_PASSWORD')

            if demo_username and demo_password:
                demo = User(
                    username=demo_username,
                    email=app.config.get('DEMO_EMAIL', 'demo@example.com'),
                    role='user',
                    active=True
                )
                demo.set_password(demo_password)
                db.session.add(demo)
                app.logger.info(f"✓ Utente demo creato: {demo_username}")

            db.session.commit()
    
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

    # =============================================================================
    # ERROR HANDLERS
    # =============================================================================

    @app.errorhandler(403)
    def forbidden(e):
        """Handler per errori 403 Forbidden"""
        app.logger.warning(f"403 Forbidden: {request.url} - User: {current_user.username if current_user.is_authenticated else 'Anonymous'}")
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def page_not_found(e):
        """Handler per errori 404 Not Found"""
        app.logger.warning(f"404 Not Found: {request.url}")
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        """Handler per errori 500 Internal Server Error"""
        app.logger.error(f"500 Internal Server Error: {request.url}", exc_info=True)
        # Rollback della sessione DB in caso di errore
        db.session.rollback()
        return render_template('errors/500.html'), 500

    @app.errorhandler(413)
    def request_entity_too_large(e):
        """Handler per file troppo grandi"""
        app.logger.warning(f"413 Request Entity Too Large: {request.url}")
        return render_template('errors/413.html'), 413

    @app.errorhandler(Exception)
    def handle_exception(e):
        """
        Handler generico per eccezioni non gestite
        Solo in development mostra lo stack trace, in production usa template generico
        """
        app.logger.error(f"Unhandled exception: {str(e)}", exc_info=True)

        # In development, lascia che Werkzeug mostri il debugger
        if app.config['DEBUG']:
            raise e

        # In production, mostra pagina errore generica
        db.session.rollback()
        return render_template('errors/500.html'), 500

    # =============================================================================
    # RETURN APP
    # =============================================================================

    app.logger.info(f"Applicazione MEC Previsioni avviata (env: {app.config.get('ENV', 'unknown')})")

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
