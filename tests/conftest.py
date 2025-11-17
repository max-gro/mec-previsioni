"""
Fixtures pytest per test suite MEC Previsioni
"""
import os
import pytest
import tempfile
import shutil
from datetime import date, datetime
from io import BytesIO

from app import create_app
from models import db, User, OrdineAcquisto, AnagraficaFile, Modello, Componente, ModelloComponente


@pytest.fixture(scope='session')
def app():
    """Crea app Flask per testing"""
    app = create_app()
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'WTF_CSRF_ENABLED': False,  # Disabilita CSRF per i test
        'SECRET_KEY': 'test-secret-key'
    })

    # Crea directory temporanee per INPUT/OUTPUT
    app.config['BASE_DIR'] = tempfile.mkdtemp()
    app.config['UPLOAD_FOLDER'] = os.path.join(app.config['BASE_DIR'], 'INPUT', 'po')

    # Crea le directory necessarie
    os.makedirs(os.path.join(app.config['BASE_DIR'], 'INPUT', 'po', '2024'), exist_ok=True)
    os.makedirs(os.path.join(app.config['BASE_DIR'], 'OUTPUT', 'po', '2024'), exist_ok=True)
    os.makedirs(os.path.join(app.config['BASE_DIR'], 'INPUT', 'anagrafiche', 'HISENSE'), exist_ok=True)
    os.makedirs(os.path.join(app.config['BASE_DIR'], 'OUTPUT', 'anagrafiche', 'HISENSE'), exist_ok=True)

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

    # Cleanup directory temporanee
    shutil.rmtree(app.config['BASE_DIR'], ignore_errors=True)


@pytest.fixture
def client(app):
    """Client Flask per testing"""
    return app.test_client()


@pytest.fixture
def runner(app):
    """CLI runner per testing"""
    return app.test_cli_runner()


@pytest.fixture
def db_session(app):
    """Sessione DB per testing con rollback automatico"""
    with app.app_context():
        # Crea un savepoint
        connection = db.engine.connect()
        transaction = connection.begin()

        # Bind sessione alla connessione
        options = dict(bind=connection, binds={})
        session = db.create_scoped_session(options=options)
        db.session = session

        yield session

        # Rollback alla fine del test
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def admin_user(app):
    """Crea utente admin di test"""
    with app.app_context():
        user = User(
            username='admin_test',
            email='admin@test.com',
            role='admin',
            active=True
        )
        user.set_password('admin123')
        db.session.add(user)
        db.session.commit()
        return user


@pytest.fixture
def normal_user(app):
    """Crea utente normale di test"""
    with app.app_context():
        user = User(
            username='user_test',
            email='user@test.com',
            role='user',
            active=True
        )
        user.set_password('user123')
        db.session.add(user)
        db.session.commit()
        return user


@pytest.fixture
def authenticated_client(client, admin_user):
    """Client autenticato come admin"""
    with client.session_transaction() as sess:
        sess['_user_id'] = str(admin_user.id)
        sess['_fresh'] = True
    return client


@pytest.fixture
def sample_pdf_file():
    """Crea un file PDF di test (fake)"""
    pdf_content = b'%PDF-1.4\nFake PDF content for testing'
    return BytesIO(pdf_content), 'test_ordine_2024.pdf'


@pytest.fixture
def sample_excel_file():
    """Crea un file Excel di test con dati anagrafica"""
    import pandas as pd

    data = {
        'file': ['anagrafica HISENSE 2024'] * 3,
        'anno': [2024] * 3,
        'modello': ['SWMH127S', 'SWMH127S', 'SWMH128S'],
        'modello fabbrica': ['WFMC7012-JUW001', 'WFMC7012-JUW001', 'WFMC7013-JUW002'],
        'M&C code': ['H2128148', 'H2128149', 'H2128150'],
        'qtà': [1, 2, 1],
        'pos number': ['T122', 'T123', 'T124'],
        'part no': ['2128148', '2128149', '2128150'],
        'alt code': ['H2128148', 'H2128149', 'H2128150'],
        'alt code 2': ['', '', ''],
        'ean code': ['', '', ''],
        'barcode': ['1', 'N', 'Q'],
        'part name': ['Motor', 'Pump', 'Belt'],
        'chinese name': ['电机', '泵', '皮带'],
        'descr ita': ['MOTORE', 'POMPA', 'CINGHIA'],
        'unit price usd': [48.60, 32.50, 12.80],
        'prezzo EURO al CAT NO trasporto - NO iva - NETTO': [76.90, 51.20, 20.30],
        'prezzo EURO al CAT con trasporto - NO iva - NETTO': [82.90, 55.40, 22.10],
        'prezzo EURO al PUBBLICO (suggerito) con IVA': [144.00, 96.00, 38.40],
        'stat': ['L0', 'M1', 'L0'],
        'softech stat': ['L0', 'M1', 'L0']
    }

    df = pd.DataFrame(data)
    excel_buffer = BytesIO()
    df.to_excel(excel_buffer, index=False, engine='openpyxl')
    excel_buffer.seek(0)

    return excel_buffer, 'anagrafica_HISENSE_2024.xlsx'


@pytest.fixture
def sample_ordine_acquisto(app, admin_user):
    """Crea un ordine di acquisto di test nel DB"""
    with app.app_context():
        filepath = os.path.join(app.config['BASE_DIR'], 'INPUT', 'po', '2024', 'test_ordine.pdf')

        # Crea file fake
        with open(filepath, 'wb') as f:
            f.write(b'%PDF-1.4\nFake PDF')

        ordine = OrdineAcquisto(
            anno=2024,
            filename='test_ordine.pdf',
            filepath=filepath,
            data_acquisizione=date.today(),
            esito='Da processare',
            note='Test ordine'
        )
        db.session.add(ordine)
        db.session.commit()

        return ordine


@pytest.fixture
def sample_anagrafica_file(app, admin_user):
    """Crea un file anagrafica di test nel DB"""
    with app.app_context():
        filepath = os.path.join(app.config['BASE_DIR'], 'INPUT', 'anagrafiche', 'HISENSE', 'test_anagrafica.xlsx')

        # Crea file Excel fake con dati validi
        import pandas as pd
        data = {
            'file': ['anagrafica HISENSE 2024'],
            'anno': [2024],
            'modello': ['SWMH127S'],
            'modello fabbrica': ['WFMC7012-JUW001'],
            'M&C code': ['H2128148'],
            'qtà': [1],
            'pos number': ['T122'],
            'part no': ['2128148'],
            'alt code': ['H2128148'],
            'alt code 2': [''],
            'ean code': [''],
            'barcode': ['1'],
            'part name': ['Motor'],
            'chinese name': ['电机'],
            'descr ita': ['MOTORE'],
            'unit price usd': [48.60],
            'prezzo EURO al CAT NO trasporto - NO iva - NETTO': [76.90],
            'prezzo EURO al CAT con trasporto - NO iva - NETTO': [82.90],
            'prezzo EURO al PUBBLICO (suggerito) con IVA': [144.00],
            'stat': ['L0'],
            'softech stat': ['L0']
        }
        df = pd.DataFrame(data)
        df.to_excel(filepath, index=False, engine='openpyxl')

        anagrafica = AnagraficaFile(
            anno=2024,
            marca='HISENSE',
            filename='test_anagrafica.xlsx',
            filepath=filepath,
            data_acquisizione=date.today(),
            esito='Da processare',
            note='Test anagrafica',
            created_by='admin_test',
            updated_by='admin_test'
        )
        db.session.add(anagrafica)
        db.session.commit()

        return anagrafica


@pytest.fixture
def sample_modello(app):
    """Crea un modello di test nel DB"""
    with app.app_context():
        modello = Modello(
            cod_modello='SWMH127S',
            cod_modello_norm='swmh127s',
            cod_modello_fabbrica='WFMC7012-JUW001',
            created_at=datetime.utcnow(),
            created_by='test',
            updated_at=datetime.utcnow(),
            updated_by='test',
            updated_from='ana'
        )
        db.session.add(modello)
        db.session.commit()
        return modello


@pytest.fixture
def sample_componente(app):
    """Crea un componente di test nel DB"""
    with app.app_context():
        componente = Componente(
            cod_componente='H2128148',
            cod_componente_norm='h2128148',
            desc_componente_it='MOTORE',
            part_name_en='Motor',
            part_name_cn='电机',
            part_name_it='MOTORE',
            pos_no='T122',
            part_no='2128148',
            barcode='1',
            unit_price_usd=48.60,
            unit_price_public_eur=144.00,
            stat='L0',
            softech_stat='L0',
            created_at=datetime.utcnow(),
            created_by='test',
            updated_at=datetime.utcnow(),
            updated_by='test'
        )
        db.session.add(componente)
        db.session.commit()
        return componente
