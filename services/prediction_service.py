"""
Prediction Service - Calcolo Previsioni di Affidabilità
Orchestrazione del calcolo delle previsioni per componenti e gruppi STAT
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from lifelines import KaplanMeierFitter
from scipy.interpolate import interp1d
from typing import Dict, List, Optional
import logging

from .statistical_service import (
    compute_riskset,
    best_prior_weibull,
    weibull_confidence_bands
)
from .chart_service import save_chart, create_reliability_chart

logger = logging.getLogger(__name__)


def precompute_all_predictions(
    df_affid: pd.DataFrame,
    modelli_topN: List[str],
    mesi_grid: np.ndarray = None,
    giorni_grid: np.ndarray = None,
    riskset_threshold: int = 1000,
    img_dir: str = "static/pred_charts"
) -> Dict:
    """
    Precalcola le curve di affidabilità per ogni componente di ogni modello.

    Args:
        df_affid: DataFrame con dati di affidabilità
        modelli_topN: Lista modelli da analizzare
        mesi_grid: Griglia mesi (default: 0-36)
        giorni_grid: Griglia giorni (default: mesi_grid * 30.42)
        riskset_threshold: Soglia minima risk set per affidabilità (default: 1000)
        img_dir: Directory salvataggio grafici (default: "static/pred_charts")

    Returns:
        Dizionario con previsioni per ogni modello e componente
        {
            "modello1": {
                "componente1": {
                    "componente": "ABC123",
                    "img_path": "/static/pred_charts/uuid.png",
                    "prev12": 0.05,
                    "prev24": 0.10,
                    ...
                },
                ...
            },
            ...
        }
    """
    if mesi_grid is None:
        mesi_grid = np.arange(0, 37)

    if giorni_grid is None:
        giorni_grid = mesi_grid * 30.42

    predizioni_json = {}
    total_comps = sum(
        df_affid[df_affid["Modello"] == m]["Codice Componente"].nunique()
        for m in modelli_topN
    )
    comp_counter = 0

    for modello in modelli_topN:
        logger.info(f'Inizio elaborazione modello: {modello}')
        predizioni_json[modello] = {}

        df_mod = df_affid[df_affid["Modello"] == modello]
        componenti = df_mod["Codice Componente"].unique()

        for componente in componenti:
            comp_counter += 1
            logger.debug(f"Componente {comp_counter}/{total_comps}: {modello} - {componente}")

            dati = df_mod[df_mod['Codice Componente'] == componente]
            if len(dati) == 0:
                continue

            # Prepara dati (censura a 1095 giorni = 3 anni)
            T = dati['Tempo di Vita'].clip(upper=1095).values
            E = np.where(dati['Tempo di Vita'] > 1095, 1, dati['Censura']).astype(int)

            # Risk set e ultimo mese affidabile
            risk_set = compute_riskset(T, mesi_grid)
            reliable_months = np.where(risk_set >= riskset_threshold)[0]
            last_reliable_month = int(reliable_months[-1]) if len(reliable_months) > 0 else 0

            # === Kaplan-Meier ===
            kmf = KaplanMeierFitter()
            kmf.fit(T, event_observed=1-E)

            surv_func = kmf.survival_function_
            ci = kmf.confidence_interval_

            # Ultima rottura osservata
            ultima_rottura = T[(E == 0)].max() if (E == 0).sum() > 0 else 0
            km_grid = giorni_grid[giorni_grid <= ultima_rottura]

            # Interpolazione Kaplan-Meier
            f_surv = interp1d(
                surv_func.index, surv_func.values.flatten(),
                bounds_error=False, fill_value=(1, surv_func.values[-1])
            )
            surv_km = f_surv(km_grid)

            f_surv_all = interp1d(
                surv_func.index, surv_func.values.flatten(),
                bounds_error=False, fill_value=(1, surv_func.values[-1])
            )
            km_surv = f_surv_all(giorni_grid)

            # Intervalli di confidenza KM
            f_lower = interp1d(
                ci.index, ci.iloc[:, 0].values,
                bounds_error=False, fill_value=(1, ci.iloc[-1, 0])
            )
            f_upper = interp1d(
                ci.index, ci.iloc[:, 1].values,
                bounds_error=False, fill_value=(1, ci.iloc[-1, 1])
            )
            km_ci_lower = f_lower(giorni_grid)
            km_ci_upper = f_upper(giorni_grid)

            # === Weibull Grid Search ===
            k_prior_grid = np.linspace(1.0, 1.2, 6)
            lambda_prior_grid = np.linspace(np.percentile(T, 60), np.percentile(T, 90), 8)

            (best_kprior, best_lambdaprior), k_map, lam_map = best_prior_weibull(
                T, E, km_grid, surv_km, k_prior_grid, lambda_prior_grid
            )

            weibull_surv = np.exp(- (giorni_grid / lam_map)**k_map)
            weibull_lower, weibull_upper = weibull_confidence_bands(
                T, E, k_map, lam_map, giorni_grid, n_boot=200
            )

            # === Calcolo Previsioni ===
            predizioni = {}
            for mesi in [12, 24, 36, last_reliable_month]:
                idx = int(np.searchsorted(mesi_grid, mesi))

                if idx >= len(weibull_surv):
                    # Out of bounds
                    predizioni[f"prev{mesi}"] = None
                    predizioni[f"prev{mesi}_lower"] = None
                    predizioni[f"prev{mesi}_upper"] = None
                    predizioni[f"prev{mesi}_km"] = None
                    predizioni[f"prev{mesi}_km_lower"] = None
                    predizioni[f"prev{mesi}_km_upper"] = None
                else:
                    # Probabilità di rottura = 1 - sopravvivenza
                    # ATTENZIONE: upper/lower sono invertiti per rottura vs sopravvivenza!
                    prob_rott = 1 - weibull_surv[idx]
                    prob_rott_low = 1 - weibull_upper[idx]
                    prob_rott_up = 1 - weibull_lower[idx]

                    prob_rott_km = 1 - km_surv[idx]
                    prob_rott_km_low = 1 - km_ci_upper[idx]
                    prob_rott_km_up = 1 - km_ci_lower[idx]

                    predizioni[f"prev{mesi}"] = float(prob_rott)
                    predizioni[f"prev{mesi}_lower"] = float(prob_rott_low)
                    predizioni[f"prev{mesi}_upper"] = float(prob_rott_up)
                    predizioni[f"prev{mesi}_km"] = float(prob_rott_km)
                    predizioni[f"prev{mesi}_km_lower"] = float(prob_rott_km_low)
                    predizioni[f"prev{mesi}_km_upper"] = float(prob_rott_km_up)

            predizioni["ultimo_mese_affidabile"] = int(last_reliable_month)

            # === Genera Grafico ===
            fig = create_reliability_chart(
                mesi_grid, km_surv, km_ci_lower, km_ci_upper,
                weibull_surv, weibull_lower, weibull_upper,
                last_reliable_month,
                title=f"Modello: {modello} - Componente: {componente}\nTuning curve"
            )
            img_path = save_chart(fig, img_dir)

            # Salva risultati
            predizioni_json[modello][componente] = {
                "componente": componente,
                "img_path": img_path,
                **predizioni
            }

    logger.info(f"Completate tutte le previsioni: {comp_counter} componenti elaborate")
    return predizioni_json


def precompute_all_predictions_by_stat(
    df_affid_with_stat: pd.DataFrame,
    modelli_topN: List[str],
    mesi_grid: np.ndarray = None,
    giorni_grid: np.ndarray = None,
    riskset_threshold: int = 1000,
    img_dir: str = "static/pred_charts_stat"
) -> Dict:
    """
    Precalcola le curve di affidabilità per ogni GRUPPO STAT di ogni modello.

    Args:
        df_affid_with_stat: DataFrame con colonna 'stat'
        modelli_topN: Lista modelli da analizzare
        mesi_grid: Griglia mesi (default: 0-36)
        giorni_grid: Griglia giorni (default: mesi_grid * 30.42)
        riskset_threshold: Soglia minima risk set (default: 1000)
        img_dir: Directory grafici (default: "static/pred_charts_stat")

    Returns:
        Dizionario con previsioni per ogni modello e codice STAT
    """
    if mesi_grid is None:
        mesi_grid = np.arange(0, 37)

    if giorni_grid is None:
        giorni_grid = mesi_grid * 30.42

    predizioni_json = {}

    # Filtra e conta gruppi STAT
    df_filtered = df_affid_with_stat[
        df_affid_with_stat["Modello"].isin(modelli_topN)
    ].dropna(subset=['stat'])

    total_stats = df_filtered.groupby("Modello")['stat'].nunique().sum()
    stat_counter = 0

    for modello in modelli_topN:
        logger.info(f'Inizio elaborazione modello (per STAT): {modello}')
        predizioni_json[modello] = {}

        df_mod = df_filtered[df_filtered["Modello"] == modello]
        stat_codes = df_mod["stat"].unique()

        for stat_code in stat_codes:
            stat_counter += 1
            logger.debug(f"Gruppo STAT {stat_counter}/{total_stats}: {modello} - {stat_code}")

            dati = df_mod[df_mod['stat'] == stat_code]
            if len(dati) < 10:  # Salta se troppo pochi dati
                continue

            # Prepara dati
            T = dati['Tempo di Vita'].clip(upper=1095).values
            E = np.where(dati['Tempo di Vita'] > 1095, 1, dati['Censura']).astype(int)

            # Risk set
            risk_set = compute_riskset(T, mesi_grid)
            reliable_months = np.where(risk_set >= riskset_threshold)[0]
            last_reliable_month = int(reliable_months[-1]) if len(reliable_months) > 0 else 0

            # === Kaplan-Meier (codice identico a precompute_all_predictions) ===
            kmf = KaplanMeierFitter()
            kmf.fit(T, event_observed=1-E)

            surv_func = kmf.survival_function_
            ci = kmf.confidence_interval_
            ultima_rottura = T[(E == 0)].max() if (E == 0).sum() > 0 else 0
            km_grid = giorni_grid[giorni_grid <= ultima_rottura]

            f_surv = interp1d(
                surv_func.index, surv_func.values.flatten(),
                bounds_error=False, fill_value=(1, surv_func.values[-1])
            )
            surv_km = f_surv(km_grid)

            f_surv_all = interp1d(
                surv_func.index, surv_func.values.flatten(),
                bounds_error=False, fill_value=(1, surv_func.values[-1])
            )
            km_surv = f_surv_all(giorni_grid)

            f_lower = interp1d(
                ci.index, ci.iloc[:, 0].values,
                bounds_error=False, fill_value=(1, ci.iloc[-1, 0])
            )
            f_upper = interp1d(
                ci.index, ci.iloc[:, 1].values,
                bounds_error=False, fill_value=(1, ci.iloc[-1, 1])
            )
            km_ci_lower = f_lower(giorni_grid)
            km_ci_upper = f_upper(giorni_grid)

            # === Weibull ===
            k_prior_grid = np.linspace(1.0, 1.2, 6)
            lambda_prior_grid = np.linspace(np.percentile(T, 60), np.percentile(T, 90), 8)

            (best_kprior, best_lambdaprior), k_map, lam_map = best_prior_weibull(
                T, E, km_grid, surv_km, k_prior_grid, lambda_prior_grid
            )

            weibull_surv = np.exp(- (giorni_grid / lam_map)**k_map)
            weibull_lower, weibull_upper = weibull_confidence_bands(
                T, E, k_map, lam_map, giorni_grid, n_boot=200
            )

            # === Previsioni ===
            predizioni = {}
            for mesi in [12, 24, 36, last_reliable_month]:
                idx = int(np.searchsorted(mesi_grid, mesi))

                if idx < len(weibull_surv):
                    prob_rott = 1 - weibull_surv[idx]
                    prob_rott_low = 1 - weibull_upper[idx]
                    prob_rott_up = 1 - weibull_lower[idx]

                    predizioni[f"prev{mesi}"] = float(prob_rott)
                    predizioni[f"prev{mesi}_lower"] = float(prob_rott_low)
                    predizioni[f"prev{mesi}_upper"] = float(prob_rott_up)

            predizioni["ultimo_mese_affidabile"] = int(last_reliable_month)

            # === Grafico ===
            fig = create_reliability_chart(
                mesi_grid, km_surv, km_ci_lower, km_ci_upper,
                weibull_surv, weibull_lower, weibull_upper,
                last_reliable_month,
                title=f"Modello: {modello} - Gruppo STAT: {stat_code}\nTuning curve"
            )
            img_path = save_chart(fig, img_dir)

            # Salva risultati
            predizioni_json[modello][stat_code] = {
                "stat_code": stat_code,
                "img_path": img_path,
                **predizioni
            }

    logger.info(f"Completate tutte le previsioni per STAT: {stat_counter} gruppi elaborati")
    return predizioni_json
