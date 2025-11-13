#!/bin/bash
# =============================================================================
# Script Inizializzazione Flask-Migrate
# =============================================================================
# Questo script inizializza Flask-Migrate per la gestione delle migrazioni DB
#
# Uso:
#   chmod +x scripts/init_migrations.sh
#   ./scripts/init_migrations.sh
# =============================================================================

set -e  # Exit on error

echo "====================================================================="
echo "  Inizializzazione Flask-Migrate per MEC Previsioni"
echo "====================================================================="
echo ""

# Check virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  ATTENZIONE: Virtual environment non attivo!"
    echo "   Attiva con: source venv/bin/activate"
    exit 1
fi

# Check Flask-Migrate installed
python -c "import flask_migrate" 2>/dev/null || {
    echo "❌ Flask-Migrate non installato!"
    echo "   Installa con: pip install -r requirements.txt"
    exit 1
}

echo "✅ Virtual environment attivo"
echo "✅ Flask-Migrate installato"
echo ""

# Initialize migrations directory
if [ -d "migrations" ]; then
    echo "⚠️  Directory migrations/ già esistente!"
    read -p "   Vuoi sovrascriverla? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf migrations
        echo "✅ Directory migrations/ rimossa"
    else
        echo "❌ Operazione annullata"
        exit 1
    fi
fi

echo "🔨 Inizializzazione migrations..."
flask db init

echo ""
echo "✅ Flask-Migrate inizializzato con successo!"
echo ""
echo "====================================================================="
echo "  PROSSIMI PASSI:"
echo "====================================================================="
echo ""
echo "1. Crea la prima migrazione:"
echo "   flask db migrate -m \"Initial migration\""
echo ""
echo "2. Applica la migrazione al database:"
echo "   flask db upgrade"
echo ""
echo "3. Per modifiche future allo schema:"
echo "   - Modifica i modelli in models/"
echo "   - flask db migrate -m \"Descrizione modifica\""
echo "   - flask db upgrade"
echo ""
echo "====================================================================="
