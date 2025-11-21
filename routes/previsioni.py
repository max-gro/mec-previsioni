"""
Blueprint per la gestione delle previsioni di affidabilità
OTTIMIZZATO: Dati caricati solo quando necessario (lazy loading)
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required
import os
import json
import logging
import pandas as pd
import numpy as np

# Importa le funzioni dal tuo codice esistente
from preprocessing import build_df_componenti, build_df_affid, tronca_affidabilita
from functions import precompute_all_predictions, precompute_all_predictions_by_stat

# Logger per questo modulo
logger = logging.getLogger(__name__)

# Crea il Blueprint
previsioni_bp = Blueprint('previsioni', __name__)

# =============================================================================
# VARIABILI GLOBALI PER CACHE (caricate solo quando necessario)
# =============================================================================

_data_cache = {
    'loaded': False,
    'df_rotture': None,
    'df_anagrafica': None,
    'json_data': None,
    'json_per_data': None,
    'modelli_topN': None,
    'df_affid_full': None,
    'df_affid_troncato_full': None,
    'precomputed_predictions': None,
    'precomputed_predictions_stat': None
}

# Percorsi dei file
BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
ROTTURE_PATH = os.path.join(BASE_DIR, "output_rotture_filtrate_completate.xlsx")
ANAGRAFICA_PATH = os.path.join(BASE_DIR, "OUTPUT", "output_anagrafica.xlsx")
JSON_PATH = os.path.join(BASE_DIR, "output_modelli.json")
JSON_PERDATA_PATH = os.path.join(BASE_DIR, "output_modelli_per_data.json")
PREDICTIONS_PATH = os.path.join(BASE_DIR, "precomputed_predictions.json")
PREDICTIONS_STAT_PATH = os.path.join(BASE_DIR, "precomputed_predictions_stat.json")

# =============================================================================
# FUNZIONE DI CARICAMENTO LAZY
# =============================================================================

def load_data_if_needed():
    """
    Carica i dati solo se non sono già in cache
    Questa funzione viene chiamata solo quando si visita /previsioni
    """
    if _data_cache['loaded']:
        return  # Dati già caricati, skip

    logger.info("🔄 [PREVISIONI] Caricamento dati in corso...")

    # Caricamento dati grezzi
    _data_cache['df_rotture'] = pd.read_excel(ROTTURE_PATH)
    _data_cache['df_anagrafica'] = pd.read_excel(ANAGRAFICA_PATH)

    with open(JSON_PATH, "r") as f:
        _data_cache['json_data'] = json.load(f)
    with open(JSON_PERDATA_PATH, "r") as f:
        _data_cache['json_per_data'] = json.load(f)

    logger.info("✓ [PREVISIONI] Dati grezzi caricati")

    # Preparazione DataFrame di affidabilità
    rotture_per_modello = _data_cache['df_rotture'].groupby("Modello").size().sort_values(ascending=False)
    _data_cache['modelli_topN'] = rotture_per_modello.head(2).index.tolist()
    logger.info(f"✓ [PREVISIONI] Modelli selezionati: {_data_cache['modelli_topN']}")

    df_componenti_full = build_df_componenti(_data_cache['modelli_topN'], _data_cache['json_per_data'])
    _data_cache['df_affid_full'] = build_df_affid(df_componenti_full, _data_cache['df_rotture'])

    # Aggiungi colonna 'stat'
    codice_to_stat_map = _data_cache['df_anagrafica'].drop_duplicates(subset=['codice']).set_index('codice')['stat'].to_dict()
    _data_cache['df_affid_full']['stat'] = _data_cache['df_affid_full']['Codice Componente'].map(codice_to_stat_map)
    _data_cache['df_affid_troncato_full'] = tronca_affidabilita(_data_cache['df_affid_full'], max_mesi=36)

    logger.info("✓ [PREVISIONI] Preparazione dati completata")

    # Caricamento o calcolo previsioni
    if not os.path.exists(PREDICTIONS_PATH):
        logger.info("⚙️ [PREVISIONI] Calcolo previsioni per COMPONENTE...")
        predizioni_json = precompute_all_predictions(
            df_affid=_data_cache['df_affid_troncato_full'],
            modelli_topN=_data_cache['modelli_topN'],
            img_dir="static/pred_charts"
        )
        with open(PREDICTIONS_PATH, "w") as f:
            json.dump(predizioni_json, f, indent=2)
        logger.info("✓ [PREVISIONI] Predizioni per componente salvate")

    with open(PREDICTIONS_PATH, "r") as f:
        _data_cache['precomputed_predictions'] = json.load(f)

    if not os.path.exists(PREDICTIONS_STAT_PATH):
        logger.info("⚙️ [PREVISIONI] Calcolo previsioni per GRUPPO STAT...")
        predizioni_stat_json = precompute_all_predictions_by_stat(
            df_affid_with_stat=_data_cache['df_affid_troncato_full'],
            modelli_topN=_data_cache['modelli_topN'],
            img_dir="static/pred_charts_stat"
        )
        with open(PREDICTIONS_STAT_PATH, "w") as f:
            json.dump(predizioni_stat_json, f, indent=2)
        logger.info("✓ [PREVISIONI] Predizioni per STAT salvate")

    with open(PREDICTIONS_STAT_PATH, "r") as f:
        _data_cache['precomputed_predictions_stat'] = json.load(f)

    _data_cache['loaded'] = True
    logger.info("✅ [PREVISIONI] Setup completato e cachato in memoria")

# =============================================================================
# FUNZIONI HELPER
# =============================================================================

def get_historical_stats(df, modello, code, group_type="Componente"):
    """Recupera il numero totale e di rotture per un componente o gruppo STAT."""
    if group_type == "Componente":
        data_slice = df[(df["Modello"] == modello) & (df["Codice Componente"] == code)]
    else:  # group_type == "STAT"
        data_slice = df[(df["Modello"] == modello) & (df["stat"] == code)]

    if data_slice.empty:
        return {'total': 0, 'broken': 0}

    n_tot = len(data_slice)
    n_rott = (data_slice["Censura"] == 0).sum()
    return {'total': n_tot, 'broken': n_rott}

def generate_reliability_summary(df, modello, code, group_type="Componente"):
    """Genera un resoconto testuale delle statistiche di affidabilità storiche."""
    data_slice = df[(df["Modello"] == modello) & 
                    ((df["Codice Componente"] == code) if group_type == "Componente" else (df["stat"] == code))]
    
    if data_slice.empty:
        return f"Nessun dato di affidabilità trovato per {group_type} {code} nel modello {modello}."
    
    T, E = data_slice["Tempo di Vita"].values, data_slice["Censura"].values
    n_tot, n_rott = len(T), (E == 0).sum()
    
    summary = f"Resoconto per {group_type}: {code}\n" + "-"*50
    summary += f"\nTotale unità osservate: {n_tot}\nRotture totali osservate: {n_rott}"
    if n_tot > 0:
        summary += f" ({n_rott/n_tot:.2%} del totale)\n\n"
    else:
        summary += "\n\n"
    
    summary += "Statistiche descrittive del tempo di vita (giorni) delle unità rotte:\n"
    if n_rott > 0:
        T_rotture = T[E == 0]
        summary += f"  - Min: {np.min(T_rotture):.0f}\n"
        summary += f"  - Media: {np.mean(T_rotture):.0f}\n"
        summary += f"  - Mediana: {np.median(T_rotture):.0f}\n"
        summary += f"  - Max: {np.max(T_rotture):.0f}\n\n"
    else:
        summary += "  - Nessuna rottura osservata.\n\n"
    
    summary += "Rotture cumulative nel tempo (basate su dati storici):\n"
    for mesi in [6, 12, 18, 24, 30, 36]:
        rotture_periodo = ((E == 0) & (T <= mesi * 30.44)).sum()
        summary += f"  - Entro {mesi} mesi: {rotture_periodo} rotture\n"
        
    summary += "\nComponenti ancora attivi nel tempo (Risk Set):\n"
    for mesi in [0, 6, 12, 18, 24, 30, 36]:
        giorni = mesi * 30.44
        ancora_attivi = (T >= giorni).sum()
        summary += f"  - A {mesi} mesi: {ancora_attivi} unità attive\n"
        
    return summary

def tabella_componenti_con_previsioni(modelli, quantita, json_modelli, json_predizioni_comp, 
                                     json_predizioni_stat, df_anagrafica_completa, df_affid):
    """Crea la tabella dettagliata per singolo componente."""
    mappa_anagrafica = df_anagrafica_completa.drop_duplicates(subset="codice").set_index("codice").to_dict("index")
    tabelle = {}
    mesi = [12, 24, 36]
    
    for modello in modelli:
        componenti = json_modelli.get(modello, {}).get("componenti", {})
        dati = []
        
        for codice, qta_per_mod in componenti.items():
            info_comp = mappa_anagrafica.get(codice, {})
            price = info_comp.get("price", 0)
            stat_code = info_comp.get("stat")
            
            row = {
                "Codice componente": codice,
                "Descrizione Componente": info_comp.get("descrizione", ""),
                "Descrizione Inglese": info_comp.get("descrizione_en", ""),
                "Prezzo": price,
                "stat": stat_code,
                "Quantità  per modello": qta_per_mod,
                "Quantità  totale": qta_per_mod * quantita,
            }
            
            # Dati storici
            hist_stats_comp = get_historical_stats(df_affid, modello, codice, "Componente")
            row['total_comp'] = hist_stats_comp['total']
            row['broken_comp'] = hist_stats_comp['broken']
            
            if stat_code:
                hist_stats_stat = get_historical_stats(df_affid, modello, stat_code, "STAT")
                row['total_stat'] = hist_stats_stat['total']
                row['broken_stat'] = hist_stats_stat['broken']
            
            # Previsioni Componente
            pred_comp = json_predizioni_comp.get(modello, {}).get(codice, {})
            for m in mesi:
                prob = pred_comp.get(f"prev{m}")
                row[f"rottura_comp_{m}_mesi"] = prob
                row[f"ci_min_comp_{m}_mesi"] = pred_comp.get(f"prev{m}_lower")
                row[f"ci_max_comp_{m}_mesi"] = pred_comp.get(f"prev{m}_upper")
                row[f"costo_comp_{m}_mesi"] = prob * row["Quantità  totale"] * price if prob and price else None

            # Previsioni STAT
            pred_stat = json_predizioni_stat.get(modello, {}).get(stat_code, {})
            for m in mesi:
                prob = pred_stat.get(f"prev{m}")
                row[f"rottura_stat_{m}_mesi"] = prob
                row[f"ci_min_stat_{m}_mesi"] = pred_stat.get(f"prev{m}_lower")
                row[f"ci_max_stat_{m}_mesi"] = pred_stat.get(f"prev{m}_upper")
                row[f"costo_stat_{m}_mesi"] = prob * row["Quantità  totale"] * price if prob and price else None

            dati.append(row)
        
        if dati:
            tabelle[modello] = pd.DataFrame(dati)
    
    return tabelle

def tabella_componenti_con_previsioni_multi_qty(modelli, quantita_dict, json_modelli, json_predizioni_comp, 
                                                json_predizioni_stat, df_anagrafica_completa, df_affid):
    """
    Crea la tabella dettagliata per singolo componente (quantità per-modello).
    
    Args:
        quantita_dict: dizionario {modello: quantità}
    """
    mappa_anagrafica = df_anagrafica_completa.drop_duplicates(subset="codice").set_index("codice").to_dict("index")
    tabelle = {}
    mesi = [12, 24, 36]
    
    for modello in modelli:
        quantita_modello = quantita_dict.get(modello, 1)
        componenti = json_modelli.get(modello, {}).get("componenti", {})
        dati = []
        
        for codice, qta_per_mod in componenti.items():
            info_comp = mappa_anagrafica.get(codice, {})
            price = info_comp.get("price", 0)
            stat_code = info_comp.get("stat")
            
            row = {
                "Codice componente": codice,
                "Descrizione Componente": info_comp.get("descrizione", ""),
                "Descrizione Inglese": info_comp.get("descrizione_en", ""),
                "Prezzo": price,
                "stat": stat_code,
                "Quantità per modello": qta_per_mod,
                "Quantità totale": qta_per_mod * quantita_modello,
            }
            
            # Dati storici
            hist_stats_comp = get_historical_stats(df_affid, modello, codice, "Componente")
            row['total_comp'] = hist_stats_comp['total']
            row['broken_comp'] = hist_stats_comp['broken']
            
            if stat_code:
                hist_stats_stat = get_historical_stats(df_affid, modello, stat_code, "STAT")
                row['total_stat'] = hist_stats_stat['total']
                row['broken_stat'] = hist_stats_stat['broken']
            
            # Previsioni Componente
            pred_comp = json_predizioni_comp.get(modello, {}).get(codice, {})
            for m in mesi:
                prob = pred_comp.get(f"prev{m}")
                row[f"rottura_comp_{m}_mesi"] = prob
                row[f"ci_min_comp_{m}_mesi"] = pred_comp.get(f"prev{m}_lower")
                row[f"ci_max_comp_{m}_mesi"] = pred_comp.get(f"prev{m}_upper")
                row[f"costo_comp_{m}_mesi"] = prob * row["Quantità totale"] * price if prob and price else None

            # Previsioni STAT
            pred_stat = json_predizioni_stat.get(modello, {}).get(stat_code, {})
            for m in mesi:
                prob = pred_stat.get(f"prev{m}")
                row[f"rottura_stat_{m}_mesi"] = prob
                row[f"ci_min_stat_{m}_mesi"] = pred_stat.get(f"prev{m}_lower")
                row[f"ci_max_stat_{m}_mesi"] = pred_stat.get(f"prev{m}_upper")
                row[f"costo_stat_{m}_mesi"] = prob * row["Quantità totale"] * price if prob and price else None

            dati.append(row)
        
        if dati:
            tabelle[modello] = pd.DataFrame(dati)
    
    return tabelle

# =============================================================================
# ROUTES
# =============================================================================

@previsioni_bp.route('/', methods=['GET', 'POST'])
@login_required
def index():
    """
    Pagina principale delle previsioni di affidabilità
    I dati vengono caricati SOLO quando questa route viene chiamata
    """
    # Carica dati solo se necessario (lazy loading)
    load_data_if_needed()
    
    selected_models = []
    quantity = 1
    tabelle_previsioni = {}
    periodi_osservazione = {}
    
    if request.method == "POST":
        selected_models = request.form.getlist("modelli")
        quantity = int(request.form.get("quantita", 1))
        
        if selected_models:
            tabelle_comp = tabella_componenti_con_previsioni(
                selected_models, quantity, 
                _data_cache['json_data'], 
                _data_cache['precomputed_predictions'],
                _data_cache['precomputed_predictions_stat'], 
                _data_cache['df_anagrafica'], 
                _data_cache['df_affid_full']
            )
            tabelle_previsioni = {k: df.to_dict('records') for k, df in tabelle_comp.items()}

            for modello in selected_models:
                # Calcola data primo ordine per il modello
                sotto_df = _data_cache['df_affid_full'][_data_cache['df_affid_full']["Modello"] == modello]
                if not sotto_df.empty:
                    data_minima = sotto_df["Data Acquisto"].min()
                    if pd.notna(data_minima):
                        periodi_osservazione[modello] = data_minima.strftime("%d/%m/%y")

                # Aggiunge i resoconti statistici
                if modello in _data_cache['precomputed_predictions']:
                    for comp_code, data in _data_cache['precomputed_predictions'][modello].items():
                        data['summary_text'] = generate_reliability_summary(
                            _data_cache['df_affid_full'], modello, comp_code, "Componente"
                        )
                        
                if modello in _data_cache['precomputed_predictions_stat']:
                    for stat_code, data in _data_cache['precomputed_predictions_stat'][modello].items():
                        data['summary_text'] = generate_reliability_summary(
                            _data_cache['df_affid_full'], modello, stat_code, "STAT"
                        )

    return render_template(
        "previsioni/previsioni.html",
        modelli=_data_cache['modelli_topN'],
        selected_models=selected_models,
        quantity=quantity,
        tabelle_previsioni=tabelle_previsioni,
        precomputed_predictions=_data_cache['precomputed_predictions'],
        precomputed_predictions_stat=_data_cache['precomputed_predictions_stat'],
        periodi_osservazione=periodi_osservazione
    )
    
    
    
# === Percorso Excel ordini da cui filtrare i modelli per Nome File ===
ORDERS_XLSX_PATH = os.path.join(BASE_DIR, "preprocessing_PO", "orders_model_quantity_FINAL_shadow.xlsx")

def get_modelli_from_orders_excel(file_nome: str):
    """
    Legge l'Excel preprocessing_PO/orders_model_quantity_FINAL_shadow.xlsx,
    filtra per colonna 'file' == file_nome e ritorna i valori DISTINCT di 'modello' ordinati.
    """
    if not file_nome:
        return []
    if not os.path.exists(ORDERS_XLSX_PATH):
        print(f"[PREVISIONI] Excel ordini NON trovato: {ORDERS_XLSX_PATH}")
        return []
    try:
        df = pd.read_excel(ORDERS_XLSX_PATH)
    except Exception as e:
        print(f"[PREVISIONI] Errore lettura Excel ordini: {e}")
        return []

    # normalizza colonne attese
    cols = {c.lower(): c for c in df.columns}
    col_file = cols.get('file')
    col_modello = cols.get('modello')
    if not col_file or not col_modello:
        print("[PREVISIONI] Colonne 'file' / 'modello' non trovate nell'Excel ordini.")
        return []

    modelli = (
        df.loc[df[col_file] == file_nome, col_modello]
        .dropna()
        .astype(str)
        .drop_duplicates()
        .sort_values()
        .tolist()
    )
    return modelli

@previsioni_bp.route('/da-ordine', methods=['GET', 'POST'])
@login_required
def da_ordine():
    """
    Pagina previsionale precompilata a partire da un 'Nome File' d'ordine.
    - Querystring: ?file=<Nome File dell'ordine>
    - PO: precompilato col 'file'
    - Modelli: DISTINCT da Excel per quel 'file' + somma quantità per la tendina
    """
    load_data_if_needed()

    file_nome = request.args.get('file', '').strip()

    # ⬅️ Prendi sia i modelli sia le quantità sommate da Excel
    modelli_prepopolati, modelli_qty = get_modelli_e_quantita_from_orders_excel(file_nome)

    selected_models: list[str] = []
    selected_models_distinct: list[str] = []
    quantity = 1
    quantita_dict = {}  # Inizializza sempre, sarà popolato nel POST
    tabelle_previsioni = {}
    periodi_osservazione = {}

    if request.method == "POST":
        # Leggi modelli attivi (checkbox selezionati)
        modelli_attivi = request.form.getlist("modelli_attivi") or []
        
        # Leggi quantità per ogni modello
						  
        for modello in modelli_attivi:
            qty_field = f"qty_{modello}"
            try:
                qty = int(request.form.get(qty_field, 1))
                quantita_dict[modello] = max(1, qty)  # min 1
            except:
                quantita_dict[modello] = 1
        
        print(f"[PREVISIONI/da-ordine] POST -> modelli_attivi: {modelli_attivi}")
        print(f"[PREVISIONI/da-ordine] POST -> quantita_dict: {quantita_dict}")
        
        # DISTINCT preservando l'ordine
        def _distinct(seq):
            seen = set()
            out = []
            for x in seq:
                if x not in seen:
                    seen.add(x)
                    out.append(x)
            return out
        
        selected_models = modelli_attivi
        selected_models_distinct = _distinct(selected_models)
        models_for_calc = selected_models_distinct
        
        if models_for_calc:
            # Chiamata con quantità per-modello
            tabelle_comp = tabella_componenti_con_previsioni_multi_qty(
                models_for_calc, 
                quantita_dict,
                _data_cache['json_data'],
                _data_cache['precomputed_predictions'],
                _data_cache['precomputed_predictions_stat'],
                _data_cache['df_anagrafica'],
                _data_cache['df_affid_full']
            )
            tabelle_previsioni = {k: df.to_dict('records') for k, df in tabelle_comp.items()}
            
            # periodi di osservazione e summary text
            for modello in models_for_calc:
                sotto_df = _data_cache['df_affid_full'][_data_cache['df_affid_full']["Modello"] == modello]
                if not sotto_df.empty:
                    data_minima = sotto_df["Data Acquisto"].min()
                    if pd.notna(data_minima):
                        periodi_osservazione[modello] = data_minima.strftime("%d/%m/%y")
                
                if modello in _data_cache['precomputed_predictions']:
                    for comp_code, data in _data_cache['precomputed_predictions'][modello].items():
                        data['summary_text'] = generate_reliability_summary(
                            _data_cache['df_affid_full'], modello, comp_code, "Componente"
                        )
                if modello in _data_cache['precomputed_predictions_stat']:
                    for stat_code, data in _data_cache['precomputed_predictions_stat'][modello].items():
                        data['summary_text'] = generate_reliability_summary(
                            _data_cache['df_affid_full'], modello, stat_code, "STAT"
                        )


    # render
    return render_template(
        "previsioni/previsionidaordine.html",
        po_val=file_nome,                               # Precompila PO con Nome File
        modelli_prepopolati=modelli_prepopolati,       # Opzioni Modelli
        modelli_qty=modelli_qty,                       # Somme quantità per label tendina
        selected_models=selected_models,
        selected_models_distinct=selected_models_distinct,
        quantities_used=quantita_dict,
        quantity=quantity,
        tabelle_previsioni=tabelle_previsioni,
        precomputed_predictions=_data_cache['precomputed_predictions'],
        precomputed_predictions_stat=_data_cache['precomputed_predictions_stat'],
        periodi_osservazione=periodi_osservazione
    )


@previsioni_bp.route('/esporta-excel', methods=['POST'])
@login_required
def esporta_excel():
    """
    Esporta le tabelle previsioni in un file Excel multi-foglio.
    Un foglio per ogni modello.
    """
    from flask import send_file
    from io import BytesIO
    from datetime import datetime
    
    load_data_if_needed()
    
    # Leggi parametri POST
    po = request.form.get('po', 'ordine')
    modelli_export = request.form.getlist('modelli_export')
    
    # Leggi quantità per ogni modello
    quantita_dict = {}
    for modello in modelli_export:
        qty_field = f"qty_{modello}"
        try:
            qty = int(request.form.get(qty_field, 1))
            quantita_dict[modello] = max(1, qty)
        except:
            quantita_dict[modello] = 1
    
    if not modelli_export:
        flash('Nessun modello selezionato per l\'esportazione.', 'warning')
        return redirect(url_for('previsioni.da_ordine', file=po))
    
    try:
        # Rigenera le tabelle
        tabelle_comp = tabella_componenti_con_previsioni_multi_qty(
            modelli_export,
            quantita_dict,
            _data_cache['json_data'],
            _data_cache['precomputed_predictions'],
            _data_cache['precomputed_predictions_stat'],
            _data_cache['df_anagrafica'],
            _data_cache['df_affid_full']
        )
        
        # Crea Excel multi-foglio in memoria
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            for modello, df in tabelle_comp.items():
                # Arrotonda tutte le colonne numeriche a 2 decimali
                df_rounded = df.copy()
                numeric_cols = df_rounded.select_dtypes(include=['float64', 'float32', 'int64', 'int32']).columns
                df_rounded[numeric_cols] = df_rounded[numeric_cols].round(2)
                        
                # Pulizia nome foglio (Excel max 31 char, no caratteri speciali)
                sheet_name = modello[:31].replace('/', '_').replace('\\', '_').replace('*', '_')
                #df.to_excel(writer, sheet_name=sheet_name, index=False)
                df_rounded.to_excel(writer, sheet_name=sheet_name, index=False)
        
        output.seek(0)
        
        # Nome file con timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"previsioni_{po}_{timestamp}.xlsx"
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        flash(f'Errore durante l\'esportazione: {str(e)}', 'danger')
        return redirect(url_for('previsioni.da_ordine', file=po))


# ========================================
# helper per colonne + somma quantità
# ========================================

import re

ORDERS_XLSX_PATH = os.path.join(BASE_DIR, "preprocessing_PO", "orders_model_quantity_FINAL_shadow.xlsx")

def _norm(s: str) -> str:
    s = s.lower().strip()
    s = s.replace("à","a").replace("á","a").replace("è","e").replace("é","e") \
         .replace("ì","i").replace("í","i").replace("ò","o").replace("ó","o") \
         .replace("ù","u").replace("ú","u")
    return re.sub(r'[^a-z0-9]', '', s)

def _guess_qty_col(columns):
    """
    Prova a individuare la colonna 'quantità' con nomi tipici:
    QuantitaOrdinata / QuantitàOrdinata / Quantita / Quantità / qty / qta / q.tà
    """
    cand = [
        "quantitaordinata", "quantita", "qta", "qtaxmodello", "qtaordinata",
        "quantitaordine", "quantitapermodello", "qtapermodello",
        "pezzi", "pezziordinati", "numeropezzi", "numpezzi",
        "qty", "quantity", "quantityordered", "pieces", "amount",
        "ordered", "orderqty", "orderquantity"
    ]
    normmap = {_norm(c): c for c in columns}
    for k in cand:
        if k in normmap:
            print(f"[DEBUG] Colonna quantita trovata: {normmap[k]}")
            return normmap[k]
         
    # Match parziale
    for col_orig in columns:
        col_norm = _norm(col_orig)
        if any(kw in col_norm for kw in ["quantit", "qty", "qta", "pezz", "piece"]):
            print(f"[DEBUG] Colonna trovata (match parziale): {col_orig}")
            return col_orig
    
    print(f"[DEBUG] ⚠️ Colonna quantita NON trovata! Colonne: {list(columns)}")
    
    return None

def get_modelli_e_quantita_from_orders_excel(file_nome: str):
    """
    Ritorna:
      - lista modelli DISTINCT per quel file
      - dizionario {modello: somma_quantita} per quel file
    """
    if not file_nome or not os.path.exists(ORDERS_XLSX_PATH):
        return [], {}

    try:
        df = pd.read_excel(ORDERS_XLSX_PATH)
    except Exception as e:
        print(f"[PREVISIONI] Errore lettura Excel ordini: {e}")
        return [], {}

    # colonne
    cols_lc = {c.lower(): c for c in df.columns}
    col_file = cols_lc.get('file')
    col_modello = cols_lc.get('modello')
    if not col_file or not col_modello:
        print("[PREVISIONI] Colonne 'file' o 'modello' non trovate nell'Excel ordini.")
        return [], {}

    col_qta = _guess_qty_col(df.columns)

    df_f = df[df[col_file] == file_nome].copy()
    if df_f.empty:
        return [], {}

    # normalizza quantità (se presente); se non c'è, metti 0
    if col_qta and col_qta in df_f.columns:
        def _to_int(x):
            try:
                s = str(x).strip()
                if s == "" or s.lower() == "nan":
                    return 0
                # numeri tipo "12", "12.0", "12,0"
                s = s.replace(",", ".")
                return int(float(s))
            except:
                return 0
        df_f[col_qta] = df_f[col_qta].apply(_to_int)
        serie = df_f.groupby(col_modello, dropna=True)[col_qta].sum()
        modelli_qty = {str(k): int(v) for k, v in serie.items()}
    else:
        modelli_qty = {str(m): 0 for m in df_f[col_modello].astype(str)}

    modelli = list(modelli_qty.keys())
    modelli.sort()
    return modelli, modelli_qty
