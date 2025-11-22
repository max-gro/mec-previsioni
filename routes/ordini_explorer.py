"""
Blueprint per Ordini Explorer (Area A)

Permette di navigare il database di ordini acquisiti in modalità read-only:
- Filtri: anno, marca, buyer, seller, data ordine, modello
- Lista file ordini (master)
- Dettaglio file con 2 tab:
  1. Righe ordine - dettaglio componenti con quantità, prezzi, importi
  2. Aggregato per modello - totali per modello
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required
from models import db, FileOrdine, Ordine, Modello, Controparte
from sqlalchemy import func, distinct, desc, asc
from datetime import datetime, timedelta, timezone

ordini_explorer_bp = Blueprint('ordini_explorer', __name__, url_prefix='/ordini/explorer')


@ordini_explorer_bp.route('/')
@login_required
def index():
    """
    Pagina principale ordini explorer con filtri avanzati.

    Filtri:
    - anno
    - marca
    - buyer
    - seller
    - data_ordine (range)
    - modello (ricerca)
    - sort, order
    """

    # Ottieni parametri filtri
    anno = request.args.get('anno', '')
    marca = request.args.get('marca', '')
    buyer = request.args.get('buyer', '')
    seller = request.args.get('seller', '')
    modello = request.args.get('modello', '')
    data_da_str = request.args.get('data_da', '')
    data_a_str = request.args.get('data_a', '')
    sort_by = request.args.get('sort', 'data_ordine')
    order = request.args.get('order', 'desc')

    # Parse date
    data_da = None
    data_a = None
    if data_da_str:
        try:
            data_da = datetime.strptime(data_da_str, '%Y-%m-%d').date()
        except ValueError:
            pass
    if data_a_str:
        try:
            data_a = datetime.strptime(data_a_str, '%Y-%m-%d').date()
        except ValueError:
            pass

    # Query base file_ordini
    query = db.session.query(FileOrdine)

    # Applica filtri
    if anno:
        query = query.filter(FileOrdine.anno == int(anno))
    if marca:
        query = query.filter(FileOrdine.marca == marca)
    if buyer:
        query = query.filter(FileOrdine.cod_buyer == buyer)
    if seller:
        query = query.filter(FileOrdine.cod_seller == seller)
    if data_da:
        query = query.filter(FileOrdine.data_ordine >= data_da)
    if data_a:
        query = query.filter(FileOrdine.data_ordine <= data_a)

    # Filtro modello: cerca nelle righe ordini associate
    if modello:
        file_ids_con_modello = db.session.query(
            distinct(Ordine.id_file_ordine)
        ).filter(
            Ordine.cod_modello.ilike(f'%{modello}%')
        ).all()
        file_ids = [f[0] for f in file_ids_con_modello]
        if file_ids:
            query = query.filter(FileOrdine.id.in_(file_ids))
        else:
            query = query.filter(False)  # Nessun risultato

    # Ottieni file ordini
    file_ordini = query.all()

    # Arricchisci con conteggio righe e importo totale
    file_ordini_list = []
    for file in file_ordini:
        # Conta righe e somma importi
        righe_stats = db.session.query(
            func.count(Ordine.ordine_modello).label('n_righe'),
            func.sum(Ordine.importo_eur).label('totale_importo'),
            func.sum(Ordine.qta).label('totale_qta')
        ).filter(
            Ordine.id_file_ordine == file.id
        ).first()

        file_ordini_list.append({
            'id': file.id,
            'anno': file.anno,
            'marca': file.marca,
            'filename': file.filename,
            'filepath': file.filepath,
            'data_ordine': file.data_ordine,
            'esito': file.esito,
            'buyer': file.buyer.controparte if file.buyer else None,
            'seller': file.seller.controparte if file.seller else None,
            'cod_buyer': file.cod_buyer,
            'cod_seller': file.cod_seller,
            'n_righe': righe_stats.n_righe or 0,
            'totale_importo': float(righe_stats.totale_importo or 0),
            'totale_qta': righe_stats.totale_qta or 0
        })

    # Ordinamento
    if sort_by == 'data_ordine':
        file_ordini_list.sort(key=lambda x: x['data_ordine'] or datetime.min.date(), reverse=(order == 'desc'))
    elif sort_by == 'anno':
        file_ordini_list.sort(key=lambda x: x['anno'], reverse=(order == 'desc'))
    elif sort_by == 'marca':
        file_ordini_list.sort(key=lambda x: x['marca'] or '', reverse=(order == 'desc'))
    elif sort_by == 'n_righe':
        file_ordini_list.sort(key=lambda x: x['n_righe'], reverse=(order == 'desc'))
    elif sort_by == 'totale_importo':
        file_ordini_list.sort(key=lambda x: x['totale_importo'], reverse=(order == 'desc'))

    # Limita risultati
    if len(file_ordini_list) > 500:
        flash(f'Trovati {len(file_ordini_list)} ordini, mostro i primi 500. Usa i filtri per affinare.', 'warning')
        file_ordini_list = file_ordini_list[:500]

    # Ottieni valori univoci per dropdown filtri
    anni = db.session.query(distinct(FileOrdine.anno)).filter(FileOrdine.anno.isnot(None)).order_by(desc(FileOrdine.anno)).all()
    anni = [a[0] for a in anni]

    marche = db.session.query(distinct(FileOrdine.marca)).filter(FileOrdine.marca.isnot(None)).order_by(FileOrdine.marca).all()
    marche = [m[0] for m in marche]

    buyers = db.session.query(Controparte).order_by(Controparte.controparte).all()
    sellers = db.session.query(Controparte).order_by(Controparte.controparte).all()

    # KPI summary
    total_ordini = len(file_ordini_list)
    total_righe = sum(f['n_righe'] for f in file_ordini_list)
    total_importo = sum(f['totale_importo'] for f in file_ordini_list)
    total_qta = sum(f['totale_qta'] for f in file_ordini_list)

    return render_template(
        'ordini/explorer.html',
        file_ordini=file_ordini_list,
        total_ordini=total_ordini,
        total_righe=total_righe,
        total_importo=total_importo,
        total_qta=total_qta,
        anni=anni,
        marche=marche,
        buyers=buyers,
        sellers=sellers,
        anno=anno,
        marca=marca,
        buyer=buyer,
        seller=seller,
        modello=modello,
        data_da=data_da,
        data_a=data_a,
        sort_by=sort_by,
        order=order
    )


@ordini_explorer_bp.route('/dettaglio/<int:id_file_ordine>')
@login_required
def dettaglio_ordine(id_file_ordine):
    """
    Pagina dettaglio file ordine con 2 tab:
    1. Righe ordine - dettaglio componenti
    2. Aggregato per modello - totali per modello
    """

    # Ottieni file ordine
    file_ordine = db.session.query(FileOrdine).filter(FileOrdine.id == id_file_ordine).first()
    if not file_ordine:
        flash(f'File ordine ID {id_file_ordine} non trovato.', 'error')
        return redirect(url_for('ordini_explorer.index'))

    # TAB 1: RIGHE ORDINE
    righe = db.session.query(
        Ordine.ordine_modello,
        Ordine.cod_ordine,
        Ordine.cod_modello,
        Ordine.brand,
        Ordine.item,
        Ordine.ean,
        Ordine.qta,
        Ordine.prezzo_eur,
        Ordine.importo_eur,
        Modello.nome_modello,
        Modello.nome_modello_it
    ).outerjoin(
        Modello, Ordine.cod_modello == Modello.cod_modello
    ).filter(
        Ordine.id_file_ordine == id_file_ordine
    ).order_by(
        Ordine.cod_modello
    ).all()

    # Calcola totali righe
    totale_righe = len(righe)
    totale_qta = sum(r.qta or 0 for r in righe)
    totale_importo = sum(float(r.importo_eur or 0) for r in righe)

    # TAB 2: AGGREGATO PER MODELLO
    aggregato = db.session.query(
        Ordine.cod_modello,
        Modello.marca,
        Modello.nome_modello,
        func.count(Ordine.ordine_modello).label('n_righe'),
        func.sum(Ordine.qta).label('qta_totale'),
        func.sum(Ordine.importo_eur).label('importo_totale')
    ).outerjoin(
        Modello, Ordine.cod_modello == Modello.cod_modello
    ).filter(
        Ordine.id_file_ordine == id_file_ordine
    ).group_by(
        Ordine.cod_modello,
        Modello.marca,
        Modello.nome_modello
    ).order_by(
        desc('importo_totale')
    ).all()

    return render_template(
        'ordini/explorer_dettaglio.html',
        file_ordine=file_ordine,
        righe=righe,
        totale_righe=totale_righe,
        totale_qta=totale_qta,
        totale_importo=totale_importo,
        aggregato=aggregato
    )
