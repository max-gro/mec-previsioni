# app.py

import os
import json
import numpy as np
import pandas as pd
from flask import Flask, render_template, request

# Importa tutte le funzioni necessarie dai tuoi moduli
from preprocessing import build_df_componenti, build_df_affid, tronca_affidabilita
from functions import (
    precompute_all_predictions,
    precompute_all_predictions_by_stat
)

# =============================================================================
# 1. SETUP INIZIALE E PRE-COMPUTAZIONE
# =============================================================================

app = Flask(__name__)

# --- Definizione dei percorsi dei file ---
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
ROTTURE_PATH = os.path.join(BASE_DIR, "output_rotture_filtrate_completate.xlsx")
ANAGRAFICA_PATH = os.path.join(BASE_DIR, "_OUTPUT", "output_anagrafica.xlsx")
JSON_PATH = os.path.join(BASE_DIR, "output_modelli.json")
JSON_PERDATA_PATH = os.path.join(BASE_DIR, "output_modelli_per_data.json")
PREDICTIONS_PATH = os.path.join(BASE_DIR, "precomputed_predictions.json")
PREDICTIONS_STAT_PATH = os.path.join(BASE_DIR, "precomputed_predictions_stat.json")

# --- Caricamento dei dati grezzi ---
print("--- FASE 1: CARICAMENTO DATI GREZZI ---")
df_rotture = pd.read_excel(ROTTURE_PATH)
df_anagrafica = pd.read_excel(ANAGRAFICA_PATH)
with open(JSON_PATH, "r") as f:
    json_data = json.load(f)
with open(JSON_PERDATA_PATH, "r") as f:
    json_per_data = json.load(f)
print("Dati grezzi caricati con successo.")

# --- Preparazione del DataFrame per l'analisi di affidabilità ---
print("\n--- FASE 2: PREPARAZIONE DATAFRAME DI AFFIDABILITÀ ---")
rotture_per_modello = df_rotture.groupby("Modello").size().sort_values(ascending=False)
modelli_topN = rotture_per_modello.head(2).index.tolist()
print(f"Modelli selezionati per l'analisi: {modelli_topN}")

df_componenti_full = build_df_componenti(modelli_topN, json_per_data)
df_affid_full = build_df_affid(df_componenti_full, df_rotture)

print("Aggiunta colonna 'stat' al dataset di affidabilità...")
codice_to_stat_map = df_anagrafica.drop_duplicates(subset=['codice']).set_index('codice')['stat'].to_dict()
df_affid_full['stat'] = df_affid_full['Codice Componente'].map(codice_to_stat_map)
df_affid_troncato_full = tronca_affidabilita(df_affid_full, max_mesi=36)
print("Preparazione dati completata.")

# --- Calcolo o caricamento delle previsioni ---
print("\n--- FASE 3: GESTIONE PREDIZIONI ---")
if not os.path.exists(PREDICTIONS_PATH):
    print(f"File '{PREDICTIONS_PATH}' non trovato. Avvio calcolo previsioni per COMPONENTE...")
    predizioni_json = precompute_all_predictions(df_affid=df_affid_troncato_full, modelli_topN=modelli_topN, img_dir="static/pred_charts")
    with open(PREDICTIONS_PATH, "w") as f: json.dump(predizioni_json, f, indent=2)
    print("Predizioni per componente salvate.")
with open(PREDICTIONS_PATH, "r") as f:
    precomputed_predictions = json.load(f)

if not os.path.exists(PREDICTIONS_STAT_PATH):
    print(f"File '{PREDICTIONS_STAT_PATH}' non trovato. Avvio calcolo previsioni per GRUPPO STAT...")
    predizioni_stat_json = precompute_all_predictions_by_stat(df_affid_with_stat=df_affid_troncato_full, modelli_topN=modelli_topN, img_dir="static/pred_charts_stat")
    with open(PREDICTIONS_STAT_PATH, "w") as f: json.dump(predizioni_stat_json, f, indent=2)
    print("Predizioni per STAT salvate.")
with open(PREDICTIONS_STAT_PATH, "r") as f:
    precomputed_predictions_stat = json.load(f)

print("\n--- SETUP COMPLETATO. SERVER PRONTO. ---")


# =============================================================================
# 2. FUNZIONI HELPER
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
    """Genera un resoconto testuale delle statistiche di affidabilità storiche, incluso il risk set."""
    data_slice = df[(df["Modello"] == modello) & ((df["Codice Componente"] == code) if group_type == "Componente" else (df["stat"] == code))]
    if data_slice.empty: return f"Nessun dato di affidabilità trovato per {group_type} {code} nel modello {modello}."
    
    T, E = data_slice["Tempo di Vita"].values, data_slice["Censura"].values
    n_tot, n_rott = len(T), (E == 0).sum()
    
    summary = f"Resoconto per {group_type}: {code}\n" + "-"*50 + f"\nTotale unità osservate: {n_tot}\nRotture totali osservate: {n_rott}"
    if n_tot > 0: summary += f" ({n_rott/n_tot:.2%} del totale)\n\n"
    else: summary += "\n\n"
    
    summary += "Statistiche descrittive del tempo di vita (giorni) delle unità rotte:\n"
    if n_rott > 0:
        T_rotture = T[E == 0]
        summary += f"  - Min: {np.min(T_rotture):.0f}\n  - Media: {np.mean(T_rotture):.0f}\n  - Mediana: {np.median(T_rotture):.0f}\n  - Max: {np.max(T_rotture):.0f}\n\n"
    else: summary += "  - Nessuna rottura osservata.\n\n"
    
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

def tabella_componenti_con_previsioni(modelli, quantita, json_modelli, json_predizioni_comp, json_predizioni_stat, df_anagrafica_completa, df_affid):
    """Crea la tabella dettagliata per singolo componente, arricchita con dati storici e previsioni STAT."""
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
                "Codice componente": codice, "Descrizione Componente": info_comp.get("descrizione", ""),
                "Descrizione Inglese": info_comp.get("descrizione_en", ""), "Prezzo": price, "stat": stat_code,
                "Quantità per modello": qta_per_mod, "Quantità totale": qta_per_mod * quantita,
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
# 3. ROUTES FLASK
# =============================================================================

@app.route("/", methods=["GET", "POST"])
def index():
    selected_models, quantity, tabelle_previsioni = [], 1, {}
    periodi_osservazione = {}
    
    if request.method == "POST":
        selected_models = request.form.getlist("modelli")
        quantity = int(request.form.get("quantita", 1))
        
        if selected_models:
            tabelle_comp = tabella_componenti_con_previsioni(
                selected_models, quantity, json_data, precomputed_predictions,
                precomputed_predictions_stat, df_anagrafica, df_affid_full
            )
            tabelle_previsioni = {k: df.to_dict('records') for k, df in tabelle_comp.items()}

            for modello in selected_models:
                # Calcola data primo ordine per il modello
                sotto_df = df_affid_full[df_affid_full["Modello"] == modello]
                if not sotto_df.empty:
                    data_minima = sotto_df["Data Acquisto"].min()
                    if pd.notna(data_minima):
                        periodi_osservazione[modello] = data_minima.strftime("%d/%m/%y")

                # Aggiunge i resoconti statistici
                if modello in precomputed_predictions:
                    for comp_code, data in precomputed_predictions[modello].items():
                        data['summary_text'] = generate_reliability_summary(df_affid_full, modello, comp_code, "Componente")
                if modello in precomputed_predictions_stat:
                    for stat_code, data in precomputed_predictions_stat[modello].items():
                        data['summary_text'] = generate_reliability_summary(df_affid_full, modello, stat_code, "STAT")

    return render_template(
        "index.html", modelli=modelli_topN, selected_models=selected_models,
        quantity=quantity, tabelle_previsioni=tabelle_previsioni,
        precomputed_predictions=precomputed_predictions,
        precomputed_predictions_stat=precomputed_predictions_stat,
        periodi_osservazione=periodi_osservazione
    )

# =============================================================================
# 4. ESECUZIONE DELL'APPLICAZIONE
# =============================================================================

if __name__ == "__main__":
    app.run(debug=True)
