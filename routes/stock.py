"""
Blueprint per la gestione Stock (CRUD + Upload TSV + Elaborazione)

Pipeline Stock:
- Upload file TSV con giacenze componenti
- Parsing e validazione
- Inserimento in DB (file_stock + stock)
- Gestione file (INPUT/OUTPUT)
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from models import db, FileStock, Stock, Componente
from utils.decorators import admin_required
import os
import csv
import re
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

stock_bp = Blueprint('stock', __name__, url_prefix='/stock')


def extract_year_from_filename(filename):
    """Estrae l'anno dal nome del file (es. stock_2024-11-01.tsv -> 2024)"""
    match = re.search(r'(20\d{2})', filename)
    if match:
        return int(match.group(1))
    return datetime.now().year


def get_upload_path(anno, esito='Da processare'):
    """
    Restituisce il path di upload per un determinato anno
    Struttura: INPUT/stock/anno/ o OUTPUT/stock/anno/
    """
    base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

    if esito == 'Processato':
        upload_dir = os.path.join(base_dir, 'OUTPUT', 'stock', str(anno))
    else:
        upload_dir = os.path.join(base_dir, 'INPUT', 'stock', str(anno))

    os.makedirs(upload_dir, exist_ok=True)
    return upload_dir


@stock_bp.route('/')
@login_required
def index():
    """Lista file stock caricati con filtri"""

    # Filtri
    anno = request.args.get('anno', type=int)
    esito = request.args.get('esito', '')
    sort = request.args.get('sort', 'id')
    order = request.args.get('order', 'desc')

    # Query base
    query = FileStock.query

    # Applica filtri
    if anno:
        query = query.filter(FileStock.anno == anno)
    if esito:
        query = query.filter(FileStock.esito == esito)

    # Ordinamento
    if sort == 'anno':
        query = query.order_by(FileStock.anno.desc() if order == 'desc' else FileStock.anno.asc())
    elif sort == 'filename':
        query = query.order_by(FileStock.filename.desc() if order == 'desc' else FileStock.filename.asc())
    elif sort == 'esito':
        query = query.order_by(FileStock.esito.desc() if order == 'desc' else FileStock.esito.asc())
    elif sort == 'data_acquisizione':
        query = query.order_by(FileStock.data_acquisizione.desc() if order == 'desc' else FileStock.data_acquisizione.asc())
    else:
        query = query.order_by(FileStock.id.desc() if order == 'desc' else FileStock.id.asc())

    file_stock_list = query.all()

    # Arricchisci con conteggio righe
    for file in file_stock_list:
        file.n_righe = Stock.query.filter_by(id_file_stock=file.id).count()

    # Valori dropdown filtri
    anni_disponibili = db.session.query(FileStock.anno).distinct().order_by(FileStock.anno.desc()).all()
    anni_disponibili = [a[0] for a in anni_disponibili]

    esiti_disponibili = ['Da processare', 'Processato', 'Errore']

    return render_template(
        'stock/index.html',
        file_stock_list=file_stock_list,
        anni_disponibili=anni_disponibili,
        esiti_disponibili=esiti_disponibili,
        anno=anno,
        esito=esito,
        sort=sort,
        order=order
    )


@stock_bp.route('/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create():
    """Upload nuovo file stock TSV"""

    if request.method == 'POST':
        # Verifica file
        if 'file' not in request.files:
            flash('Nessun file selezionato', 'error')
            return redirect(url_for('stock.create'))

        file = request.files['file']

        if file.filename == '':
            flash('Nessun file selezionato', 'error')
            return redirect(url_for('stock.create'))

        # Valida estensione
        if not file.filename.lower().endswith(('.tsv', '.txt')):
            flash('Formato file non valido. Carica un file TSV (.tsv o .txt)', 'error')
            return redirect(url_for('stock.create'))

        try:
            # Salva file
            filename = secure_filename(file.filename)
            anno = extract_year_from_filename(filename)
            upload_dir = get_upload_path(anno, 'Da processare')
            filepath = os.path.join(upload_dir, filename)

            # Verifica duplicati
            existing = FileStock.query.filter_by(filename=filename).first()
            if existing:
                flash(f'File già esistente: {filename}', 'error')
                return redirect(url_for('stock.create'))

            file.save(filepath)

            # Crea record DB
            nuovo_file = FileStock(
                anno=anno,
                filename=filename,
                filepath=filepath,
                data_acquisizione=datetime.now(),
                esito='Da processare',
                created_by=current_user.id
            )

            db.session.add(nuovo_file)
            db.session.commit()

            flash(f'File {filename} caricato con successo', 'success')
            return redirect(url_for('stock.index'))

        except Exception as e:
            db.session.rollback()
            logger.error(f"Errore upload file stock: {e}")
            flash(f'Errore durante il caricamento: {str(e)}', 'error')
            return redirect(url_for('stock.create'))

    return render_template('stock/create.html')


@stock_bp.route('/elabora/<int:id>')
@login_required
@admin_required
def elabora(id):
    """Elabora file stock TSV"""

    file_stock = FileStock.query.get_or_404(id)

    if file_stock.esito == 'Processato':
        flash('File già elaborato', 'warning')
        return redirect(url_for('stock.index'))

    try:
        # Verifica esistenza file
        if not os.path.exists(file_stock.filepath):
            flash(f'File non trovato: {file_stock.filepath}', 'error')
            file_stock.esito = 'Errore'
            file_stock.note = 'File non trovato sul filesystem'
            db.session.commit()
            return redirect(url_for('stock.index'))

        # Parse TSV
        righe_ok = 0
        righe_errore = 0
        errori = []

        with open(file_stock.filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter='\t')

            for idx, row in enumerate(reader, 1):
                try:
                    # Validazione campi obbligatori
                    cod_componente = row.get('cod_componente', '').strip()
                    data_snapshot_str = row.get('data_snapshot', '').strip()

                    if not cod_componente:
                        errori.append(f"Riga {idx}: cod_componente mancante")
                        righe_errore += 1
                        continue

                    if not data_snapshot_str:
                        errori.append(f"Riga {idx}: data_snapshot mancante")
                        righe_errore += 1
                        continue

                    # Parse giacenze (obbligatorie)
                    try:
                        giacenza_disponibile = int(row.get('giacenza_disponibile', '0'))
                        giacenza_impegnata = int(row.get('giacenza_impegnata', '0'))
                        giacenza_fisica = int(row.get('giacenza_fisica', '0'))
                    except ValueError as e:
                        errori.append(f"Riga {idx}: giacenza non valida - {str(e)}")
                        righe_errore += 1
                        continue

                    # Parse soglie (opzionali)
                    try:
                        scorta_minima = int(row.get('scorta_minima')) if row.get('scorta_minima', '').strip() else None
                        scorta_massima = int(row.get('scorta_massima')) if row.get('scorta_massima', '').strip() else None
                        punto_riordino = int(row.get('punto_riordino')) if row.get('punto_riordino', '').strip() else None
                        lead_time_days = int(row.get('lead_time_days')) if row.get('lead_time_days', '').strip() else None
                    except ValueError as e:
                        errori.append(f"Riga {idx}: soglie non valide - {str(e)}")
                        righe_errore += 1
                        continue

                    # Parse date
                    try:
                        # data_snapshot può essere YYYY-MM-DD HH:MM:SS o solo YYYY-MM-DD
                        if ' ' in data_snapshot_str:
                            data_snapshot = datetime.strptime(data_snapshot_str, '%Y-%m-%d %H:%M:%S')
                        else:
                            data_snapshot = datetime.strptime(data_snapshot_str, '%Y-%m-%d')
                    except ValueError:
                        errori.append(f"Riga {idx}: data_snapshot non valida '{data_snapshot_str}'")
                        righe_errore += 1
                        continue

                    # Parse data_stock (opzionale)
                    data_stock = None
                    data_stock_str = row.get('data_stock', '').strip()
                    if data_stock_str:
                        try:
                            if ' ' in data_stock_str:
                                data_stock = datetime.strptime(data_stock_str, '%Y-%m-%d %H:%M:%S')
                            else:
                                data_stock = datetime.strptime(data_stock_str, '%Y-%m-%d')
                        except ValueError:
                            pass  # Ignora se non valida

                    # Parse flag_corrente
                    flag_corrente_str = row.get('flag_corrente', 'FALSE').strip().upper()
                    flag_corrente = flag_corrente_str in ('TRUE', 'T', '1', 'YES')

                    # Verifica se componente esiste (opzionale - crea se non esiste)
                    componente = Componente.query.filter_by(cod_componente=cod_componente).first()
                    if not componente:
                        # Crea componente placeholder
                        componente = Componente(
                            cod_componente=cod_componente,
                            cod_componente_norm=cod_componente.upper(),
                            componente_it=f"Componente {cod_componente}",
                            created_by=current_user.id
                        )
                        db.session.add(componente)

                    # Crea record stock
                    stock_record = Stock(
                        id_file_stock=file_stock.id,
                        cod_componente=cod_componente,
                        warehouse=row.get('warehouse', '').strip() or None,
                        ubicazione=row.get('ubicazione', '').strip() or None,
                        lotto=row.get('lotto', '').strip() or None,
                        giacenza_disponibile=giacenza_disponibile,
                        giacenza_impegnata=giacenza_impegnata,
                        giacenza_fisica=giacenza_fisica,
                        scorta_minima=scorta_minima,
                        scorta_massima=scorta_massima,
                        punto_riordino=punto_riordino,
                        lead_time_days=lead_time_days,
                        data_snapshot=data_snapshot,
                        data_stock=data_stock,
                        flag_corrente=flag_corrente,
                        created_by=current_user.id
                    )

                    db.session.add(stock_record)
                    righe_ok += 1

                except Exception as e:
                    errori.append(f"Riga {idx}: {str(e)}")
                    righe_errore += 1
                    continue

        # Aggiorna file_stock
        if righe_errore == 0:
            file_stock.esito = 'Processato'
            file_stock.note = f'Elaborato con successo: {righe_ok} righe'

            # Sposta file in OUTPUT
            output_dir = get_upload_path(file_stock.anno, 'Processato')
            new_filepath = os.path.join(output_dir, file_stock.filename)

            if os.path.exists(file_stock.filepath):
                os.rename(file_stock.filepath, new_filepath)
                file_stock.filepath = new_filepath
        else:
            file_stock.esito = 'Errore'
            file_stock.note = f'Elaborato con errori: {righe_ok} OK, {righe_errore} KO. Errori: ' + '; '.join(errori[:5])

        file_stock.data_elaborazione = datetime.now()
        file_stock.updated_by = current_user.id
        file_stock.updated_at = datetime.now()

        db.session.commit()

        if righe_errore == 0:
            flash(f'File elaborato con successo: {righe_ok} righe importate', 'success')
        else:
            flash(f'File elaborato con errori: {righe_ok} OK, {righe_errore} KO', 'warning')

    except Exception as e:
        db.session.rollback()
        logger.error(f"Errore elaborazione file stock {id}: {e}")
        file_stock.esito = 'Errore'
        file_stock.note = f'Errore elaborazione: {str(e)}'
        file_stock.data_elaborazione = datetime.now()
        db.session.commit()
        flash(f'Errore durante elaborazione: {str(e)}', 'error')

    return redirect(url_for('stock.index'))


@stock_bp.route('/delete/<int:id>')
@login_required
@admin_required
def delete(id):
    """Elimina file stock e righe associate"""

    file_stock = FileStock.query.get_or_404(id)

    try:
        # Elimina righe stock associate
        Stock.query.filter_by(id_file_stock=id).delete()

        # Elimina file fisico se esiste
        if os.path.exists(file_stock.filepath):
            os.remove(file_stock.filepath)

        # Elimina record DB
        db.session.delete(file_stock)
        db.session.commit()

        flash(f'File {file_stock.filename} eliminato con successo', 'success')

    except Exception as e:
        db.session.rollback()
        logger.error(f"Errore eliminazione file stock {id}: {e}")
        flash(f'Errore durante eliminazione: {str(e)}', 'error')

    return redirect(url_for('stock.index'))


@stock_bp.route('/dettaglio/<int:id>')
@login_required
def dettaglio(id):
    """Visualizza dettaglio file stock con righe"""

    file_stock = FileStock.query.get_or_404(id)

    # Query righe stock con join componente
    righe = db.session.query(
        Stock,
        Componente
    ).outerjoin(
        Componente, Stock.cod_componente == Componente.cod_componente
    ).filter(
        Stock.id_file_stock == id
    ).order_by(
        Stock.cod_componente
    ).all()

    # Statistiche
    totale_righe = len(righe)
    totale_qta = sum(r.Stock.qta for r in righe)
    componenti_zero = sum(1 for r in righe if r.Stock.qta == 0)
    componenti_low = sum(1 for r in righe if 0 < r.Stock.qta < 50)

    return render_template(
        'stock/dettaglio.html',
        file_stock=file_stock,
        righe=righe,
        totale_righe=totale_righe,
        totale_qta=totale_qta,
        componenti_zero=componenti_zero,
        componenti_low=componenti_low
    )
