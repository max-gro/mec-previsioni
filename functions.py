import numpy as np
import matplotlib.pyplot as plt
try:
    from lifelines import KaplanMeierFitter
    LIFELINES_AVAILABLE = True
except ImportError:
    LIFELINES_AVAILABLE = False
    print("[WARNING] lifelines non installato - funzionalità previsioni disabilitate")
from scipy.optimize import minimize
from scipy.interpolate import interp1d
import numpy as np
import os, uuid

def weibull_logpost(params, data, cens, k_prior, lambda_prior, k_var, lambda_var):
    k, lam = params
    if k <= 0 or lam <= 0:
        return np.inf
    events = (cens == 0)
    censored = (cens == 1)
    loglike = (
        np.sum(np.log(k/lam) + (k-1)*np.log(data[events]/lam) - (data[events]/lam)**k) +
        np.sum(- (data[censored]/lam)**k)
    )
    logprior = -((np.log(k) - np.log(k_prior))**2 / (2*k_var) + (np.log(lam) - np.log(lambda_prior))**2 / (2*lambda_var))
    return -(loglike + logprior)

def fit_weibull_and_score(T, E, km_grid, surv_km, k_prior, lambda_prior, k_var, lambda_var):
    res = minimize(weibull_logpost, x0=[k_prior, lambda_prior], args=(T, E, k_prior, lambda_prior, k_var, lambda_var),
                bounds=[(0.1,10),(10,10000)])
    k_map, lam_map = res.x
    weibull_surv = np.exp(- (km_grid / lam_map)**k_map)
    error = np.mean((weibull_surv - surv_km)**2)
    return error, k_map, lam_map

def best_prior_weibull(T, E, km_grid, surv_km, k_prior_grid, lambda_prior_grid, k_var=0.05, lambda_var=0.15):
    best_score = np.inf
    best_params = None
    best_kmap = None
    best_lammap = None
    for k_p in k_prior_grid:
        for l_p in lambda_prior_grid:
            error, k_map, lam_map = fit_weibull_and_score(T, E, km_grid, surv_km, k_p, l_p, k_var, lambda_var)
            if error < best_score:
                best_score = error
                best_params = (k_p, l_p)
                best_kmap = k_map
                best_lammap = lam_map
    return best_params, best_kmap, best_lammap

def compute_riskset(T, mesi_grid):
    return np.array([(T >= m*30.42).sum() for m in mesi_grid])

def weibull_confidence_bands(T, E, k_map, lam_map, giorni_grid, n_boot=200, k_var=0.05, lambda_var=0.15):
    k_samples = np.random.normal(k_map, np.sqrt(k_var), n_boot)
    lam_samples = np.random.normal(lam_map, np.sqrt(lambda_var)*lam_map/lam_map, n_boot)
    k_samples = k_samples[k_samples > 0]
    lam_samples = lam_samples[lam_samples > 0]
    weibull_array = []
    for k, lam in zip(np.random.choice(k_samples, n_boot), np.random.choice(lam_samples, n_boot)):
        weibull_array.append(np.exp(- (giorni_grid / lam)**k))
    weibull_array = np.array(weibull_array)
    weibull_lower = np.percentile(weibull_array, 2.5, axis=0)
    weibull_upper = np.percentile(weibull_array, 97.5, axis=0)
    return weibull_lower, weibull_upper

def save_chart(fig, img_dir):
    img_id = str(uuid.uuid4()) + ".png"
    img_path = os.path.join(img_dir, img_id)
    fig.savefig(img_path, bbox_inches="tight")
    plt.close(fig)
    return "/" + img_path.replace("\\", "/")

def precompute_all_predictions(
    df_affid,
    modelli_topN,
    mesi_grid=np.arange(0,37),
    giorni_grid=None,
    riskset_threshold=1000,
    img_dir="static/pred_charts"
):
    """
    Precalcola le curve di affidabilità per ogni componente di ogni modello.
    Salva:
      - curve di sopravvivenza Kaplan-Meier e Weibull per ogni mese (0...36)
      - intervalli di confidenza
      - ultimo mese affidabile
      - grafico salvato per ogni componente
    """
    import matplotlib.pyplot as plt
    from lifelines import KaplanMeierFitter
    from scipy.optimize import minimize
    from scipy.interpolate import interp1d
    import os, uuid

    # ... (tieni le funzioni interne come sono ora: weibull_logpost, fit_weibull_and_score, best_prior_weibull, compute_riskset, weibull_confidence_bands, save_chart) ...

    if giorni_grid is None:
        giorni_grid = mesi_grid * 30.42

    predizioni_json = {}
    total_comps = sum(df_affid[df_affid["Modello"] == m]["Codice Componente"].nunique() for m in modelli_topN)
    comp_counter = 0

    for modello in modelli_topN:
        print(f'INIZIO MODELLO {modello}')
        predizioni_json[modello] = {}
        df_mod = df_affid[df_affid["Modello"] == modello]
        componenti = df_mod["Codice Componente"].unique()
        for componente in componenti:
            comp_counter += 1
            print(f"Componente {comp_counter}/{total_comps}: {modello} - {componente}")
            dati = df_mod[df_mod['Codice Componente'] == componente]
            if len(dati) == 0:
                continue

            T = dati['Tempo di Vita'].clip(upper=1095).values
            E = np.where(dati['Tempo di Vita'] > 1095, 1, dati['Censura']).astype(int)
            risk_set = compute_riskset(T, mesi_grid)
            reliable_months = np.where(risk_set >= riskset_threshold)[0]
            last_reliable_month = int(reliable_months[-1]) if len(reliable_months)>0 else 0

            # Kaplan-Meier
            kmf = KaplanMeierFitter()
            kmf.fit(T, event_observed=1-E)
            surv_func = kmf.survival_function_
            ci = kmf.confidence_interval_
            ultima_rottura = T[(E == 0)].max() if (E == 0).sum() > 0 else 0
            km_grid = giorni_grid[giorni_grid <= ultima_rottura]
            f_surv = interp1d(surv_func.index, surv_func.values.flatten(), bounds_error=False, fill_value=(1,surv_func.values[-1]))
            surv_km = f_surv(km_grid)
            f_surv_all = interp1d(surv_func.index, surv_func.values.flatten(), bounds_error=False, fill_value=(1, surv_func.values[-1]))
            km_surv = f_surv_all(giorni_grid)
            f_lower = interp1d(ci.index, ci.iloc[:,0].values, bounds_error=False, fill_value=(1,ci.iloc[-1,0]))
            f_upper = interp1d(ci.index, ci.iloc[:,1].values, bounds_error=False, fill_value=(1,ci.iloc[-1,1]))
            km_ci_lower = f_lower(giorni_grid)
            km_ci_upper = f_upper(giorni_grid)

            # Grid search per Weibull
            k_prior_grid = np.linspace(1.0, 1.2, 6)
            lambda_prior_grid = np.linspace(np.percentile(T,60), np.percentile(T,90), 8)
            (best_kprior, best_lambdaprior), k_map, lam_map = best_prior_weibull(
                T, E, km_grid, surv_km, k_prior_grid, lambda_prior_grid
            )
            weibull_surv = np.exp(- (giorni_grid / lam_map)**k_map)
            weibull_lower, weibull_upper = weibull_confidence_bands(T, E, k_map, lam_map, giorni_grid, n_boot=200)

            # Previsione solo in termini di probabilità di rottura (1-sopravvivenza)
            predizioni = {}
            for mesi in [12, 24, 36, last_reliable_month]:
                idx = int(np.searchsorted(mesi_grid, mesi))
                if idx >= len(weibull_surv):
                    predizioni[f"prev{mesi}"] = None
                    predizioni[f"prev{mesi}_lower"] = None
                    predizioni[f"prev{mesi}_upper"] = None
                    predizioni[f"prev{mesi}_km"] = None
                    predizioni[f"prev{mesi}_km_lower"] = None
                    predizioni[f"prev{mesi}_km_upper"] = None
                else:
                    # Weibull
                    prob_rott = 1 - weibull_surv[idx]
                    prob_rott_low = 1 - weibull_upper[idx]    # ATTENZIONE: upper/lower sono sugli intervalli di SOPRAVVIVENZA!
                    prob_rott_up  = 1 - weibull_lower[idx]
                    # Kaplan-Meier
                    prob_rott_km = 1 - km_surv[idx]
                    prob_rott_km_low = 1 - km_ci_upper[idx]
                    prob_rott_km_up  = 1 - km_ci_lower[idx]
                    predizioni[f"prev{mesi}"] = float(prob_rott)
                    predizioni[f"prev{mesi}_lower"] = float(prob_rott_low)
                    predizioni[f"prev{mesi}_upper"] = float(prob_rott_up)
                    predizioni[f"prev{mesi}_km"] = float(prob_rott_km)
                    predizioni[f"prev{mesi}_km_lower"] = float(prob_rott_km_low)
                    predizioni[f"prev{mesi}_km_upper"] = float(prob_rott_km_up)
            predizioni["ultimo_mese_affidabile"] = int(last_reliable_month)

            # Plot e salva grafico
            fig = plt.figure(figsize=(9,5))
            plt.step(mesi_grid, km_surv, label='Kaplan-Meier', where='post', color='C0')
            plt.fill_between(mesi_grid, km_ci_lower, km_ci_upper, color='C0', alpha=0.20, step='post', label='KM 95% CI')
            plt.plot(mesi_grid, weibull_surv, 'r--', label='Weibull tuned')
            plt.fill_between(mesi_grid, weibull_lower, weibull_upper, color='r', alpha=0.15, label='Weibull 95% CI')
            plt.axvline(last_reliable_month, color='orange', linestyle='-.', label=f'Stima affidabile fino a {last_reliable_month} mesi')
            plt.xlabel("Mesi")
            plt.ylabel("Probabilità di sopravvivenza")
            plt.title(f"Modello: {modello} - Componente: {componente}\nTuning curve")
            plt.legend()
            plt.ylim(0.85, 1.01)
            plt.xlim(0,36)
            plt.tight_layout()
            img_path = save_chart(fig, img_dir)

            predizioni_json[modello][componente] = {
                "componente": componente,
                "img_path": img_path,
                **predizioni
            }

    print(f"COMPLETATE TUTTE LE PREVISIONI: {comp_counter} componenti elaborate.")
    return predizioni_json

def precompute_all_predictions_by_stat(
    df_affid_with_stat, # Richiede un df con la colonna 'stat'
    modelli_topN,
    mesi_grid=np.arange(0,37),
    giorni_grid=None,
    riskset_threshold=1000,
    img_dir="static/pred_charts_stat" # Salva i grafici in una cartella separata
):
    """
    Precalcola le curve di affidabilità per ogni GRUPPO STAT di ogni modello.
    """
    import matplotlib.pyplot as plt
    from lifelines import KaplanMeierFitter
    from scipy.optimize import minimize
    from scipy.interpolate import interp1d
    import os, uuid

    # Crea la directory per i grafici se non esiste
    if not os.path.exists(img_dir):
        os.makedirs(img_dir)

    # Assicurati che le funzioni helper siano definite o importate qui
    # (weibull_logpost, fit_weibull_and_score, ecc.)

    if giorni_grid is None:
        giorni_grid = mesi_grid * 30.42

    predizioni_json = {}
    
    # Calcola il numero totale di gruppi STAT da elaborare
    df_filtered = df_affid_with_stat[df_affid_with_stat["Modello"].isin(modelli_topN)].dropna(subset=['stat'])
    total_stats = df_filtered.groupby("Modello")['stat'].nunique().sum()
    stat_counter = 0

    for modello in modelli_topN:
        print(f'\nINIZIO MODELLO {modello} (per STAT)')
        predizioni_json[modello] = {}
        df_mod = df_filtered[df_filtered["Modello"] == modello]
        
        stat_codes = df_mod["stat"].unique()

        for stat_code in stat_codes:
            stat_counter += 1
            print(f"Gruppo STAT {stat_counter}/{total_stats}: {modello} - {stat_code}")
            
            dati = df_mod[df_mod['stat'] == stat_code]
            if len(dati) < 10: # Salta se ci sono pochissimi dati
                continue

            T = dati['Tempo di Vita'].clip(upper=1095).values
            E = np.where(dati['Tempo di Vita'] > 1095, 1, dati['Censura']).astype(int)
            risk_set = compute_riskset(T, mesi_grid)
            reliable_months = np.where(risk_set >= riskset_threshold)[0]
            last_reliable_month = int(reliable_months[-1]) if len(reliable_months)>0 else 0

            # Kaplan-Meier (codice identico a prima)
            kmf = KaplanMeierFitter()
            kmf.fit(T, event_observed=1-E)
            surv_func = kmf.survival_function_
            ci = kmf.confidence_interval_
            ultima_rottura = T[(E == 0)].max() if (E == 0).sum() > 0 else 0
            km_grid = giorni_grid[giorni_grid <= ultima_rottura]
            f_surv = interp1d(surv_func.index, surv_func.values.flatten(), bounds_error=False, fill_value=(1,surv_func.values[-1]))
            surv_km = f_surv(km_grid)
            f_surv_all = interp1d(surv_func.index, surv_func.values.flatten(), bounds_error=False, fill_value=(1, surv_func.values[-1]))
            km_surv = f_surv_all(giorni_grid)
            f_lower = interp1d(ci.index, ci.iloc[:,0].values, bounds_error=False, fill_value=(1,ci.iloc[-1,0]))
            f_upper = interp1d(ci.index, ci.iloc[:,1].values, bounds_error=False, fill_value=(1,ci.iloc[-1,1]))
            km_ci_lower = f_lower(giorni_grid)
            km_ci_upper = f_upper(giorni_grid)

            # Grid search per Weibull (codice identico a prima)
            k_prior_grid = np.linspace(1.0, 1.2, 6)
            lambda_prior_grid = np.linspace(np.percentile(T,60), np.percentile(T,90), 8)
            (best_kprior, best_lambdaprior), k_map, lam_map = best_prior_weibull(
                T, E, km_grid, surv_km, k_prior_grid, lambda_prior_grid
            )
            weibull_surv = np.exp(- (giorni_grid / lam_map)**k_map)
            weibull_lower, weibull_upper = weibull_confidence_bands(T, E, k_map, lam_map, giorni_grid, n_boot=200)

            # Previsioni (codice identico a prima)
            predizioni = {}
            for mesi in [12, 24, 36, last_reliable_month]:
                # ... (stesso codice di calcolo previsioni)
                idx = int(np.searchsorted(mesi_grid, mesi))
                if idx < len(weibull_surv):
                    prob_rott = 1 - weibull_surv[idx]
                    prob_rott_low = 1 - weibull_upper[idx]
                    prob_rott_up  = 1 - weibull_lower[idx]
                    predizioni[f"prev{mesi}"] = float(prob_rott)
                    predizioni[f"prev{mesi}_lower"] = float(prob_rott_low)
                    predizioni[f"prev{mesi}_upper"] = float(prob_rott_up)
            predizioni["ultimo_mese_affidabile"] = int(last_reliable_month)

            # Plot e salva grafico
            fig = plt.figure(figsize=(9,5))
            plt.step(mesi_grid, km_surv, label='Kaplan-Meier', where='post', color='C0')
            plt.fill_between(mesi_grid, km_ci_lower, km_ci_upper, color='C0', alpha=0.20, step='post', label='KM 95% CI')
            plt.plot(mesi_grid, weibull_surv, 'r--', label='Weibull tuned')
            plt.fill_between(mesi_grid, weibull_lower, weibull_upper, color='r', alpha=0.15, label='Weibull 95% CI')
            plt.axvline(last_reliable_month, color='orange', linestyle='-.', label=f'Stima affidabile fino a {last_reliable_month} mesi')
            plt.xlabel("Mesi")
            plt.ylabel("Probabilità di sopravvivenza")
            # Titolo del grafico modificato
            plt.title(f"Modello: {modello} - Gruppo STAT: {stat_code}\nTuning curve")
            plt.legend()
            plt.ylim(0.85, 1.01)
            plt.xlim(0,36)
            plt.tight_layout()
            img_path = save_chart(fig, img_dir)

            # Salva i risultati indicizzati per codice STAT
            predizioni_json[modello][stat_code] = {
                "stat_code": stat_code,
                "img_path": img_path,
                **predizioni
            }

    print(f"\nCOMPLETATE TUTTE LE PREVISIONI PER STAT: {stat_counter} gruppi elaborati.")
    return predizioni_json

