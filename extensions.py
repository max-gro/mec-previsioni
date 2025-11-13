"""
Flask Extensions - Inizializzazione estensioni riutilizzabili
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_caching import Cache

# Database
db = SQLAlchemy()

# Login Manager
login_manager = LoginManager()

# Cache
cache = Cache()


def init_extensions(app):
    """
    Inizializza tutte le estensioni Flask

    Args:
        app: Istanza Flask app
    """
    # Database
    db.init_app(app)

    # Login Manager
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Effettua il login per accedere a questa pagina.'
    login_manager.login_message_category = 'warning'

    # Cache
    cache.init_app(app, config={
        'CACHE_TYPE': app.config.get('CACHE_TYPE', 'SimpleCache'),
        'CACHE_DEFAULT_TIMEOUT': app.config.get('CACHE_DEFAULT_TIMEOUT', 300),
        'CACHE_REDIS_URL': app.config.get('CACHE_REDIS_URL'),
        'CACHE_DIR': app.config.get('CACHE_DIR', '/tmp/flask_cache')
    })

    app.logger.info(f"Estensioni inizializzate: DB, Login, Cache ({app.config.get('CACHE_TYPE', 'simple')})")
