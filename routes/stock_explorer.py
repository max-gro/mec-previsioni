"""
Blueprint per Stock Explorer (Area C)

Permette di navigare il database giacenze in modalità read-only:
- Vista giacenze correnti (ultima rilevazione per componente)
- Filtri: componente, ubicazione, range quantità
- Dettaglio componente con storico giacenze
- Alert scorte basse/esaurite
"""

from flask import Blueprint, render_template, request, flash
from flask_login import login_required
from models import db, Stock, Componente, FileStock
from sqlalchemy import func, distinct, desc, asc, case
from datetime import datetime, timedelta

stock_explorer_bp = Blueprint('stock_explorer', __name__, url_prefix='/stock/explorer')


@stock_explorer_bp.route('/')
@login_required
def index():
    """
    Pagina principale stock explorer con vista giacenze correnti

    Mostra l'ultima rilevazione per ogni componente con filtri:
    - Ricerca componente
    - Range quantità
    - Ubicazione
    - Stato (tutti, scorta bassa, esauriti)
    """

    # Parametri filtri
    componente_filter = request.args.get('componente', '')
    ubicazione_filter = request.args.get('ubicazione', '')
    qta_min = request.args.get('qta_min', type=int)
    qta_max = request.args.get('qta_max', type=int)
    stato_filter = request.args.get('stato', '')  # 'low', 'zero', 'ok'
    sort_by = request.args.get('sort', 'cod_componente')
    order = request.args.get('order', 'asc')

    # Subquery: ultima data rilevazione per ogni componente
    last_dates = db.session.query(
        Stock.cod_componente,
        func.max(Stock.data_rilevazione).label('ultima_data')
    ).group_by(Stock.cod_componente).subquery()

    # Query principale: giacenze correnti con join alla subquery
    query = db.session.query(
        Stock,
        Componente
    ).join(
        last_dates,
        (Stock.cod_componente == last_dates.c.cod_componente) &
        (Stock.data_rilevazione == last_dates.c.ultima_data)
    ).outerjoin(
        Componente, Stock.cod_componente == Componente.cod_componente
    )

    # Applica filtri
    if componente_filter:
        query = query.filter(
            (Stock.cod_componente.ilike(f'%{componente_filter}%')) |
            (Componente.componente_it.ilike(f'%{componente_filter}%'))
        )

    if ubicazione_filter:
        query = query.filter(Stock.ubicazione.ilike(f'%{ubicazione_filter}%'))

    if qta_min is not None:
        query = query.filter(Stock.qta >= qta_min)

    if qta_max is not None:
        query = query.filter(Stock.qta <= qta_max)

    # Filtro stato
    if stato_filter == 'zero':
        query = query.filter(Stock.qta == 0)
    elif stato_filter == 'low':
        query = query.filter(Stock.qta > 0, Stock.qta < 50)
    elif stato_filter == 'ok':
        query = query.filter(Stock.qta >= 50)

    # Ordinamento
    if sort_by == 'cod_componente':
        col = Stock.cod_componente
    elif sort_by == 'qta':
        col = Stock.qta
    elif sort_by == 'data_rilevazione':
        col = Stock.data_rilevazione
    elif sort_by == 'ubicazione':
        col = Stock.ubicazione
    else:
        col = Stock.cod_componente

    if order == 'desc':
        query = query.order_by(col.desc())
    else:
        query = query.order_by(col.asc())

    # Esegui query
    risultati = query.all()

    # Limita risultati
    if len(risultati) > 500:
        flash(f'Trovati {len(risultati)} componenti, mostro i primi 500. Usa i filtri per affinare.', 'warning')
        risultati = risultati[:500]

    # KPI Summary
    total_componenti = len(risultati)
    total_unita = sum(r.Stock.qta for r in risultati)
    componenti_zero = sum(1 for r in risultati if r.Stock.qta == 0)
    componenti_low = sum(1 for r in risultati if 0 < r.Stock.qta < 50)

    # Ubicazioni disponibili per filtro
    ubicazioni = db.session.query(distinct(Stock.ubicazione))\
                          .filter(Stock.ubicazione.isnot(None))\
                          .order_by(Stock.ubicazione)\
                          .all()
    ubicazioni = [u[0] for u in ubicazioni]

    return render_template(
        'stock/explorer.html',
        risultati=risultati,
        total_componenti=total_componenti,
        total_unita=total_unita,
        componenti_zero=componenti_zero,
        componenti_low=componenti_low,
        componente_filter=componente_filter,
        ubicazione_filter=ubicazione_filter,
        ubicazioni=ubicazioni,
        qta_min=qta_min,
        qta_max=qta_max,
        stato_filter=stato_filter,
        sort_by=sort_by,
        order=order
    )


@stock_explorer_bp.route('/dettaglio/<cod_componente>')
@login_required
def dettaglio_componente(cod_componente):
    """
    Dettaglio componente con storico giacenze

    Mostra:
    - Info componente
    - Giacenza corrente
    - Storico rilevazioni (grafico + tabella)
    - File sorgente
    """

    # Info componente
    componente = Componente.query.filter_by(cod_componente=cod_componente).first()

    # Storico giacenze (tutte le rilevazioni ordinate per data)
    storico = db.session.query(
        Stock,
        FileStock
    ).outerjoin(
        FileStock, Stock.id_file_stock == FileStock.id
    ).filter(
        Stock.cod_componente == cod_componente
    ).order_by(
        Stock.data_rilevazione.desc()
    ).all()

    if not storico:
        flash(f'Nessuna giacenza trovata per componente {cod_componente}', 'warning')
        return render_template(
            'stock/explorer_dettaglio.html',
            componente=componente,
            cod_componente=cod_componente,
            storico=[],
            giacenza_corrente=None
        )

    # Giacenza corrente (prima del l'elenco = più recente)
    giacenza_corrente = storico[0].Stock

    # Prepara dati per grafico (invertiti per ordine cronologico)
    storico_reversed = list(reversed(storico))
    chart_labels = [s.Stock.data_rilevazione.strftime('%d/%m/%Y') for s in storico_reversed]
    chart_data = [s.Stock.qta for s in storico_reversed]

    # Statistiche
    qta_media = sum(s.Stock.qta for s in storico) / len(storico) if storico else 0
    qta_max = max(s.Stock.qta for s in storico)
    qta_min = min(s.Stock.qta for s in storico)

    return render_template(
        'stock/explorer_dettaglio.html',
        componente=componente,
        cod_componente=cod_componente,
        storico=storico,
        giacenza_corrente=giacenza_corrente,
        chart_labels=chart_labels,
        chart_data=chart_data,
        qta_media=qta_media,
        qta_max=qta_max,
        qta_min=qta_min
    )


@stock_explorer_bp.route('/alert')
@login_required
def alert():
    """
    Vista Alert: componenti con giacenze critiche

    Mostra:
    - Componenti esauriti (qtà = 0)
    - Componenti scorta bassa (0 < qtà < 50)
    Ordinati per priorità
    """

    # Subquery: ultima data rilevazione per ogni componente
    last_dates = db.session.query(
        Stock.cod_componente,
        func.max(Stock.data_rilevazione).label('ultima_data')
    ).group_by(Stock.cod_componente).subquery()

    # Query componenti critici (giacenza corrente < 50)
    query = db.session.query(
        Stock,
        Componente
    ).join(
        last_dates,
        (Stock.cod_componente == last_dates.c.cod_componente) &
        (Stock.data_rilevazione == last_dates.c.ultima_data)
    ).outerjoin(
        Componente, Stock.cod_componente == Componente.cod_componente
    ).filter(
        Stock.qta < 50
    ).order_by(
        Stock.qta.asc()  # Prima gli esauriti, poi i più bassi
    )

    componenti_critici = query.all()

    # Separa esauriti e scorta bassa
    esauriti = [c for c in componenti_critici if c.Stock.qta == 0]
    scorta_bassa = [c for c in componenti_critici if 0 < c.Stock.qta < 50]

    return render_template(
        'stock/explorer_alert.html',
        esauriti=esauriti,
        scorta_bassa=scorta_bassa,
        total_critici=len(componenti_critici)
    )
