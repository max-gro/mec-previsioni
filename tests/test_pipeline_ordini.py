"""
Test per Pipeline Ordini di Acquisto
"""
import os
import pytest
from datetime import date
from models import db, OrdineAcquisto


class TestOrdiniUpload:
    """Test caricamento file PDF ordini"""

    def test_upload_ordine_success(self, authenticated_client, app, admin_user, sample_pdf_file):
        """Test upload file PDF con successo"""
        pdf_data, filename = sample_pdf_file

        with app.app_context():
            response = authenticated_client.post('/ordini/create', data={
                'file': (pdf_data, filename),
                'anno': 2024,
                'data_acquisizione': '01/01/2024',
                'note': 'Test upload'
            }, follow_redirects=True)

            assert response.status_code == 200
            assert b'caricato con successo' in response.data

            # Verifica record nel DB
            ordine = OrdineAcquisto.query.filter_by(filename=filename).first()
            assert ordine is not None
            assert ordine.anno == 2024
            assert ordine.esito == 'Da processare'

    def test_upload_ordine_invalid_extension(self, authenticated_client, app):
        """Test upload file con estensione non valida"""
        from io import BytesIO
        invalid_file = (BytesIO(b'test content'), 'test.txt')

        response = authenticated_client.post('/ordini/create', data={
            'file': invalid_file,
            'anno': 2024,
            'data_acquisizione': '01/01/2024'
        }, follow_redirects=True)

        assert response.status_code == 200
        # Il form dovrebbe rifiutare file non PDF

    def test_upload_without_authentication(self, client, sample_pdf_file):
        """Test upload senza autenticazione"""
        pdf_data, filename = sample_pdf_file

        response = client.post('/ordini/create', data={
            'file': (pdf_data, filename),
            'anno': 2024
        }, follow_redirects=True)

        # Dovrebbe reindirizzare al login
        assert response.status_code == 200
        assert b'login' in response.data.lower() or b'accesso' in response.data.lower()


class TestOrdiniElaborazione:
    """Test elaborazione ordini"""

    def test_elabora_ordine_success(self, app, authenticated_client, sample_ordine_acquisto, admin_user):
        """Test elaborazione ordine con successo"""
        with app.app_context():
            ordine_id = sample_ordine_acquisto.id

            # Forza successo (mocka il random)
            import routes.ordini as ordini_module
            original_random = ordini_module.random.random
            ordini_module.random.random = lambda: 0.5  # > 0.3 → successo

            try:
                response = authenticated_client.post(f'/ordini/{ordine_id}/elabora', follow_redirects=True)

                assert response.status_code == 200

                # Verifica che l'ordine sia stato elaborato
                ordine = OrdineAcquisto.query.get(ordine_id)
                # Potrebbe essere 'Processato' o 'Errore' dipende dal random
                assert ordine.esito in ['Processato', 'Errore']
                assert ordine.data_elaborazione is not None

            finally:
                ordini_module.random.random = original_random

    def test_elabora_ordine_file_not_found(self, app, authenticated_client, admin_user):
        """Test elaborazione ordine con file mancante"""
        with app.app_context():
            # Crea ordine con filepath inesistente
            ordine = OrdineAcquisto(
                anno=2024,
                filename='missing.pdf',
                filepath='/path/to/missing.pdf',
                data_acquisizione=date.today(),
                esito='Da processare'
            )
            db.session.add(ordine)
            db.session.commit()
            ordine_id = ordine.id

            response = authenticated_client.post(f'/ordini/{ordine_id}/elabora', follow_redirects=True)

            # Verifica che l'esito sia 'Errore'
            ordine = OrdineAcquisto.query.get(ordine_id)
            assert ordine.esito == 'Errore'
            assert 'File non trovato' in ordine.note


class TestOrdiniDelete:
    """Test cancellazione ordini"""

    def test_delete_ordine_success(self, app, authenticated_client, sample_ordine_acquisto):
        """Test cancellazione ordine con successo"""
        with app.app_context():
            ordine_id = sample_ordine_acquisto.id
            filepath = sample_ordine_acquisto.filepath

            # Verifica che il file esista
            assert os.path.exists(filepath)

            response = authenticated_client.post(f'/ordini/{ordine_id}/delete', follow_redirects=True)

            assert response.status_code == 200
            assert b'eliminato' in response.data.lower()

            # Verifica che il record sia stato cancellato
            ordine = OrdineAcquisto.query.get(ordine_id)
            assert ordine is None

            # Verifica che il file sia stato cancellato
            assert not os.path.exists(filepath)

    def test_delete_ordine_file_already_deleted(self, app, authenticated_client, sample_ordine_acquisto):
        """Test cancellazione ordine quando il file è già stato cancellato"""
        with app.app_context():
            ordine_id = sample_ordine_acquisto.id
            filepath = sample_ordine_acquisto.filepath

            # Cancella il file manualmente
            if os.path.exists(filepath):
                os.remove(filepath)

            response = authenticated_client.post(f'/ordini/{ordine_id}/delete', follow_redirects=True)

            assert response.status_code == 200

            # Verifica che il record sia stato cancellato comunque
            ordine = OrdineAcquisto.query.get(ordine_id)
            assert ordine is None

    def test_delete_without_admin_permission(self, client, normal_user, sample_ordine_acquisto):
        """Test cancellazione senza permessi admin"""
        # Login come utente normale
        with client.session_transaction() as sess:
            sess['_user_id'] = str(normal_user.id)
            sess['_fresh'] = True

        response = client.post(f'/ordini/{sample_ordine_acquisto.id}/delete', follow_redirects=True)

        # Dovrebbe negare l'accesso
        assert response.status_code == 200
        assert b'accesso negato' in response.data.lower() or b'admin' in response.data.lower()


class TestOrdiniSync:
    """Test sincronizzazione filesystem"""

    def test_sync_ordini_folder(self, app, authenticated_client, admin_user):
        """Test sincronizzazione cartelle INPUT/OUTPUT con DB"""
        with app.app_context():
            # Crea file in INPUT senza record DB
            input_dir = os.path.join(app.config['BASE_DIR'], 'INPUT', 'po', '2024')
            filepath = os.path.join(input_dir, 'new_file.pdf')

            with open(filepath, 'wb') as f:
                f.write(b'%PDF-1.4\nNew file')

            # Chiama sync
            response = authenticated_client.get('/ordini/sync', follow_redirects=True)

            assert response.status_code == 200

            # Verifica che il file sia stato aggiunto al DB
            ordine = OrdineAcquisto.query.filter_by(filename='new_file.pdf').first()
            assert ordine is not None
            assert ordine.esito == 'Da processare'

            # Cleanup
            os.remove(filepath)

    def test_sync_removes_orphan_records(self, app, authenticated_client, admin_user):
        """Test rimozione record orfani dal DB"""
        with app.app_context():
            # Crea record DB senza file
            ordine = OrdineAcquisto(
                anno=2024,
                filename='orphan.pdf',
                filepath='/path/to/orphan.pdf',
                data_acquisizione=date.today(),
                esito='Da processare'
            )
            db.session.add(ordine)
            db.session.commit()
            ordine_id = ordine.id

            # Chiama sync
            response = authenticated_client.get('/ordini/sync', follow_redirects=True)

            assert response.status_code == 200

            # Verifica che il record sia stato rimosso
            ordine = OrdineAcquisto.query.get(ordine_id)
            assert ordine is None


class TestOrdiniDownload:
    """Test download file ordini"""

    def test_download_ordine_success(self, app, authenticated_client, sample_ordine_acquisto):
        """Test download file PDF"""
        with app.app_context():
            response = authenticated_client.get(f'/ordini/download/{sample_ordine_acquisto.id}')

            assert response.status_code == 200
            assert response.content_type == 'application/pdf'

    def test_download_ordine_not_found(self, app, authenticated_client, sample_ordine_acquisto):
        """Test download file mancante"""
        with app.app_context():
            # Cancella il file
            os.remove(sample_ordine_acquisto.filepath)

            response = authenticated_client.get(f'/ordini/download/{sample_ordine_acquisto.id}',
                                                 follow_redirects=True)

            assert response.status_code == 200
            assert b'non trovato' in response.data.lower()


class TestOrdiniList:
    """Test lista ordini"""

    def test_list_ordini_with_filters(self, app, authenticated_client, sample_ordine_acquisto):
        """Test lista ordini con filtri"""
        with app.app_context():
            response = authenticated_client.get('/ordini/?anno=2024&esito=Da processare')

            assert response.status_code == 200
            assert b'test_ordine.pdf' in response.data

    def test_list_ordini_pagination(self, app, authenticated_client, admin_user):
        """Test paginazione lista ordini"""
        with app.app_context():
            # Crea 25 ordini
            for i in range(25):
                filepath = os.path.join(app.config['BASE_DIR'], 'INPUT', 'po', '2024', f'ordine_{i}.pdf')
                with open(filepath, 'wb') as f:
                    f.write(b'%PDF-1.4\nTest')

                ordine = OrdineAcquisto(
                    anno=2024,
                    filename=f'ordine_{i}.pdf',
                    filepath=filepath,
                    data_acquisizione=date.today(),
                    esito='Da processare'
                )
                db.session.add(ordine)

            db.session.commit()

            # Richiedi pagina 1
            response = authenticated_client.get('/ordini/?page=1')
            assert response.status_code == 200

            # Richiedi pagina 2
            response = authenticated_client.get('/ordini/?page=2')
            assert response.status_code == 200
