"""
Gunicorn Configuration File - MEC Previsioni
"""

import os
import multiprocessing

# =============================================================================
# Server Socket
# =============================================================================

# Bind address (localhost:5010 per single worker, o porte multiple per load balancing)
bind = "127.0.0.1:5010"

# Backlog (numero connessioni in coda)
backlog = 2048

# =============================================================================
# Worker Processes
# =============================================================================

# Numero di worker processes
# Formula raccomandata: (2 x numero_cpu) + 1
workers = multiprocessing.cpu_count() * 2 + 1  # es. 4 CPU = 9 workers

# Tipo di worker
# - sync: Default, blocking (buono per CPU-intensive)
# - gevent/eventlet: Async (buono per I/O-intensive, richiede gevent installato)
# - gthread: Threaded workers
worker_class = "sync"

# Threads per worker (solo con worker_class=gthread)
# threads = 2

# Worker connections (solo per async workers)
# worker_connections = 1000

# Timeout worker (secondi) - aumentato per operazioni lunghe come calcolo previsioni
timeout = 300  # 5 minuti

# Graceful timeout (tempo per chiusura pulita)
graceful_timeout = 30

# Keepalive
keepalive = 5

# =============================================================================
# Logging
# =============================================================================

# Access log
accesslog = "/var/www/mec-previsioni/logs/gunicorn-access.log"

# Error log
errorlog = "/var/www/mec-previsioni/logs/gunicorn-error.log"

# Log level: debug, info, warning, error, critical
loglevel = "info"

# Access log format
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Disable request logging per stdout (solo file)
# accesslog = "-"  # Decommentare per log su stdout

# =============================================================================
# Process Naming
# =============================================================================

# Nome processo
proc_name = "mec-previsioni"

# =============================================================================
# Server Mechanics
# =============================================================================

# Daemon mode (NO se usi systemd!)
daemon = False

# PID file
pidfile = "/var/www/mec-previsioni/logs/gunicorn.pid"

# User e group (lascia None se gestito da systemd)
user = None
group = None

# Umask
umask = 0o007

# Temp directory
tmp_upload_dir = None

# =============================================================================
# Server Hooks
# =============================================================================

def on_starting(server):
    """
    Called just before the master process is initialized.
    """
    server.log.info("Gunicorn master starting...")


def on_reload(server):
    """
    Called to recycle workers during a reload via SIGHUP.
    """
    server.log.info("Gunicorn reloading...")


def when_ready(server):
    """
    Called just after the server is started.
    """
    server.log.info("Gunicorn server ready. Listening on: %s", server.address)


def pre_fork(server, worker):
    """
    Called just before a worker is forked.
    """
    pass


def post_fork(server, worker):
    """
    Called just after a worker has been forked.
    """
    server.log.info("Worker spawned (pid: %s)", worker.pid)


def pre_exec(server):
    """
    Called just before a new master process is forked.
    """
    server.log.info("Forked child, re-executing.")


def worker_int(worker):
    """
    Called just after a worker exited on SIGINT or SIGQUIT.
    """
    worker.log.info("Worker received INT or QUIT signal")


def worker_abort(worker):
    """
    Called when a worker received the SIGABRT signal.
    """
    worker.log.info("Worker received SIGABRT signal")


def worker_exit(server, worker):
    """
    Called just after a worker has been exited.
    """
    server.log.info("Worker exited (pid: %s)", worker.pid)


# =============================================================================
# SSL (se non usi Apache/Nginx come reverse proxy)
# =============================================================================

# keyfile = '/path/to/keyfile'
# certfile = '/path/to/certfile'
# ssl_version = TLS  # o SSLv23
# cert_reqs = ssl.CERT_REQUIRED
# ca_certs = '/path/to/ca_certs'

# =============================================================================
# Security
# =============================================================================

# Limit request line size
limit_request_line = 4094

# Limit request header field size
limit_request_field_size = 8190

# Limit number of request header fields
limit_request_fields = 100

# =============================================================================
# Development Override (per testing locale)
# =============================================================================

# Se ENV=development, usa configurazioni più permissive
if os.environ.get('FLASK_ENV') == 'development':
    workers = 2
    loglevel = 'debug'
    reload = True  # Auto-reload su cambiamenti file
    accesslog = '-'  # Log su stdout
    errorlog = '-'

# =============================================================================
# Production Hardening
# =============================================================================

# Pre-load application code (migliora performance ma disabilita reload)
if os.environ.get('FLASK_ENV') == 'production':
    preload_app = True

    # Max requests per worker prima di restart (previene memory leaks)
    max_requests = 1000
    max_requests_jitter = 50

    # Worker timeout più corto in production
    # timeout = 120
