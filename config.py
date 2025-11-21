import os
import secrets
from dotenv import load_dotenv
from datetime import timedelta


load_dotenv()

# Base directory del progetto
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    # Flask - Secret Key sicura
    # In development genera una key casuale, in production DEVE essere impostata via env
    SECRET_KEY = os.environ.get('SECRET_KEY')
    
    # Base directory
    BASE_DIR = BASE_DIR
    
    # Database - Path assoluto corretto per Windows
    # SQLite su Windows richiede forward slashes nel URI
    db_path = os.path.join(BASE_DIR, "instance", "mec.db")
    # Converti backslash in forward slash per SQLite URI
    db_path = db_path.replace('\\', '/')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or f'sqlite:///{db_path}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Session
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    SESSION_COOKIE_SECURE = False  # True in produzione con HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Upload
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 16MB max upload
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'INPUT', 'po')
    ALLOWED_EXTENSIONS = {'pdf'} # Estensioni permesse per upload
    
    # Pagination
    ITEMS_PER_PAGE = 20

class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False

    # In development, se SECRET_KEY non è impostata, genera una casuale
    # Nota: questo significa che le sessioni non persistono tra restart
    if not Config.SECRET_KEY:
        SECRET_KEY = secrets.token_urlsafe(32)
        print(f"[WARNING] SECRET_KEY non impostata, generata casualmente per development")

class ProductionConfig(Config):
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True

    # In production, SECRET_KEY DEVE essere impostata, altrimenti fallisce
    if not Config.SECRET_KEY:
        raise ValueError(
            "SECRET_KEY must be set in production environment. "
            "Please set the SECRET_KEY environment variable with a secure random value. "
            "Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
        )

# Per debug: stampa il path del database quando il modulo viene importato
if __name__ != '__main__':
    print(f"[Config] Database path: {Config.db_path}")
    print(f"[Config] Database URI: {Config.SQLALCHEMY_DATABASE_URI}")
