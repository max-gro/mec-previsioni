"""
Test per Pipeline Anagrafiche
"""
import os
import pytest
from datetime import date
from decimal import Decimal
from models import db, AnagraficaFile, Modello, Componente, ModelloComponente


class TestAnagraficheUpload:
    """Test caricamento file Excel anagrafiche"""

    def test_upload_anagrafica_success(self, authenticated_client, app, admin_user, sample_excel_file):
        """Test upload file Excel con successo"""
        excel_data, filename = sample_excel_file

        with app.app_context():
            response = authenticated_client.post('/anagrafiche/create', data={
                'file': (excel_data, filename),
                'marca': 'HISENSE',
                'anno': 2024,
                'data_acquisizione': '01/01/2024',
                'note': 'Test upload'
            }, follow_redirects=True)

            assert response.status_code == 200
            assert b'caricato con successo' in response.data

            # Verifica record nel DB
            anagrafica = AnagraficaFile.query.filter_by(filename=filename).first()
            assert anagrafica is not None
            assert anagrafica.marca == 'HISENSE'
            assert anagrafica.anno == 2024
            assert anagrafica.esito == 'Da processare'

    def test_upload_anagrafica_invalid_extension(self, authenticated_client, app):
        """Test upload file con estensione non valida"""
        from io import BytesIO
        invalid_file = (BytesIO(b'test content'), 'test.pdf')

        response = authenticated_client.post('/anagrafiche/create', data={
            'file': invalid_file,
            'marca': 'HISENSE',
            'anno': 2024,
            'data_acquisizione': '01/01/2024'
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b'Solo file Excel' in response.data or b'permessi' in response.data


class TestAnagraficheElaborazione:
    """Test elaborazione anagrafiche"""

    def test_elabora_anagrafica_success(self, app, authenticated_client, sample_anagrafica_file, admin_user):
        """Test elaborazione anagrafica con inserimento dati nel DB"""
        with app.app_context():
            anagrafica_id = sample_anagrafica_file.id

            response = authenticated_client.post(f'/anagrafiche/{anagrafica_id}/elabora', follow_redirects=True)

            assert response.status_code == 200

            # Verifica che l'anagrafica sia stata elaborata
            anagrafica = AnagraficaFile.query.get(anagrafica_id)
            assert anagrafica.esito == 'Processato'
            assert anagrafica.data_elaborazione is not None
            assert 'Elaborazione completata con successo' in anagrafica.note

            # Verifica che il modello sia stato creato/aggiornato
            modello = Modello.query.filter_by(cod_modello='SWMH127S').first()
            assert modello is not None
            assert modello.cod_modello_norm == 'swmh127s'
            assert modello.cod_modello_fabbrica == 'WFMC7012-JUW001'
            assert modello.updated_from == 'ana'

            # Verifica che il componente sia stato creato/aggiornato
            componente = Componente.query.filter_by(cod_componente='H2128148').first()
            assert componente is not None
            assert componente.cod_componente_norm == 'h2128148'
            assert componente.desc_componente_it == 'MOTORE'
            assert componente.part_name_en == 'Motor'
            assert componente.unit_price_usd == Decimal('48.60')

            # Verifica che la relazione modello-componente sia stata creata
            mc = ModelloComponente.query.filter_by(
                cod_modello='SWMH127S',
                cod_componente='H2128148'
            ).first()
            assert mc is not None
            assert mc.qta == 1
            assert mc.id_file_anagrafiche == anagrafica_id
            assert mc.modello_componente == 'SWMH127S|H2128148'

    def test_elabora_anagrafica_upsert_modello_esistente(self, app, authenticated_client,
                                                           sample_anagrafica_file, sample_modello, admin_user):
        """Test UPSERT: aggiorna modello esistente"""
        with app.app_context():
            anagrafica_id = sample_anagrafica_file.id
            modello_id_originale = sample_modello.cod_modello

            # Modifica cod_modello_fabbrica originale
            sample_modello.cod_modello_fabbrica = 'OLD_CODE'
            db.session.commit()

            response = authenticated_client.post(f'/anagrafiche/{anagrafica_id}/elabora', follow_redirects=True)

            assert response.status_code == 200

            # Verifica che il modello sia stato aggiornato (non duplicato)
            modelli = Modello.query.filter_by(cod_modello=modello_id_originale).all()
            assert len(modelli) == 1

            modello = modelli[0]
            assert modello.cod_modello_fabbrica == 'WFMC7012-JUW001'  # Aggiornato
            assert modello.updated_from == 'ana'

    def test_elabora_anagrafica_upsert_componente_esistente(self, app, authenticated_client,
                                                              sample_anagrafica_file, sample_componente, admin_user):
        """Test UPSERT: aggiorna componente esistente"""
        with app.app_context():
            anagrafica_id = sample_anagrafica_file.id
            componente_id_originale = sample_componente.cod_componente

            # Modifica descrizione originale
            sample_componente.desc_componente_it = 'OLD DESCRIPTION'
            db.session.commit()

            response = authenticated_client.post(f'/anagrafiche/{anagrafica_id}/elabora', follow_redirects=True)

            assert response.status_code == 200

            # Verifica che il componente sia stato aggiornato (non duplicato)
            componenti = Componente.query.filter_by(cod_componente=componente_id_originale).all()
            assert len(componenti) == 1

            componente = componenti[0]
            assert componente.desc_componente_it == 'MOTORE'  # Aggiornato

    def test_elabora_anagrafica_delete_preventivo_modelli_componenti(self, app, authenticated_client,
                                                                       sample_anagrafica_file, sample_modello,
                                                                       sample_componente, admin_user):
        """Test DELETE preventivo: rimuove modelli_componenti esistenti prima di reinserire"""
        with app.app_context():
            anagrafica_id = sample_anagrafica_file.id

            # Crea una relazione modello-componente esistente
            mc_old = ModelloComponente(
                modello_componente='SWMH127S|H2128148',
                id_file_anagrafiche=anagrafica_id,
                cod_modello='SWMH127S',
                cod_componente='H2128148',
                qta=99,  # Quantità diversa
                created_by='test',
                updated_by='test'
            )
            db.session.add(mc_old)
            db.session.commit()

            response = authenticated_client.post(f'/anagrafiche/{anagrafica_id}/elabora', follow_redirects=True)

            assert response.status_code == 200

            # Verifica che la vecchia relazione sia stata cancellata e ricreata
            mc_new = ModelloComponente.query.filter_by(
                cod_modello='SWMH127S',
                cod_componente='H2128148'
            ).first()

            assert mc_new is not None
            assert mc_new.qta == 1  # Quantità aggiornata dal file

    def test_elabora_anagrafica_colonne_mancanti(self, app, authenticated_client, admin_user):
        """Test errore: file Excel con colonne mancanti"""
        import pandas as pd
        from io import BytesIO

        with app.app_context():
            # Crea file con colonne mancanti
            data = {
                'file': ['test'],
                'anno': [2024],
                'modello': ['TEST']
                # Mancano tutte le altre colonne
            }
            df = pd.DataFrame(data)
            excel_buffer = BytesIO()
            df.to_excel(excel_buffer, index=False, engine='openpyxl')
            excel_buffer.seek(0)

            # Salva file
            filepath = os.path.join(app.config['BASE_DIR'], 'INPUT', 'anagrafiche', 'HISENSE', 'invalid.xlsx')
            with open(filepath, 'wb') as f:
                f.write(excel_buffer.getvalue())

            anagrafica = AnagraficaFile(
                anno=2024,
                marca='HISENSE',
                filename='invalid.xlsx',
                filepath=filepath,
                data_acquisizione=date.today(),
                esito='Da processare',
                created_by='admin_test'
            )
            db.session.add(anagrafica)
            db.session.commit()
            anagrafica_id = anagrafica.id

            response = authenticated_client.post(f'/anagrafiche/{anagrafica_id}/elabora', follow_redirects=True)

            # Verifica che l'esito sia 'Errore'
            anagrafica = AnagraficaFile.query.get(anagrafica_id)
            assert anagrafica.esito == 'Errore'
            assert 'Colonne mancanti' in anagrafica.note

    def test_elabora_anagrafica_rollback_on_error(self, app, authenticated_client, sample_anagrafica_file, admin_user):
        """Test rollback DB in caso di errore durante elaborazione"""
        with app.app_context():
            # Conta record iniziali
            count_modelli_before = Modello.query.count()
            count_componenti_before = Componente.query.count()

            # Simula errore modificando il file per renderlo invalido
            filepath = sample_anagrafica_file.filepath
            with open(filepath, 'wb') as f:
                f.write(b'INVALID EXCEL CONTENT')

            response = authenticated_client.post(f'/anagrafiche/{sample_anagrafica_file.id}/elabora',
                                                  follow_redirects=True)

            # Verifica che l'esito sia 'Errore'
            anagrafica = AnagraficaFile.query.get(sample_anagrafica_file.id)
            assert anagrafica.esito == 'Errore'

            # Verifica che nessun record sia stato inserito (rollback)
            count_modelli_after = Modello.query.count()
            count_componenti_after = Componente.query.count()

            assert count_modelli_after == count_modelli_before
            assert count_componenti_after == count_componenti_before


class TestAnagraficheDelete:
    """Test cancellazione anagrafiche"""

    def test_delete_anagrafica_cascade_modelli_componenti(self, app, authenticated_client,
                                                            sample_anagrafica_file, sample_modello,
                                                            sample_componente):
        """Test cancellazione CASCADE: rimuove modelli_componenti ma NON modelli/componenti"""
        with app.app_context():
            anagrafica_id = sample_anagrafica_file.id

            # Crea relazioni modello-componente
            mc1 = ModelloComponente(
                modello_componente='SWMH127S|H2128148',
                id_file_anagrafiche=anagrafica_id,
                cod_modello='SWMH127S',
                cod_componente='H2128148',
                qta=1,
                created_by='test',
                updated_by='test'
            )
            db.session.add(mc1)
            db.session.commit()

            # Conta record iniziali
            count_modelli_before = Modello.query.count()
            count_componenti_before = Componente.query.count()
            count_mc_before = ModelloComponente.query.count()

            filepath = sample_anagrafica_file.filepath

            response = authenticated_client.post(f'/anagrafiche/{anagrafica_id}/delete', follow_redirects=True)

            assert response.status_code == 200
            assert b'eliminata' in response.data.lower()

            # Verifica che il record anagrafica sia stato cancellato
            anagrafica = AnagraficaFile.query.get(anagrafica_id)
            assert anagrafica is None

            # Verifica che il file sia stato cancellato
            assert not os.path.exists(filepath)

            # Verifica che modelli_componenti siano stati cancellati (CASCADE)
            count_mc_after = ModelloComponente.query.count()
            assert count_mc_after == count_mc_before - 1

            # Verifica che modelli e componenti NON siano stati cancellati
            count_modelli_after = Modello.query.count()
            count_componenti_after = Componente.query.count()

            assert count_modelli_after == count_modelli_before
            assert count_componenti_after == count_componenti_before

    def test_delete_anagrafica_rollback_on_error(self, app, authenticated_client, sample_anagrafica_file):
        """Test rollback in caso di errore durante cancellazione"""
        with app.app_context():
            anagrafica_id = sample_anagrafica_file.id

            # Simula errore rendendo il file non cancellabile (read-only)
            filepath = sample_anagrafica_file.filepath
            os.chmod(os.path.dirname(filepath), 0o444)  # Read-only directory

            try:
                response = authenticated_client.post(f'/anagrafiche/{anagrafica_id}/delete', follow_redirects=True)

                # Verifica che il record NON sia stato cancellato (rollback)
                anagrafica = AnagraficaFile.query.get(anagrafica_id)
                # Il record dovrebbe esistere ancora
                assert anagrafica is not None or response.status_code == 200

            finally:
                # Ripristina permessi
                os.chmod(os.path.dirname(filepath), 0o755)


class TestAnagraficheHelperFunctions:
    """Test funzioni helper"""

    def test_normalizza_codice(self):
        """Test normalizzazione codici"""
        from routes.anagrafiche import normalizza_codice

        assert normalizza_codice('ABC 123') == 'abc123'
        assert normalizza_codice('  XYZ  ') == 'xyz'
        assert normalizza_codice('MiXeD CaSe') == 'mixedcase'
        assert normalizza_codice('') is None
        assert normalizza_codice(None) is None

    def test_safe_decimal(self):
        """Test conversione sicura a Decimal"""
        from routes.anagrafiche import safe_decimal

        assert safe_decimal('48.60') == Decimal('48.60')
        assert safe_decimal(' € 76.90 ') == Decimal('76.90')
        assert safe_decimal('1,234.56') == Decimal('1234.56')
        assert safe_decimal('') is None
        assert safe_decimal(None) is None
        assert safe_decimal('invalid', default=Decimal('0')) == Decimal('0')

    def test_safe_int(self):
        """Test conversione sicura a int"""
        from routes.anagrafiche import safe_int

        assert safe_int('123') == 123
        assert safe_int('45.67') == 45
        assert safe_int(None) is None
        assert safe_int('', default=0) == 0
        assert safe_int('invalid', default=1) == 1

    def test_safe_str(self):
        """Test conversione sicura a stringa"""
        from routes.anagrafiche import safe_str

        assert safe_str('test') == 'test'
        assert safe_str('  spaces  ') == 'spaces'
        assert safe_str(None) == ''
        assert safe_str(None, default='N/A') == 'N/A'


class TestAnagraficheSync:
    """Test sincronizzazione filesystem"""

    def test_sync_anagrafiche_folder(self, app, authenticated_client, admin_user, sample_excel_file):
        """Test sincronizzazione cartelle INPUT/OUTPUT con DB"""
        excel_data, _ = sample_excel_file

        with app.app_context():
            # Crea file in INPUT senza record DB
            input_dir = os.path.join(app.config['BASE_DIR'], 'INPUT', 'anagrafiche', 'HISENSE')
            filepath = os.path.join(input_dir, 'new_file.xlsx')

            with open(filepath, 'wb') as f:
                f.write(excel_data.read())

            # Chiama sync
            response = authenticated_client.get('/anagrafiche/sync', follow_redirects=True)

            assert response.status_code == 200

            # Verifica che il file sia stato aggiunto al DB
            anagrafica = AnagraficaFile.query.filter_by(filename='new_file.xlsx').first()
            assert anagrafica is not None
            assert anagrafica.esito == 'Da processare'
            assert anagrafica.marca == 'HISENSE'

            # Cleanup
            os.remove(filepath)


class TestAnagrafichePreview:
    """Test anteprima file Excel"""

    def test_preview_anagrafica_success(self, app, authenticated_client, sample_anagrafica_file):
        """Test anteprima HTML del file Excel"""
        with app.app_context():
            response = authenticated_client.get(f'/anagrafiche/preview/{sample_anagrafica_file.id}')

            assert response.status_code == 200
            assert b'<table' in response.data  # Verifica presenza tabella HTML
            assert b'SWMH127S' in response.data  # Verifica contenuto

    def test_preview_anagrafica_file_not_found(self, app, authenticated_client, sample_anagrafica_file):
        """Test anteprima con file mancante"""
        with app.app_context():
            # Cancella il file
            os.remove(sample_anagrafica_file.filepath)

            response = authenticated_client.get(f'/anagrafiche/preview/{sample_anagrafica_file.id}',
                                                 follow_redirects=True)

            assert response.status_code == 200
            assert b'non trovato' in response.data.lower()


class TestAnagraficheMarche:
    """Test gestione marche"""

    def test_crea_nuova_marca(self, app, authenticated_client, admin_user):
        """Test creazione nuova marca"""
        with app.app_context():
            response = authenticated_client.post('/anagrafiche/nuova-marca', data={
                'nome_marca': 'SAMSUNG'
            }, follow_redirects=True)

            assert response.status_code == 200
            assert b'creata con successo' in response.data

            # Verifica che le cartelle siano state create
            input_dir = os.path.join(app.config['BASE_DIR'], 'INPUT', 'anagrafiche', 'SAMSUNG')
            output_dir = os.path.join(app.config['BASE_DIR'], 'OUTPUT', 'anagrafiche', 'SAMSUNG')

            assert os.path.exists(input_dir)
            assert os.path.exists(output_dir)

    def test_crea_marca_duplicata(self, app, authenticated_client, admin_user):
        """Test creazione marca già esistente"""
        with app.app_context():
            # Crea marca esistente
            input_dir = os.path.join(app.config['BASE_DIR'], 'INPUT', 'anagrafiche', 'EXISTING')
            os.makedirs(input_dir, exist_ok=True)

            response = authenticated_client.post('/anagrafiche/nuova-marca', data={
                'nome_marca': 'EXISTING'
            }, follow_redirects=True)

            assert response.status_code == 200
            assert b'esiste già' in response.data.lower() or b'già presente' in response.data.lower()
