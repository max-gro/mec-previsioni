"""
Blueprint per la Dashboard Generale delle Elaborazioni
"""

from flask import Blueprint, render_template, request
from flask_login import login_required
from models import db, TraceElab, TraceElabDett, OrdineAcquisto, AnagraficaFile, Rottura
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

    # ORDINI (conta solo elaborazioni END = elaborazioni complete)
    ordini_total = OrdineAcquisto.query.count()
    ordini_elab_total = TraceElab.query.filter_by(tipo_file='ORD', step='END').count()
    ordini_elab_recenti = TraceElab.query.filter_by(tipo_file='ORD', step='END').filter(
        TraceElab.created_at >= data_inizio
    ).count()
    ordini_successo = TraceElab.query.filter_by(
        tipo_file='ORD',
        step='END',
        stato='OK'
    ).filter(TraceElab.created_at >= data_inizio).count()

    # ANAGRAFICHE
    anagr_total = AnagraficaFile.query.count()
    anagr_elab_total = TraceElab.query.filter_by(tipo_file='ANA', step='END').count()
    anagr_elab_recenti = TraceElab.query.filter_by(tipo_file='ANA', step='END').filter(
        TraceElab.created_at >= data_inizio
    ).count()
    anagr_successo = TraceElab.query.filter_by(
        tipo_file='ANA',
        step='END',
        stato='OK'
    ).filter(TraceElab.created_at >= data_inizio).count()

    # ROTTURE
    rotture_total = Rottura.query.count()
    rotture_elab_total = TraceElab.query.filter_by(tipo_file='ROT', step='END').count()
    rotture_elab_recenti = TraceElab.query.filter_by(tipo_file='ROT', step='END').filter(
        TraceElab.created_at >= data_inizio
    ).count()
    rotture_successo = TraceElab.query.filter_by(
        tipo_file='ROT',
        step='END',
        stato='OK'
    ).filter(TraceElab.created_at >= data_inizio).count()

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
    ultime_elaborazioni_end = TraceElab.query.filter(
        TraceElab.step == 'END',
        TraceElab.created_at >= data_inizio
    ).order_by(desc(TraceElab.created_at)).limit(10).all()

    # Arricchisci con info file e trace START
    elab_con_file = []
    for elab_end in ultime_elaborazioni_end:
        # Trova trace START corrispondente
        elab_start = TraceElab.query.filter_by(
            id_elab=elab_end.id_elab,
            tipo_file=elab_end.tipo_file,
            id_file=elab_end.id_file,
            step='START'
        ).first()

        # Determina tipo file e carica oggetto file
        if elab_end.tipo_file == 'ORD':
            file_obj = OrdineAcquisto.query.get(elab_end.id_file)
            tipo_pipeline_name = 'ordini'
        elif elab_end.tipo_file == 'ANA':
            file_obj = AnagraficaFile.query.get(elab_end.id_file)
            tipo_pipeline_name = 'anagrafiche'
        elif elab_end.tipo_file == 'ROT':
            from models import FileRottura
            file_obj = FileRottura.query.get(elab_end.id_file)
            tipo_pipeline_name = 'rotture'
        else:
            file_obj = None
            tipo_pipeline_name = 'unknown'

        elab_con_file.append({
            'elaborazione': {
                'id_elab': elab_end.id_elab,
                'ts_inizio': elab_start.created_at if elab_start else elab_end.created_at,
                'ts_fine': elab_end.created_at,
                'stato': elab_end.stato,
                'messaggio': elab_end.messaggio,
                'righe_totali': elab_end.righe_totali,
                'righe_ok': elab_end.righe_ok,
                'righe_errore': elab_end.righe_errore,
                'righe_warning': elab_end.righe_warning
            },
            'file': file_obj,
            'tipo_pipeline': tipo_pipeline_name
        })

    # ========== ELABORAZIONI CON ERRORI ==========
    elab_con_errori_end = TraceElab.query.filter(
        TraceElab.step == 'END',
        TraceElab.stato == 'KO',
        TraceElab.created_at >= data_inizio
    ).order_by(desc(TraceElab.created_at)).limit(10).all()

    errori_con_file = []
    for elab_end in elab_con_errori_end:
        # Trova trace START corrispondente
        elab_start = TraceElab.query.filter_by(
            id_elab=elab_end.id_elab,
            tipo_file=elab_end.tipo_file,
            id_file=elab_end.id_file,
            step='START'
        ).first()

        # Determina tipo file e carica oggetto file
        if elab_end.tipo_file == 'ORD':
            file_obj = OrdineAcquisto.query.get(elab_end.id_file)
            tipo_pipeline_name = 'ordini'
        elif elab_end.tipo_file == 'ANA':
            file_obj = AnagraficaFile.query.get(elab_end.id_file)
            tipo_pipeline_name = 'anagrafiche'
        elif elab_end.tipo_file == 'ROT':
            from models import FileRottura
            file_obj = FileRottura.query.get(elab_end.id_file)
            tipo_pipeline_name = 'rotture'
        else:
            file_obj = None
            tipo_pipeline_name = 'unknown'

        errori_con_file.append({
            'elaborazione': {
                'id_elab': elab_end.id_elab,
                'ts_inizio': elab_start.created_at if elab_start else elab_end.created_at,
                'ts_fine': elab_end.created_at,
                'stato': elab_end.stato,
                'messaggio': elab_end.messaggio,
                'righe_totali': elab_end.righe_totali,
                'righe_ok': elab_end.righe_ok,
                'righe_errore': elab_end.righe_errore,
                'righe_warning': elab_end.righe_warning
            },
            'file': file_obj,
            'tipo_pipeline': tipo_pipeline_name
        })

    # ========== STATISTICHE GLOBALI ==========
    # Durata media elaborazioni: calcolata da coppie START/END
    # Per ora semplifichiamo senza calcolare durata media (richiederebbe query complesse)
    # In futuro si può aggiungere una vista o calcolo più sofisticato

    # Totale dettagli elaborati (record processati)
    totale_righe = TraceElabDett.query.join(TraceElab).filter(
        TraceElab.created_at >= data_inizio
    ).count()

    # Totale errori (dettagli con stato KO)
    totale_errori = TraceElabDett.query.join(TraceElab).filter(
        TraceElab.created_at >= data_inizio,
        TraceElabDett.stato == 'KO'
    ).count()

    stats_globali = {
        'durata_media': 0,  # Placeholder - da implementare con calcolo START/END
        'totale_righe': totale_righe,
        'totale_errori': totale_errori
    }

    return render_template('dashboard/index.html',
                         stats_pipeline=stats_pipeline,
                         ultime_elaborazioni=elab_con_file,
                         errori=errori_con_file,
                         stats_globali=stats_globali,
                         days=days)
