"""
Flask App - Sistema MEC Previsioni
Applicazione multi-pagina con autenticazione
"""

from flask import Flask, render_template, redirect, url_for
from flask_login import LoginManager, login_required, current_user
from models import db, User
from config import DevelopmentConfig, ProductionConfig
from utils.db_log import init_log_session, cleanup_log_session
import os
import logging
from logging.handlers import RotatingFileHandler
from sqlalchemy import text


def setup_logging(app):
    """
    Configura il sistema di logging per l'applicazione.

    - Crea cartella logs/ se non esiste
    - File di log rotanti (max 10MB, mantiene 10 backup)
    - Formato: [timestamp] [LEVEL] [modulo] messaggio
    - Livello DEBUG in development, INFO in production
    """
    # Crea cartella logs se non esiste
    logs_dir = os.path.join(app.root_path, 'logs')
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)

    # Determina livello log in base all'ambiente
    log_level = logging.DEBUG if app.config['DEBUG'] else logging.INFO

    # Formato log dettagliato
    log_format = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # File handler principale (rotating, max 10MB, 10 backup files)
    file_handler = RotatingFileHandler(
        os.path.join(logs_dir, 'app.log'),
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=10,
        encoding='utf-8'
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(log_format)

    # File handler per errori critici (separato)
    error_handler = RotatingFileHandler(
        os.path.join(logs_dir, 'errors.log'),
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(log_format)

    # Console handler (per vedere log anche in console)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(log_format)

    # Configura root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(error_handler)
    root_logger.addHandler(console_handler)

    # Log di startup
    app.logger.info('='*60)
    app.logger.info('Sistema MEC Previsioni - Avvio applicazione')
    app.logger.info(f'Ambiente: {"Development" if app.config["DEBUG"] else "Production"}')
    app.logger.info(f'Livello log: {logging.getLevelName(log_level)}')
    app.logger.info(f'Log file: {os.path.join(logs_dir, "app.log")}')
    app.logger.info('='*60)


def create_app(config_class=DevelopmentConfig):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # ✅ SETUP LOGGING (prima di tutto per catturare ogni evento)
    setup_logging(app)

    # Assicurati che la cartella instance esista
    instance_path = os.path.join(app.root_path, 'instance')
    if not os.path.exists(instance_path):
        os.makedirs(instance_path)
        app.logger.info(f'Creata cartella instance: {instance_path}')

    # Inizializza estensioni
    db.init_app(app)

    # Inizializza sessione log separata (AUTONOMOUS TRANSACTION)
    with app.app_context():
        init_log_session(app.config['SQLALCHEMY_DATABASE_URI'])

    # Stampa informazioni sul database
    with app.app_context():
        eng = db.engine
        app.logger.info(f"[DB Main] Dialect: {eng.dialect.name}  Driver: {eng.dialect.driver}")
        app.logger.info(f"[DB Main] URL: {str(eng.url).split('@')[-1] if '@' in str(eng.url) else eng.url}")  # Nascondi password

        # Mostra versione solo per PostgreSQL
        if eng.dialect.name == 'postgresql':
            version = db.session.execute(text("select version()")).scalar()
            app.logger.info(f"[DB Main] PostgreSQL version: {version.split(',')[0]}")
        elif eng.dialect.name == 'sqlite':
            version = db.session.execute(text("select sqlite_version()")).scalar()
            app.logger.info(f"[DB Main] SQLite version: {version}")

        db.create_all()
        app.logger.info("[DB Main] Tabelle database create/verificate")

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
            admin.set_password('admin123')  # CAMBIARE IN PRODUZIONE!
            db.session.add(admin)

            demo = User(username='demo', email='demo@example.com', role='user', active=True)
            demo.set_password('demo123')
            db.session.add(demo)

            db.session.commit()
            app.logger.info("Utenti di default creati: admin/admin123 e demo/demo123")
    
    # Registra blueprints
    from routes.auth import auth_bp
    from routes.previsioni import previsioni_bp
    #from routes.anagrafica import anagrafica_bp
    from routes.rotture import rotture_bp
    from routes.users import users_bp
    from routes.ordini import ordini_bp
    from routes.anagrafiche import anagrafiche_bp  # Gestione file anagrafiche Excel
    from routes.dashboard import dashboard_bp  # Dashboard elaborazioni

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')  # Dashboard elaborazioni
    app.register_blueprint(previsioni_bp, url_prefix='/previsioni')
    #app.register_blueprint(anagrafica_bp, url_prefix='/anagrafica')
    app.register_blueprint(rotture_bp, url_prefix='/rotture')
    app.register_blueprint(users_bp, url_prefix='/users')
    app.register_blueprint(ordini_bp, url_prefix='/ordini')
    app.register_blueprint(anagrafiche_bp, url_prefix='/anagrafiche')  # Gestione file anagrafiche

    # Teardown handler per pulire la log session
    @app.teardown_appcontext
    def shutdown_log_session(exception=None):
        """Pulisce la log session alla fine di ogni request"""
        cleanup_log_session()

    # Homepage con card per funzioni principali
    @app.route('/')
    @login_required
    def index():
        """Homepage con card per accedere alle funzioni principali"""
        return render_template('home.html')

    # Filtri Jinja2 custom per formattazione date
    @app.template_filter('datetime_format')
    def datetime_format(value, format='%d/%m/%Y %H:%M'):
        """Formatta datetime in formato italiano con ora"""
        if value is None:
            return '-'
        if isinstance(value, str):
            return value
        return value.strftime(format)

    @app.template_filter('date_format')
    def date_format(value, format='%d/%m/%Y'):
        """Formatta date (senza ora) in formato italiano"""
        if value is None:
            return '-'
        if isinstance(value, str):
            return value
        return value.strftime(format)

    # Context processor per rendere current_user disponibile in tutti i template
    @app.context_processor
    def inject_user():
        return dict(current_user=current_user)

    return app

if __name__ == '__main__':
    app = create_app()
    app.logger.info("="*60)
    app.logger.info("🚀 SERVER AVVIATO")
    app.logger.info("="*60)
    app.logger.info("📍 Vai su: http://localhost:5010")
    app.logger.info("🔐 Credenziali di accesso:")
    app.logger.info("   Admin: admin / admin123")
    app.logger.info("   Demo:  demo / demo123")
    app.logger.info("="*60)
    app.run(debug=True, host='0.0.0.0', port=5010)
