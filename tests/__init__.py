"""
Test Suite - MEC Previsioni
============================
Test suite completa per l'applicazione MEC Previsioni.

Struttura:
- tests/conftest.py: Fixtures comuni
- tests/unit/: Test unitari (models, utils, functions)
- tests/integration/: Test di integrazione (routes, workflows)

Esecuzione:
    pytest                          # Tutti i test
    pytest tests/unit               # Solo unit test
    pytest tests/integration        # Solo integration test
    pytest -m unit                  # Test con marker 'unit'
    pytest --cov                    # Con coverage

Markers:
    @pytest.mark.unit              # Test unitario
    @pytest.mark.integration       # Test di integrazione
    @pytest.mark.slow              # Test lento
"""
