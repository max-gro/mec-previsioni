"""
Blueprint per Rotture Explorer - Analisi Affidabilità Database

Vista read-only per navigare rotture strutturate:
- Aggregati per modello/componente
- Filtri avanzati
- TOP/FLOP lists
- Link con previsioni
"""

from flask import Blueprint, render_template, request, jsonify, send_file
from flask_login import login_required
from sqlalchemy import func, desc, case
from models import (
    db, FileRottura, Rottura, RotturaComponente,
    Modello, Componente, Rivenditore, UtenteRottura
)
from datetime import datetime, timedelta
import pandas as pd
from io import BytesIO

rotture_explorer_bp = Blueprint('rotture_explorer', __name__, url_prefix='/rotture/explorer')


@rotture_explorer_bp.route('/')
@login_required
def index():
    """
    Pagina principale Rotture Explorer

    Features:
    - Filtri: periodo, marca, modello, componente, rivenditore
    - Toggle vista: per modello / per componente
    - KPI cards (totale rotture, modelli coinvolti, etc.)
    - Tabella aggregati
    """

    # === Parametri filtri ===
    data_da = request.args.get('data_da', type=str)
    data_a = request.args.get('data_a', type=str)
    marca_filter = request.args.get('marca', '')
    modello_filter = request.args.get('modello', '')
    componente_filter = request.args.get('componente', '')
    rivenditore_filter = request.args.get('rivenditore', '')
    categoria_filter = request.args.get('cat', '')

    # Vista: 'modello' o 'componente'
    vista = request.args.get('vista', 'modello')

    # Ordinamento
    sort_by = request.args.get('sort', 'n_rotture')
    order = request.args.get('order', 'desc')

    # === Date default: ultimi 12 mesi ===
    if not data_a:
        data_a = datetime.now().date()
    else:
        data_a = datetime.strptime(data_a, '%Y-%m-%d').date()

    if not data_da:
        data_da = data_a - timedelta(days=365)
    else:
        data_da = datetime.strptime(data_da, '%Y-%m-%d').date()

    # === Query base rotture ===
    query = db.session.query(Rottura)

    # Filtri data
    if data_da:
        query = query.filter(Rottura.data_competenza >= data_da)
    if data_a:
        query = query.filter(Rottura.data_competenza <= data_a)

    # Filtri opzionali
    if marca_filter:
        query = query.join(Modello, Rottura.cod_modello == Modello.cod_modello)\
                     .filter(Modello.marca == marca_filter)

    if modello_filter:
        query = query.filter(Rottura.cod_modello.ilike(f'%{modello_filter}%'))

    if rivenditore_filter:
        query = query.filter(Rottura.cod_rivenditore.ilike(f'%{rivenditore_filter}%'))

    if categoria_filter:
        query = query.filter(Rottura.cat == categoria_filter)

    # === KPI Cards ===
    total_rotture = query.count()

    modelli_unici = db.session.query(func.count(func.distinct(Rottura.cod_modello)))\
                              .filter(Rottura.cod_rottura.in_([r.cod_rottura for r in query.all()]))\
                              .scalar() or 0

    vita_media = db.session.query(func.avg(Rottura.gg_vita_prodotto))\
                          .filter(Rottura.cod_rottura.in_([r.cod_rottura for r in query.all()]))\
                          .scalar() or 0

    # === Aggregazioni ===
    if vista == 'modello':
        aggregati = aggrega_per_modello(query, sort_by, order)
    else:
        aggregati = aggrega_per_componente(query, sort_by, order, componente_filter)

    # === Liste per dropdown filtri ===
    marche_disponibili = db.session.query(Modello.marca)\
                                   .distinct()\
                                   .order_by(Modello.marca)\
                                   .all()
    marche_disponibili = [m[0] for m in marche_disponibili if m[0]]

    categorie_disponibili = db.session.query(Rottura.cat)\
                                      .distinct()\
                                      .order_by(Rottura.cat)\
                                      .all()
    categorie_disponibili = [c[0] for c in categorie_disponibili if c[0]]

    return render_template('rotture/explorer.html',
                         aggregati=aggregati,
                         total_rotture=total_rotture,
                         modelli_unici=modelli_unici,
                         vita_media=round(vita_media, 0) if vita_media else 0,
                         data_da=data_da,
                         data_a=data_a,
                         marca_filter=marca_filter,
                         modello_filter=modello_filter,
                         componente_filter=componente_filter,
                         rivenditore_filter=rivenditore_filter,
                         categoria_filter=categoria_filter,
                         marche_disponibili=marche_disponibili,
                         categorie_disponibili=categorie_disponibili,
                         vista=vista,
                         sort_by=sort_by,
                         order=order)


def aggrega_per_modello(query_base, sort_by='n_rotture', order='desc'):
    """
    Aggrega rotture per modello

    Returns: Lista dict con:
        - cod_modello
        - marca
        - n_rotture
        - vita_media
        - componenti_coinvolti (count distinct)
    """

    # Subquery IDs rotture filtrate
    rotture_ids = [r.cod_rottura for r in query_base.all()]

    if not rotture_ids:
        return []

    # Aggregazione
    results = db.session.query(
        Rottura.cod_modello,
        Modello.marca,
        func.count(Rottura.cod_rottura).label('n_rotture'),
        func.avg(Rottura.gg_vita_prodotto).label('vita_media'),
        func.count(func.distinct(RotturaComponente.cod_componente)).label('componenti_coinvolti')
    ).outerjoin(
        Modello, Rottura.cod_modello == Modello.cod_modello
    ).outerjoin(
        RotturaComponente, Rottura.cod_rottura == RotturaComponente.cod_rottura
    ).filter(
        Rottura.cod_rottura.in_(rotture_ids)
    ).group_by(
        Rottura.cod_modello,
        Modello.marca
    )

    # Ordinamento
    if sort_by == 'n_rotture':
        column = func.count(Rottura.cod_rottura)
    elif sort_by == 'vita_media':
        column = func.avg(Rottura.gg_vita_prodotto)
    elif sort_by == 'componenti_coinvolti':
        column = func.count(func.distinct(RotturaComponente.cod_componente))
    else:
        column = func.count(Rottura.cod_rottura)

    if order == 'desc':
        results = results.order_by(column.desc())
    else:
        results = results.order_by(column.asc())

    # Limit per performance
    results = results.limit(100).all()

    # Formatta risultati
    aggregati = []
    for r in results:
        aggregati.append({
            'cod_modello': r.cod_modello,
            'marca': r.marca or 'N/D',
            'n_rotture': r.n_rotture,
            'vita_media': round(r.vita_media, 0) if r.vita_media else 0,
            'componenti_coinvolti': r.componenti_coinvolti or 0
        })

    return aggregati


def aggrega_per_componente(query_base, sort_by='n_rotture', order='desc', componente_filter=''):
    """
    Aggrega rotture per componente

    Returns: Lista dict con:
        - cod_componente
        - componente_it
        - n_rotture
        - modelli_coinvolti (count distinct)
    """

    # Subquery IDs rotture filtrate
    rotture_ids = [r.cod_rottura for r in query_base.all()]

    if not rotture_ids:
        return []

    # Query componenti
    query = db.session.query(
        RotturaComponente.cod_componente,
        Componente.componente_it,
        func.count(RotturaComponente.cod_rottura).label('n_rotture'),
        func.count(func.distinct(Rottura.cod_modello)).label('modelli_coinvolti')
    ).join(
        Rottura, RotturaComponente.cod_rottura == Rottura.cod_rottura
    ).outerjoin(
        Componente, RotturaComponente.cod_componente == Componente.cod_componente
    ).filter(
        Rottura.cod_rottura.in_(rotture_ids)
    )

    # Filtro componente specifico
    if componente_filter:
        query = query.filter(
            RotturaComponente.cod_componente.ilike(f'%{componente_filter}%') |
            Componente.componente_it.ilike(f'%{componente_filter}%')
        )

    query = query.group_by(
        RotturaComponente.cod_componente,
        Componente.componente_it
    )

    # Ordinamento
    if sort_by == 'n_rotture':
        column = func.count(RotturaComponente.cod_rottura)
    elif sort_by == 'modelli_coinvolti':
        column = func.count(func.distinct(Rottura.cod_modello))
    else:
        column = func.count(RotturaComponente.cod_rottura)

    if order == 'desc':
        query = query.order_by(column.desc())
    else:
        query = query.order_by(column.asc())

    results = query.limit(100).all()

    # Formatta risultati
    aggregati = []
    for r in results:
        aggregati.append({
            'cod_componente': r.cod_componente,
            'componente_it': r.componente_it or 'N/D',
            'n_rotture': r.n_rotture,
            'modelli_coinvolti': r.modelli_coinvolti
        })

    return aggregati


@rotture_explorer_bp.route('/dettaglio/<cod_modello>')
@login_required
def dettaglio_modello(cod_modello):
    """
    Dettaglio rotture per un modello specifico

    Mostra:
    - Lista rotture del modello
    - Componenti più critici per questo modello
    - Timeline rotture
    """

    # Filtri periodo (mantieni da index)
    data_da = request.args.get('data_da', type=str)
    data_a = request.args.get('data_a', type=str)

    if data_a:
        data_a = datetime.strptime(data_a, '%Y-%m-%d').date()
    else:
        data_a = datetime.now().date()

    if data_da:
        data_da = datetime.strptime(data_da, '%Y-%m-%d').date()
    else:
        data_da = data_a - timedelta(days=365)

    # Query rotture modello
    rotture = db.session.query(Rottura).filter(
        Rottura.cod_modello == cod_modello,
        Rottura.data_competenza >= data_da,
        Rottura.data_competenza <= data_a
    ).order_by(Rottura.data_competenza.desc()).all()

    # Componenti critici per questo modello
    componenti_critici = db.session.query(
        RotturaComponente.cod_componente,
        Componente.componente_it,
        func.count(RotturaComponente.cod_rottura).label('n_rotture')
    ).join(
        Rottura, RotturaComponente.cod_rottura == Rottura.cod_rottura
    ).outerjoin(
        Componente, RotturaComponente.cod_componente == Componente.cod_componente
    ).filter(
        Rottura.cod_modello == cod_modello,
        Rottura.data_competenza >= data_da,
        Rottura.data_competenza <= data_a
    ).group_by(
        RotturaComponente.cod_componente,
        Componente.componente_it
    ).order_by(
        desc('n_rotture')
    ).limit(10).all()

    # Info modello
    modello = Modello.query.filter_by(cod_modello=cod_modello).first()

    return render_template('rotture/explorer_dettaglio.html',
                         rotture=rotture,
                         componenti_critici=componenti_critici,
                         modello=modello,
                         cod_modello=cod_modello,
                         data_da=data_da,
                         data_a=data_a)


@rotture_explorer_bp.route('/export-excel')
@login_required
def export_excel():
    """
    Export risultati in Excel

    Esporta aggregati correnti (con filtri applicati)
    """

    # Ri-esegui query con filtri
    # (codice semplificato, andrebbe refactorizzato per riusare logica index)

    vista = request.args.get('vista', 'modello')

    # Placeholder - implementazione completa dopo
    data = {
        'cod_modello': ['MOD-001', 'MOD-002'],
        'n_rotture': [10, 5],
        'vita_media': [720, 650]
    }

    df = pd.DataFrame(data)

    # Export Excel in memoria
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Rotture', index=False)

    output.seek(0)

    filename = f'rotture_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'

    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )
