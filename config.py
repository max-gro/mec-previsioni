import os
from dotenv import load_dotenv
from datetime import timedelta


load_dotenv()

# Base directory del progetto
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production-2024'
    
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

class ProductionConfig(Config):
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True

# Per debug: stampa il path del database quando il modulo viene importato
if __name__ != '__main__':
    print(f"[Config] Database path: {Config.db_path}")
    print(f"[Config] Database URI: {Config.SQLALCHEMY_DATABASE_URI}")
