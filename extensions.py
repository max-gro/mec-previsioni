"""
Flask Extensions - Inizializzazione estensioni riutilizzabili
"""

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_caching import Cache
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Database
db = SQLAlchemy()

# Database Migrations
migrate = Migrate()

# Login Manager
login_manager = LoginManager()

# Cache
cache = Cache()

# Rate Limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
    strategy="fixed-window"
)


def init_extensions(app):
    """
    Inizializza tutte le estensioni Flask

    Args:
        app: Istanza Flask app
    """
    # Database
    db.init_app(app)

    # Database Migrations
    migrate.init_app(app, db)

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

    # Rate Limiter
    limiter.init_app(app)

    app.logger.info(
        f"Estensioni inizializzate: DB, Migrate, Login, Cache ({app.config.get('CACHE_TYPE', 'simple')}), "
        f"Limiter (default: 200/day, 50/hour)"
    )
