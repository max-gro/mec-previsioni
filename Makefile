# ============================================================================
# Makefile - MEC Previsioni
# ============================================================================
# Comandi comuni per sviluppo, testing e deployment
#
# Uso:
#   make help       - Mostra questo help
#   make install    - Installa dipendenze di sviluppo
#   make test       - Esegue tutti i test
#   make lint       - Esegue linting
#   make format     - Formatta il codice
# ============================================================================

.PHONY: help
help:
	@echo "============================================================================"
	@echo "MEC Previsioni - Makefile Commands"
	@echo "============================================================================"
	@echo ""
	@echo "Setup:"
	@echo "  make install          Installa dipendenze di sviluppo"
	@echo "  make install-hooks    Installa pre-commit hooks"
	@echo ""
	@echo "Development:"
	@echo "  make run              Avvia server di sviluppo"
	@echo "  make shell            Apri Flask shell interattiva"
	@echo ""
	@echo "Code Quality:"
	@echo "  make format           Formatta codice (black + isort)"
	@echo "  make lint             Esegue tutti i linter"
	@echo "  make lint-flake8      Esegue solo flake8"
	@echo "  make lint-pylint      Esegue solo pylint"
	@echo "  make lint-bandit      Esegue security checks"
	@echo "  make typecheck        Esegue type checking (mypy)"
	@echo ""
	@echo "Testing:"
	@echo "  make test             Esegue tutti i test"
	@echo "  make test-unit        Esegue solo unit test"
	@echo "  make test-integration Esegue solo integration test"
	@echo "  make test-cov         Esegue test con coverage report"
	@echo "  make coverage         Apri coverage report HTML"
	@echo ""
	@echo "Database:"
	@echo "  make db-init          Inizializza database"
	@echo "  make db-migrate       Crea nuova migration"
	@echo "  make db-upgrade       Applica migrations"
	@echo "  make db-reset         Reset database (ATTENZIONE!)"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean            Rimuovi file temporanei"
	@echo "  make clean-all        Rimuovi tutto (include venv)"
	@echo ""
	@echo "CI/CD:"
	@echo "  make ci               Esegue tutti i check CI"
	@echo "  make pre-commit       Esegue pre-commit su tutti i file"
	@echo ""
	@echo "============================================================================"

# ============================================================================
# Setup
# ============================================================================

.PHONY: install
install:
	pip install -r requirements-dev.txt

.PHONY: install-hooks
install-hooks:
	pre-commit install

# ============================================================================
# Development
# ============================================================================

.PHONY: run
run:
	python app.py

.PHONY: shell
shell:
	flask shell

# ============================================================================
# Code Quality
# ============================================================================

.PHONY: format
format:
	@echo "Formatting code with black..."
	black .
	@echo "Sorting imports with isort..."
	isort .
	@echo "✓ Formatting complete"

.PHONY: lint
lint: lint-flake8 lint-pylint lint-bandit
	@echo "✓ All linting complete"

.PHONY: lint-flake8
lint-flake8:
	@echo "Running flake8..."
	flake8 .

.PHONY: lint-pylint
lint-pylint:
	@echo "Running pylint..."
	pylint app.py routes/ utils/ || true

.PHONY: lint-bandit
lint-bandit:
	@echo "Running bandit (security checks)..."
	bandit -r . -ll -x ./venv,./env,./tests

.PHONY: typecheck
typecheck:
	@echo "Running mypy (type checking)..."
	mypy . || true

# ============================================================================
# Testing
# ============================================================================

.PHONY: test
test:
	pytest -v

.PHONY: test-unit
test-unit:
	pytest -v -m unit

.PHONY: test-integration
test-integration:
	pytest -v -m integration

.PHONY: test-cov
test-cov:
	pytest --cov=. --cov-report=html --cov-report=term-missing

.PHONY: coverage
coverage:
	@echo "Opening coverage report..."
	@which xdg-open > /dev/null && xdg-open htmlcov/index.html || \
	which open > /dev/null && open htmlcov/index.html || \
	which start > /dev/null && start htmlcov/index.html || \
	echo "Cannot open browser. Report at: htmlcov/index.html"

# ============================================================================
# Database
# ============================================================================

.PHONY: db-init
db-init:
	python init_db.py

.PHONY: db-migrate
db-migrate:
	flask db migrate

.PHONY: db-upgrade
db-upgrade:
	flask db upgrade

.PHONY: db-reset
db-reset:
	@echo "⚠️  WARNING: This will delete the database!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		rm -f instance/mec.db; \
		echo "✓ Database deleted"; \
	fi

# ============================================================================
# Cleanup
# ============================================================================

.PHONY: clean
clean:
	@echo "Cleaning temporary files..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf build
	rm -rf dist
	@echo "✓ Cleanup complete"

.PHONY: clean-all
clean-all: clean
	@echo "⚠️  WARNING: This will delete venv!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		rm -rf venv env .venv; \
		echo "✓ Virtual environment deleted"; \
	fi

# ============================================================================
# CI/CD
# ============================================================================

.PHONY: ci
ci: format lint typecheck test-cov
	@echo "============================================================================"
	@echo "✓ All CI checks passed!"
	@echo "============================================================================"

.PHONY: pre-commit
pre-commit:
	pre-commit run --all-files

# ============================================================================
# Default target
# ============================================================================

.DEFAULT_GOAL := help
