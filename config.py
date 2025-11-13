"""
Configurazione Flask Application - MEC Previsioni
Gestisce configurazioni per diversi ambienti (Development, Production, Testing)
"""

import os
import secrets
from dotenv import load_dotenv
from datetime import timedelta

# Carica variabili d'ambiente da .env
load_dotenv()

# Base directory del progetto
BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Configurazione base condivisa tra tutti gli ambienti"""

    # =============================================================================
    # SECURITY - Configurazioni critiche
    # =============================================================================

    # Secret key per sessioni, CSRF, cookie signing
    # DEVE essere settata tramite variabile d'ambiente in produzione!
    SECRET_KEY = os.environ.get('SECRET_KEY')

    if not SECRET_KEY:
        # In development, genera una chiave casuale ad ogni avvio (OK per dev)
        # In production, DEVE essere settata o l'app fallisce
        if os.environ.get('FLASK_ENV') == 'production':
            raise ValueError(
                "SECRET_KEY non settata! "
                "Genera una chiave sicura con: python -c 'import secrets; print(secrets.token_hex(32))' "
                "e aggiungila al file .env come SECRET_KEY=..."
            )
        else:
            # Development: genera chiave temporanea (riavvio = nuova sessione)
            SECRET_KEY = secrets.token_hex(32)
            print("⚠️  [CONFIG] SECRET_KEY non settata, generata chiave temporanea per development")

    # CSRF Protection
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # 1 ora

    # Base directory
    BASE_DIR = BASE_DIR

    # =============================================================================
    # DATABASE
    # =============================================================================

    # Database URI - Default SQLite, override con DATABASE_URL
    db_path = os.path.join(BASE_DIR, "instance", "mec.db")
    db_path = db_path.replace('\\', '/')  # Windows compatibility

    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or f'sqlite:///{db_path}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False  # Log SQL queries (solo in debug)

    # Connection pool settings (per PostgreSQL)
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_recycle': 3600,
        'pool_pre_ping': True,  # Verifica connessione prima dell'uso
    }

    # =============================================================================
    # SESSION & COOKIES
    # =============================================================================

    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    SESSION_COOKIE_SECURE = False  # Override in Production
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_NAME = 'mec_session'

    # =============================================================================
    # FILE UPLOAD
    # =============================================================================

    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_UPLOAD_SIZE_MB', 100)) * 1024 * 1024
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'INPUT', 'po')
    ALLOWED_EXTENSIONS = {'pdf', 'xls', 'xlsx'}

    # =============================================================================
    # PAGINATION
    # =============================================================================

    ITEMS_PER_PAGE = int(os.environ.get('ITEMS_PER_PAGE', 20))

    # =============================================================================
    # LOGGING
    # =============================================================================

    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.environ.get('LOG_FILE', None)  # None = stdout
    LOG_FORMAT = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

    # =============================================================================
    # CACHE
    # =============================================================================

    CACHE_TYPE = os.environ.get('CACHE_TYPE', 'simple')
    CACHE_DEFAULT_TIMEOUT = int(os.environ.get('CACHE_DEFAULT_TIMEOUT', 300))
    CACHE_REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

    # =============================================================================
    # APPLICATION SETTINGS
    # =============================================================================

    # Credenziali utenti di default (da .env)
    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'admin@example.com')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD')  # DEVE essere settata!

    DEMO_USERNAME = os.environ.get('DEMO_USERNAME', 'demo')
    DEMO_EMAIL = os.environ.get('DEMO_EMAIL', 'demo@example.com')
    DEMO_PASSWORD = os.environ.get('DEMO_PASSWORD', 'demo123')


class DevelopmentConfig(Config):
    """Configurazione per ambiente di sviluppo"""

    DEBUG = True
    TESTING = False

    # SQL query logging in development
    SQLALCHEMY_ECHO = os.environ.get('SQL_ECHO', 'False').lower() == 'true'

    # Development: cookie non richiedono HTTPS
    SESSION_COOKIE_SECURE = False

    # Log più verboso
    LOG_LEVEL = 'DEBUG'


class ProductionConfig(Config):
    """Configurazione per ambiente di produzione"""

    DEBUG = False
    TESTING = False

    # SECURITY: Cookie HTTPS only
    SESSION_COOKIE_SECURE = True

    # Validazioni aggiuntive per produzione
    if not os.environ.get('ADMIN_PASSWORD'):
        raise ValueError(
            "ADMIN_PASSWORD non settata! "
            "In produzione è OBBLIGATORIO settare una password sicura nel .env"
        )

    # Warning se si usa SQLite in produzione
    if 'sqlite' in Config.SQLALCHEMY_DATABASE_URI.lower():
        print("⚠️  [CONFIG] ATTENZIONE: Stai usando SQLite in produzione! "
              "Raccomandato PostgreSQL per performance e affidabilità.")

    # Log su file in produzione
    if not Config.LOG_FILE:
        Config.LOG_FILE = os.path.join(Config.BASE_DIR, 'logs', 'production.log')


class TestingConfig(Config):
    """Configurazione per testing"""

    TESTING = True
    DEBUG = True

    # Database in-memory per test
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

    # Disabilita CSRF nei test
    WTF_CSRF_ENABLED = False

    # Secret key fissa per test riproducibili
    SECRET_KEY = 'test-secret-key-do-not-use-in-production'


# =============================================================================
# CONFIGURAZIONE FACTORY
# =============================================================================

config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config(env_name=None):
    """
    Ritorna la classe di configurazione appropriata per l'ambiente

    Args:
        env_name: Nome ambiente ('development', 'production', 'testing')
                 Se None, legge da FLASK_ENV o usa 'default'

    Returns:
        Config class appropriata
    """
    if env_name is None:
        env_name = os.environ.get('FLASK_ENV', 'development')

    return config_by_name.get(env_name, DevelopmentConfig)


# =============================================================================
# DEBUG INFO (solo se eseguito direttamente)
# =============================================================================

if __name__ == '__main__':
    print("=== MEC PREVISIONI - CONFIG DEBUG ===\n")

    env = os.environ.get('FLASK_ENV', 'development')
    cfg = get_config(env)

    print(f"Ambiente: {env}")
    print(f"Config class: {cfg.__name__}")
    print(f"DEBUG: {cfg.DEBUG}")
    print(f"Database URI: {cfg.SQLALCHEMY_DATABASE_URI}")
    print(f"SECRET_KEY settata: {'✅' if cfg.SECRET_KEY else '❌'}")
    print(f"ADMIN_PASSWORD settata: {'✅' if cfg.ADMIN_PASSWORD else '❌'}")
    print(f"Log level: {cfg.LOG_LEVEL}")
    print(f"Cache type: {cfg.CACHE_TYPE}")
    print(f"Session cookie secure: {cfg.SESSION_COOKIE_SECURE}")
