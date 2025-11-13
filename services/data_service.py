"""
Data Service - Gestione Dati e Cache
Caricamento dati, preprocessing e funzioni helper per statistiche
"""

import os
import json
import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


def load_data_cache(
    base_dir: str,
    rotture_path: Optional[str] = None,
    anagrafica_path: Optional[str] = None,
    json_path: Optional[str] = None,
    json_perdata_path: Optional[str] = None,
    predictions_path: Optional[str] = None,
    predictions_stat_path: Optional[str] = None
) -> Dict:
    """
    Carica tutti i dati necessari per le previsioni e li ritorna in un dizionario

    Args:
        base_dir: Directory base del progetto
        rotture_path: Path file Excel rotture (default: base_dir/output_rotture_filtrate_completate.xlsx)
        anagrafica_path: Path file Excel anagrafiche (default: base_dir/OUTPUT/output_anagrafica.xlsx)
        json_path: Path JSON modelli (default: base_dir/output_modelli.json)
        json_perdata_path: Path JSON modelli per data (default: base_dir/output_modelli_per_data.json)
        predictions_path: Path previsioni componenti (default: base_dir/precomputed_predictions.json)
        predictions_stat_path: Path previsioni STAT (default: base_dir/precomputed_predictions_stat.json)

    Returns:
        Dizionario con tutti i dati caricati:
        {
            'df_rotture': DataFrame,
            'df_anagrafica': DataFrame,
            'json_data': dict,
            'json_per_data': dict,
            'modelli_topN': list,
            'df_affid_full': DataFrame,
            'df_affid_troncato_full': DataFrame,
            'precomputed_predictions': dict,
            'precomputed_predictions_stat': dict
        }
    """
    # Import necessari
    from preprocessing import build_df_componenti, build_df_affid, tronca_affidabilita

    # Path di default
    if rotture_path is None:
        rotture_path = os.path.join(base_dir, "output_rotture_filtrate_completate.xlsx")
    if anagrafica_path is None:
        anagrafica_path = os.path.join(base_dir, "OUTPUT", "output_anagrafica.xlsx")
    if json_path is None:
        json_path = os.path.join(base_dir, "output_modelli.json")
    if json_perdata_path is None:
        json_perdata_path = os.path.join(base_dir, "output_modelli_per_data.json")
    if predictions_path is None:
        predictions_path = os.path.join(base_dir, "precomputed_predictions.json")
    if predictions_stat_path is None:
        predictions_stat_path = os.path.join(base_dir, "precomputed_predictions_stat.json")

    logger.info("Inizio caricamento dati...")

    # Carica dati grezzi
    df_rotture = pd.read_excel(rotture_path)
    df_anagrafica = pd.read_excel(anagrafica_path)

    with open(json_path, "r") as f:
        json_data = json.load(f)

    with open(json_perdata_path, "r") as f:
        json_per_data = json.load(f)

    logger.info("Dati grezzi caricati")

    # Seleziona top N modelli per numero di rotture
    rotture_per_modello = df_rotture.groupby("Modello").size().sort_values(ascending=False)
    modelli_topN = rotture_per_modello.head(2).index.tolist()
    logger.info(f"Modelli selezionati: {modelli_topN}")

    # Prepara DataFrame di affidabilità
    df_componenti_full = build_df_componenti(modelli_topN, json_per_data)
    df_affid_full = build_df_affid(df_componenti_full, df_rotture)

    # Aggiungi colonna 'stat' da anagrafica
    codice_to_stat_map = df_anagrafica.drop_duplicates(
        subset=['codice']
    ).set_index('codice')['stat'].to_dict()

    df_affid_full['stat'] = df_affid_full['Codice Componente'].map(codice_to_stat_map)
    df_affid_troncato_full = tronca_affidabilita(df_affid_full, max_mesi=36)

    logger.info("Preparazione dati completata")

    # Carica previsioni precompilate (se esistono)
    precomputed_predictions = None
    if os.path.exists(predictions_path):
        with open(predictions_path, "r") as f:
            precomputed_predictions = json.load(f)
        logger.info("Previsioni componenti caricate da cache")

    precomputed_predictions_stat = None
    if os.path.exists(predictions_stat_path):
        with open(predictions_stat_path, "r") as f:
            precomputed_predictions_stat = json.load(f)
        logger.info("Previsioni STAT caricate da cache")

    return {
        'df_rotture': df_rotture,
        'df_anagrafica': df_anagrafica,
        'json_data': json_data,
        'json_per_data': json_per_data,
        'modelli_topN': modelli_topN,
        'df_affid_full': df_affid_full,
        'df_affid_troncato_full': df_affid_troncato_full,
        'precomputed_predictions': precomputed_predictions,
        'precomputed_predictions_stat': precomputed_predictions_stat
    }


def get_historical_stats(
    df: pd.DataFrame,
    modello: str,
    code: str,
    group_type: str = "Componente"
) -> Dict[str, int]:
    """
    Recupera statistiche storiche (totale unità e rotture) per un componente o gruppo STAT

    Args:
        df: DataFrame con dati di affidabilità
        modello: Codice modello
        code: Codice componente o STAT
        group_type: Tipo di raggruppamento ("Componente" o "STAT")

    Returns:
        Dizionario {'total': n_tot, 'broken': n_rott}
    """
    if group_type == "Componente":
        data_slice = df[(df["Modello"] == modello) & (df["Codice Componente"] == code)]
    else:  # group_type == "STAT"
        data_slice = df[(df["Modello"] == modello) & (df["stat"] == code)]

    if data_slice.empty:
        return {'total': 0, 'broken': 0}

    n_tot = len(data_slice)
    n_rott = (data_slice["Censura"] == 0).sum()

    return {'total': n_tot, 'broken': n_rott}


def generate_reliability_summary(
    df: pd.DataFrame,
    modello: str,
    code: str,
    group_type: str = "Componente"
) -> str:
    """
    Genera un resoconto testuale dettagliato delle statistiche di affidabilità storiche

    Args:
        df: DataFrame con dati di affidabilità
        modello: Codice modello
        code: Codice componente o STAT
        group_type: Tipo di raggruppamento ("Componente" o "STAT")

    Returns:
        Stringa formattata con statistiche descrittive
    """
    # Filtra dati
    if group_type == "Componente":
        data_slice = df[(df["Modello"] == modello) & (df["Codice Componente"] == code)]
    else:
        data_slice = df[(df["Modello"] == modello) & (df["stat"] == code)]

    if data_slice.empty:
        return f"Nessun dato di affidabilità trovato per {group_type} {code} nel modello {modello}."

    T = data_slice["Tempo di Vita"].values
    E = data_slice["Censura"].values
    n_tot = len(T)
    n_rott = (E == 0).sum()

    # Header
    summary = f"Resoconto per {group_type}: {code}\n"
    summary += "-" * 50

    # Statistiche generali
    summary += f"\nTotale unità osservate: {n_tot}\n"
    summary += f"Rotture totali osservate: {n_rott}"

    if n_tot > 0:
        summary += f" ({n_rott/n_tot:.2%} del totale)\n\n"
    else:
        summary += "\n\n"

    # Statistiche descrittive tempo di vita (solo rotture)
    summary += "Statistiche descrittive del tempo di vita (giorni) delle unità rotte:\n"

    if n_rott > 0:
        T_rotture = T[E == 0]
        summary += f"  - Min: {np.min(T_rotture):.0f}\n"
        summary += f"  - Media: {np.mean(T_rotture):.0f}\n"
        summary += f"  - Mediana: {np.median(T_rotture):.0f}\n"
        summary += f"  - Max: {np.max(T_rotture):.0f}\n\n"
    else:
        summary += "  - Nessuna rottura osservata.\n\n"

    # Rotture cumulative nel tempo
    summary += "Rotture cumulative nel tempo (basate su dati storici):\n"
    for mesi in [6, 12, 18, 24, 30, 36]:
        rotture_periodo = ((E == 0) & (T <= mesi * 30.44)).sum()
        summary += f"  - Entro {mesi} mesi: {rotture_periodo} rotture\n"

    # Risk set nel tempo
    summary += "\nComponenti ancora attivi nel tempo (Risk Set):\n"
    for mesi in [0, 6, 12, 18, 24, 30, 36]:
        giorni = mesi * 30.44
        ancora_attivi = (T >= giorni).sum()
        summary += f"  - A {mesi} mesi: {ancora_attivi} unità attive\n"

    return summary


def tabella_componenti_con_previsioni(
    modelli: list,
    quantita: int,
    json_modelli: dict,
    json_predizioni_comp: dict,
    json_predizioni_stat: dict,
    df_anagrafica_completa: pd.DataFrame,
    df_affid: pd.DataFrame
) -> Dict[str, pd.DataFrame]:
    """
    Crea tabelle dettagliate con previsioni per ogni modello (quantità fissa)

    Args:
        modelli: Lista modelli da elaborare
        quantita: Quantità fissa per tutti i modelli
        json_modelli: Dizionario modelli con componenti
        json_predizioni_comp: Previsioni per componente
        json_predizioni_stat: Previsioni per gruppo STAT
        df_anagrafica_completa: DataFrame anagrafica
        df_affid: DataFrame affidabilità

    Returns:
        Dizionario {modello: DataFrame} con tabelle previsioni
    """
    mappa_anagrafica = df_anagrafica_completa.drop_duplicates(
        subset="codice"
    ).set_index("codice").to_dict("index")

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
                "Quantità per modello": qta_per_mod,
                "Quantità totale": qta_per_mod * quantita,
            }

            # Dati storici componente
            hist_stats_comp = get_historical_stats(df_affid, modello, codice, "Componente")
            row['total_comp'] = hist_stats_comp['total']
            row['broken_comp'] = hist_stats_comp['broken']

            # Dati storici STAT (se esiste)
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
                row[f"costo_comp_{m}_mesi"] = (
                    prob * row["Quantità totale"] * price
                    if prob and price else None
                )

            # Previsioni STAT
            pred_stat = json_predizioni_stat.get(modello, {}).get(stat_code, {})
            for m in mesi:
                prob = pred_stat.get(f"prev{m}")
                row[f"rottura_stat_{m}_mesi"] = prob
                row[f"ci_min_stat_{m}_mesi"] = pred_stat.get(f"prev{m}_lower")
                row[f"ci_max_stat_{m}_mesi"] = pred_stat.get(f"prev{m}_upper")
                row[f"costo_stat_{m}_mesi"] = (
                    prob * row["Quantità totale"] * price
                    if prob and price else None
                )

            dati.append(row)

        if dati:
            tabelle[modello] = pd.DataFrame(dati)

    return tabelle


def tabella_componenti_con_previsioni_multi_qty(
    modelli: list,
    quantita_dict: dict,
    json_modelli: dict,
    json_predizioni_comp: dict,
    json_predizioni_stat: dict,
    df_anagrafica_completa: pd.DataFrame,
    df_affid: pd.DataFrame
) -> Dict[str, pd.DataFrame]:
    """
    Crea tabelle dettagliate con previsioni per ogni modello (quantità variabile)

    Args:
        modelli: Lista modelli da elaborare
        quantita_dict: Dizionario {modello: quantità}
        json_modelli: Dizionario modelli con componenti
        json_predizioni_comp: Previsioni per componente
        json_predizioni_stat: Previsioni per gruppo STAT
        df_anagrafica_completa: DataFrame anagrafica
        df_affid: DataFrame affidabilità

    Returns:
        Dizionario {modello: DataFrame} con tabelle previsioni
    """
    mappa_anagrafica = df_anagrafica_completa.drop_duplicates(
        subset="codice"
    ).set_index("codice").to_dict("index")

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
                row[f"costo_comp_{m}_mesi"] = (
                    prob * row["Quantità totale"] * price
                    if prob and price else None
                )

            # Previsioni STAT
            pred_stat = json_predizioni_stat.get(modello, {}).get(stat_code, {})
            for m in mesi:
                prob = pred_stat.get(f"prev{m}")
                row[f"rottura_stat_{m}_mesi"] = prob
                row[f"ci_min_stat_{m}_mesi"] = pred_stat.get(f"prev{m}_lower")
                row[f"ci_max_stat_{m}_mesi"] = pred_stat.get(f"prev{m}_upper")
                row[f"costo_stat_{m}_mesi"] = (
                    prob * row["Quantità totale"] * price
                    if prob and price else None
                )

            dati.append(row)

        if dati:
            tabelle[modello] = pd.DataFrame(dati)

    return tabelle
