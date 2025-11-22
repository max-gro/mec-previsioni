"""
Blueprint per Catalogo Modelli & Componenti (Area B)

Permette di navigare il database di modelli e componenti in modalità read-only:
- Filtri: marca, divisione, famiglia, tipo, ricerca testo
- Lista modelli con n. componenti e flag origine dati
- Dettaglio modello con 3 tab:
  1. Componenti (BOM) - distinta base con quantità e prezzi
  2. File di origine - file anagrafiche sorgente
  3. Statistiche rotture - affidabilità e link a previsioni
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required
from models import db, Modello, Componente, ModelloComponente, FileAnagrafica, Rottura, RotturaComponente
from sqlalchemy import func, distinct, desc, asc
from datetime import datetime, timedelta, timezone

anagrafiche_catalogo_bp = Blueprint('anagrafiche_catalogo', __name__, url_prefix='/anagrafiche/catalogo')


@anagrafiche_catalogo_bp.route('/')
@login_required
def index():
    """
    Pagina principale catalogo modelli con filtri avanzati.

    Filtri:
    - marca
    - divisione
    - famiglia
    - tipo
    - ricerca (cod_modello o nome_modello)
    - sort (colonna)
    - order (asc/desc)
    """

    # Ottieni parametri filtri
    marca = request.args.get('marca', '')
    divisione = request.args.get('divisione', '')
    famiglia = request.args.get('famiglia', '')
    tipo = request.args.get('tipo', '')
    ricerca = request.args.get('ricerca', '')
    sort_by = request.args.get('sort', 'marca_modello')  # Default: marca + cod_modello
    order = request.args.get('order', 'asc')

    # Query base modelli
    query = db.session.query(Modello)

    # Applica filtri
    if marca:
        query = query.filter(Modello.marca == marca)
    if divisione:
        query = query.filter(Modello.divisione == divisione)
    if famiglia:
        query = query.filter(Modello.famiglia == famiglia)
    if tipo:
        query = query.filter(Modello.tipo == tipo)
    if ricerca:
        query = query.filter(
            (Modello.cod_modello.ilike(f'%{ricerca}%')) |
            (Modello.nome_modello.ilike(f'%{ricerca}%'))
        )

    # Ottieni modelli per calcolare aggregazioni
    modelli_ids = [m.cod_modello for m in query.all()]

    # Aggregazione: numero componenti per modello
    componenti_count = db.session.query(
        ModelloComponente.cod_modello,
        func.count(ModelloComponente.cod_componente).label('n_componenti')
    ).filter(
        ModelloComponente.cod_modello.in_(modelli_ids) if modelli_ids else False
    ).group_by(
        ModelloComponente.cod_modello
    ).all()

    # Converti in dizionario per lookup veloce
    componenti_map = {row.cod_modello: row.n_componenti for row in componenti_count}

    # Ottieni lista modelli
    modelli = query.all()

    # Arricchisci modelli con n_componenti
    modelli_list = []
    for modello in modelli:
        modelli_list.append({
            'cod_modello': modello.cod_modello,
            'marca': modello.marca,
            'divisione': modello.divisione,
            'famiglia': modello.famiglia,
            'tipo': modello.tipo,
            'nome_modello': modello.nome_modello,
            'nome_modello_it': modello.nome_modello_it,
            'updated_from': modello.updated_from or 'N/D',
            'n_componenti': componenti_map.get(modello.cod_modello, 0)
        })

    # Ordinamento
    if sort_by == 'marca_modello':
        modelli_list.sort(key=lambda x: (x['marca'] or '', x['cod_modello']), reverse=(order == 'desc'))
    elif sort_by == 'cod_modello':
        modelli_list.sort(key=lambda x: x['cod_modello'], reverse=(order == 'desc'))
    elif sort_by == 'marca':
        modelli_list.sort(key=lambda x: x['marca'] or '', reverse=(order == 'desc'))
    elif sort_by == 'divisione':
        modelli_list.sort(key=lambda x: x['divisione'] or '', reverse=(order == 'desc'))
    elif sort_by == 'famiglia':
        modelli_list.sort(key=lambda x: x['famiglia'] or '', reverse=(order == 'desc'))
    elif sort_by == 'tipo':
        modelli_list.sort(key=lambda x: x['tipo'] or '', reverse=(order == 'desc'))
    elif sort_by == 'n_componenti':
        modelli_list.sort(key=lambda x: x['n_componenti'], reverse=(order == 'desc'))

    # Limita risultati per performance (primi 500)
    if len(modelli_list) > 500:
        flash(f'Trovati {len(modelli_list)} modelli, mostro i primi 500. Usa i filtri per affinare la ricerca.', 'warning')
        modelli_list = modelli_list[:500]

    # Ottieni valori univoci per dropdown filtri
    marche = db.session.query(distinct(Modello.marca)).filter(Modello.marca.isnot(None)).order_by(Modello.marca).all()
    marche = [m[0] for m in marche]

    divisioni = db.session.query(distinct(Modello.divisione)).filter(Modello.divisione.isnot(None)).order_by(Modello.divisione).all()
    divisioni = [d[0] for d in divisioni]

    famiglie = db.session.query(distinct(Modello.famiglia)).filter(Modello.famiglia.isnot(None)).order_by(Modello.famiglia).all()
    famiglie = [f[0] for f in famiglie]

    tipi = db.session.query(distinct(Modello.tipo)).filter(Modello.tipo.isnot(None)).order_by(Modello.tipo).all()
    tipi = [t[0] for t in tipi]

    # KPI summary
    total_modelli = len(modelli_list)
    total_componenti = sum(m['n_componenti'] for m in modelli_list)

    return render_template(
        'anagrafiche/catalogo.html',
        modelli=modelli_list,
        total_modelli=total_modelli,
        total_componenti=total_componenti,
        marche=marche,
        divisioni=divisioni,
        famiglie=famiglie,
        tipi=tipi,
        marca=marca,
        divisione=divisione,
        famiglia=famiglia,
        tipo=tipo,
        ricerca=ricerca,
        sort_by=sort_by,
        order=order
    )


@anagrafiche_catalogo_bp.route('/dettaglio/<cod_modello>')
@login_required
def dettaglio_modello(cod_modello):
    """
    Pagina dettaglio modello con 3 tab:
    1. Componenti (BOM) - distinta base con quantità e prezzi
    2. File di origine - file anagrafiche sorgente
    3. Statistiche rotture - affidabilità e link a previsioni
    """

    # Ottieni modello
    modello = db.session.query(Modello).filter(Modello.cod_modello == cod_modello).first()
    if not modello:
        flash(f'Modello {cod_modello} non trovato.', 'error')
        return redirect(url_for('anagrafiche_catalogo.index'))

    # TAB 1: COMPONENTI (BOM)
    # Query BOM con join a componenti per ottenere prezzi
    bom = db.session.query(
        ModelloComponente.cod_componente,
        ModelloComponente.qta,
        Componente.componente_it,
        Componente.stat,
        Componente.softech_stat,
        Componente.unit_price_usd,
        Componente.unit_price_notra_noiva_netto_eur,
        Componente.unit_price_tra_noiva_netto_eur,
        Componente.part_name_it
    ).join(
        Componente, ModelloComponente.cod_componente == Componente.cod_componente
    ).filter(
        ModelloComponente.cod_modello == cod_modello
    ).order_by(
        ModelloComponente.cod_componente
    ).all()

    # Calcola riepilogo costi BOM
    totale_componenti = len(bom)
    totale_qta = sum(item.qta or 0 for item in bom)

    # Calcola costi teorici (somma qtà × prezzo)
    costo_usd = sum((item.qta or 0) * (item.unit_price_usd or 0) for item in bom)
    costo_buyer_eur = sum((item.qta or 0) * (item.unit_price_notra_noiva_netto_eur or 0) for item in bom)
    costo_seller_eur = sum((item.qta or 0) * (item.unit_price_tra_noiva_netto_eur or 0) for item in bom)

    bom_summary = {
        'totale_componenti': totale_componenti,
        'totale_qta': totale_qta,
        'costo_usd': float(costo_usd),
        'costo_buyer_eur': float(costo_buyer_eur),
        'costo_seller_eur': float(costo_seller_eur)
    }

    # TAB 2: FILE DI ORIGINE
    # Query file anagrafiche da cui proviene questo modello
    file_origine = db.session.query(
        FileAnagrafica.id,
        FileAnagrafica.anno,
        FileAnagrafica.marca,
        FileAnagrafica.filename,
        FileAnagrafica.esito,
        FileAnagrafica.data_acquisizione
    ).join(
        ModelloComponente, FileAnagrafica.id == ModelloComponente.id_file_anagrafiche
    ).filter(
        ModelloComponente.cod_modello == cod_modello
    ).distinct().order_by(
        desc(FileAnagrafica.anno),
        desc(FileAnagrafica.data_acquisizione)
    ).all()

    # TAB 3: STATISTICHE ROTTURE
    # Query rotture per questo modello
    rotture_stats = db.session.query(
        func.count(Rottura.cod_rottura).label('n_rotture'),
        func.avg(Rottura.gg_vita_prodotto).label('vita_media'),
        func.min(Rottura.data_competenza).label('data_prima_rottura'),
        func.max(Rottura.data_competenza).label('data_ultima_rottura')
    ).filter(
        Rottura.cod_modello == cod_modello
    ).first()

    # TOP 5 componenti più critici per rotture
    componenti_critici = db.session.query(
        RotturaComponente.cod_componente,
        Componente.componente_it,
        func.count(RotturaComponente.cod_rottura).label('n_rotture')
    ).join(
        Rottura, RotturaComponente.cod_rottura == Rottura.cod_rottura
    ).outerjoin(
        Componente, RotturaComponente.cod_componente == Componente.cod_componente
    ).filter(
        Rottura.cod_modello == cod_modello
    ).group_by(
        RotturaComponente.cod_componente,
        Componente.componente_it
    ).order_by(
        desc('n_rotture')
    ).limit(5).all()

    return render_template(
        'anagrafiche/catalogo_dettaglio.html',
        modello=modello,
        bom=bom,
        bom_summary=bom_summary,
        file_origine=file_origine,
        rotture_stats=rotture_stats,
        componenti_critici=componenti_critici
    )
