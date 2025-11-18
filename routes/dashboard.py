"""
Blueprint per la Dashboard Generale delle Elaborazioni
"""

from flask import Blueprint, render_template, request
from flask_login import login_required
from models import db, TraceElaborazione, OrdineAcquisto, AnagraficaFile, Rottura
from sqlalchemy import func, desc
from datetime import datetime, timedelta

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
@login_required
def index():
    """
    Dashboard principale con statistiche globali delle 3 pipeline
    """
    # Filtro temporale (ultimi N giorni)
    days = request.args.get('days', 7, type=int)
    data_inizio = datetime.utcnow() - timedelta(days=days)

    # ========== STATISTICHE PER PIPELINE ==========

    # ORDINI
    ordini_total = OrdineAcquisto.query.count()
    ordini_elab_total = TraceElaborazione.query.filter_by(tipo_pipeline='ordini').count()
    ordini_elab_recenti = TraceElaborazione.query.filter_by(tipo_pipeline='ordini').filter(
        TraceElaborazione.ts_inizio >= data_inizio
    ).count()
    ordini_successo = TraceElaborazione.query.filter_by(
        tipo_pipeline='ordini',
        esito='Successo'
    ).filter(TraceElaborazione.ts_inizio >= data_inizio).count()

    # ANAGRAFICHE
    anagr_total = AnagraficaFile.query.count()
    anagr_elab_total = TraceElaborazione.query.filter_by(tipo_pipeline='anagrafiche').count()
    anagr_elab_recenti = TraceElaborazione.query.filter_by(tipo_pipeline='anagrafiche').filter(
        TraceElaborazione.ts_inizio >= data_inizio
    ).count()
    anagr_successo = TraceElaborazione.query.filter_by(
        tipo_pipeline='anagrafiche',
        esito='Successo'
    ).filter(TraceElaborazione.ts_inizio >= data_inizio).count()

    # ROTTURE
    rotture_total = Rottura.query.count()
    rotture_elab_total = TraceElaborazione.query.filter_by(tipo_pipeline='rotture').count()
    rotture_elab_recenti = TraceElaborazione.query.filter_by(tipo_pipeline='rotture').filter(
        TraceElaborazione.ts_inizio >= data_inizio
    ).count()
    rotture_successo = TraceElaborazione.query.filter_by(
        tipo_pipeline='rotture',
        esito='Successo'
    ).filter(TraceElaborazione.ts_inizio >= data_inizio).count()

    # Calcola % successo
    ordini_perc = round((ordini_successo / ordini_elab_recenti * 100), 1) if ordini_elab_recenti > 0 else 0
    anagr_perc = round((anagr_successo / anagr_elab_recenti * 100), 1) if anagr_elab_recenti > 0 else 0
    rotture_perc = round((rotture_successo / rotture_elab_recenti * 100), 1) if rotture_elab_recenti > 0 else 0

    stats_pipeline = {
        'ordini': {
            'file_totali': ordini_total,
            'elaborazioni_totali': ordini_elab_total,
            'elaborazioni_recenti': ordini_elab_recenti,
            'successi': ordini_successo,
            'perc_successo': ordini_perc
        },
        'anagrafiche': {
            'file_totali': anagr_total,
            'elaborazioni_totali': anagr_elab_total,
            'elaborazioni_recenti': anagr_elab_recenti,
            'successi': anagr_successo,
            'perc_successo': anagr_perc
        },
        'rotture': {
            'file_totali': rotture_total,
            'elaborazioni_totali': rotture_elab_total,
            'elaborazioni_recenti': rotture_elab_recenti,
            'successi': rotture_successo,
            'perc_successo': rotture_perc
        }
    }

    # ========== ULTIME ELABORAZIONI ==========
    ultime_elaborazioni = TraceElaborazione.query.filter(
        TraceElaborazione.ts_inizio >= data_inizio
    ).order_by(desc(TraceElaborazione.ts_inizio)).limit(10).all()

    # Arricchisci con info file
    elab_con_file = []
    for elab in ultime_elaborazioni:
        file_obj = elab.get_file_object()
        elab_con_file.append({
            'elaborazione': elab,
            'file': file_obj
        })

    # ========== ELABORAZIONI CON ERRORI ==========
    elab_con_errori = TraceElaborazione.query.filter(
        TraceElaborazione.esito == 'Errore',
        TraceElaborazione.ts_inizio >= data_inizio
    ).order_by(desc(TraceElaborazione.ts_inizio)).limit(10).all()

    errori_con_file = []
    for elab in elab_con_errori:
        file_obj = elab.get_file_object()
        errori_con_file.append({
            'elaborazione': elab,
            'file': file_obj
        })

    # ========== STATISTICHE GLOBALI ==========
    # Durata media elaborazioni (ultimi N giorni, solo successi)
    durata_media_query = db.session.query(
        func.avg(TraceElaborazione.durata_secondi)
    ).filter(
        TraceElaborazione.ts_inizio >= data_inizio,
        TraceElaborazione.esito.in_(['Successo', 'Warning']),
        TraceElaborazione.durata_secondi.isnot(None)
    ).scalar()

    durata_media = round(durata_media_query, 1) if durata_media_query else 0

    # Totale righe elaborate
    totale_righe = db.session.query(
        func.sum(TraceElaborazione.righe_totali)
    ).filter(
        TraceElaborazione.ts_inizio >= data_inizio
    ).scalar() or 0

    # Totale errori
    totale_errori = db.session.query(
        func.sum(TraceElaborazione.righe_errore)
    ).filter(
        TraceElaborazione.ts_inizio >= data_inizio
    ).scalar() or 0

    stats_globali = {
        'durata_media': durata_media,
        'totale_righe': totale_righe,
        'totale_errori': totale_errori
    }

    return render_template('dashboard/index.html',
                         stats_pipeline=stats_pipeline,
                         ultime_elaborazioni=elab_con_file,
                         errori=errori_con_file,
                         stats_globali=stats_globali,
                         days=days)
