"""
Statistical Service - Analisi di Sopravvivenza
Contiene funzioni per analisi Weibull e Kaplan-Meier
"""

import numpy as np
from scipy.optimize import minimize
from typing import Tuple, Optional


def weibull_logpost(
    params: Tuple[float, float],
    data: np.ndarray,
    cens: np.ndarray,
    k_prior: float,
    lambda_prior: float,
    k_var: float,
    lambda_var: float
) -> float:
    """
    Calcola la log-posterior Weibull (negativa, per minimizzazione)

    Args:
        params: Tupla (k, lambda) parametri Weibull
        data: Array tempi di vita
        cens: Array censure (0=evento, 1=censurato)
        k_prior: Prior per parametro k (shape)
        lambda_prior: Prior per parametro lambda (scale)
        k_var: Varianza prior k
        lambda_var: Varianza prior lambda

    Returns:
        Negative log-posterior (per minimizzazione)
    """
    k, lam = params

    # Validazione parametri
    if k <= 0 or lam <= 0:
        return np.inf

    # Separa eventi e censure
    events = (cens == 0)
    censored = (cens == 1)

    # Log-likelihood
    loglike = (
        np.sum(np.log(k/lam) + (k-1)*np.log(data[events]/lam) - (data[events]/lam)**k) +
        np.sum(- (data[censored]/lam)**k)
    )

    # Log-prior (distribuzione log-normale)
    logprior = -(
        (np.log(k) - np.log(k_prior))**2 / (2*k_var) +
        (np.log(lam) - np.log(lambda_prior))**2 / (2*lambda_var)
    )

    return -(loglike + logprior)


def fit_weibull_and_score(
    T: np.ndarray,
    E: np.ndarray,
    km_grid: np.ndarray,
    surv_km: np.ndarray,
    k_prior: float,
    lambda_prior: float,
    k_var: float,
    lambda_var: float
) -> Tuple[float, float, float]:
    """
    Fit del modello Weibull e calcolo score (MSE con Kaplan-Meier)

    Args:
        T: Tempi di vita
        E: Eventi (0=evento, 1=censurato)
        km_grid: Griglia temporale per confronto
        surv_km: Sopravvivenza Kaplan-Meier sulla griglia
        k_prior: Prior parametro k
        lambda_prior: Prior parametro lambda
        k_var: Varianza prior k
        lambda_var: Varianza prior lambda

    Returns:
        Tupla (error, k_map, lam_map)
            - error: Mean squared error tra Weibull e KM
            - k_map: Parametro k stimato (MAP)
            - lam_map: Parametro lambda stimato (MAP)
    """
    # Ottimizzazione
    res = minimize(
        weibull_logpost,
        x0=[k_prior, lambda_prior],
        args=(T, E, k_prior, lambda_prior, k_var, lambda_var),
        bounds=[(0.1, 10), (10, 10000)]
    )

    k_map, lam_map = res.x

    # Calcola curva Weibull con parametri stimati
    weibull_surv = np.exp(- (km_grid / lam_map)**k_map)

    # Errore quadratico medio
    error = np.mean((weibull_surv - surv_km)**2)

    return error, k_map, lam_map


def best_prior_weibull(
    T: np.ndarray,
    E: np.ndarray,
    km_grid: np.ndarray,
    surv_km: np.ndarray,
    k_prior_grid: np.ndarray,
    lambda_prior_grid: np.ndarray,
    k_var: float = 0.05,
    lambda_var: float = 0.15
) -> Tuple[Tuple[float, float], float, float]:
    """
    Grid search per trovare i migliori prior Weibull

    Args:
        T: Tempi di vita
        E: Eventi (0=evento, 1=censurato)
        km_grid: Griglia temporale
        surv_km: Sopravvivenza Kaplan-Meier
        k_prior_grid: Griglia valori prior k
        lambda_prior_grid: Griglia valori prior lambda
        k_var: Varianza prior k (default: 0.05)
        lambda_var: Varianza prior lambda (default: 0.15)

    Returns:
        Tupla ((best_k_prior, best_lambda_prior), k_map, lam_map)
    """
    best_score = np.inf
    best_params = None
    best_kmap = None
    best_lammap = None

    for k_p in k_prior_grid:
        for l_p in lambda_prior_grid:
            error, k_map, lam_map = fit_weibull_and_score(
                T, E, km_grid, surv_km, k_p, l_p, k_var, lambda_var
            )

            if error < best_score:
                best_score = error
                best_params = (k_p, l_p)
                best_kmap = k_map
                best_lammap = lam_map

    return best_params, best_kmap, best_lammap


def compute_riskset(T: np.ndarray, mesi_grid: np.ndarray) -> np.ndarray:
    """
    Calcola il risk set (numero di unità ancora a rischio) per ogni mese

    Args:
        T: Tempi di vita in giorni
        mesi_grid: Griglia mesi per cui calcolare il risk set

    Returns:
        Array con numero di unità a rischio per ogni mese
    """
    return np.array([(T >= m * 30.42).sum() for m in mesi_grid])


def weibull_confidence_bands(
    T: np.ndarray,
    E: np.ndarray,
    k_map: float,
    lam_map: float,
    giorni_grid: np.ndarray,
    n_boot: int = 200,
    k_var: float = 0.05,
    lambda_var: float = 0.15
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Calcola bande di confidenza Weibull tramite bootstrap parametrico

    Args:
        T: Tempi di vita
        E: Eventi
        k_map: Parametro k stimato
        lam_map: Parametro lambda stimato
        giorni_grid: Griglia temporale in giorni
        n_boot: Numero iterazioni bootstrap (default: 200)
        k_var: Varianza k
        lambda_var: Varianza lambda

    Returns:
        Tupla (weibull_lower, weibull_upper)
            - weibull_lower: Percentile 2.5% (banda inferiore)
            - weibull_upper: Percentile 97.5% (banda superiore)
    """
    # Genera campioni dai prior
    k_samples = np.random.normal(k_map, np.sqrt(k_var), n_boot)
    lam_samples = np.random.normal(lam_map, np.sqrt(lambda_var) * lam_map / lam_map, n_boot)

    # Filtra valori invalidi
    k_samples = k_samples[k_samples > 0]
    lam_samples = lam_samples[lam_samples > 0]

    # Genera curve Weibull con parametri campionati
    weibull_array = []
    for k, lam in zip(
        np.random.choice(k_samples, n_boot),
        np.random.choice(lam_samples, n_boot)
    ):
        weibull_array.append(np.exp(- (giorni_grid / lam)**k))

    weibull_array = np.array(weibull_array)

    # Calcola percentili
    weibull_lower = np.percentile(weibull_array, 2.5, axis=0)
    weibull_upper = np.percentile(weibull_array, 97.5, axis=0)

    return weibull_lower, weibull_upper
