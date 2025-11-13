# preprocessing.py
import pandas as pd
import numpy as np
import json

def build_df_componenti(modelli, json_per_data):
    """
    Crea un DataFrame con tutte le componenti (modello, codice, data acquisto, quantità) per i modelli richiesti.
    """
    records = []
    for modello in modelli:
        if modello not in json_per_data:
            continue
        for lotto in json_per_data[modello]:
            data_lotto = lotto["data"]
            for codice_comp, qta in lotto.get("componenti", {}).items():
                records.append({
                    "Modello": modello,
                    "Codice Componente": codice_comp,
                    "Data Acquisto": data_lotto,
                    "Quantità": qta
                })
    return pd.DataFrame(records)

# def build_df_affid_old(df_componenti, df_rotture, data_censura="2024-12-31"):
#     """
#     Costruisce il dataset di affidabilità (eventi/censure) partendo dalle componenti e dalle rotture note.
#     """
#     df_componenti = df_componenti.copy()
#     df_rotture = df_rotture.copy()
#     df_componenti["Data Acquisto"] = pd.to_datetime(df_componenti["Data Acquisto"], dayfirst=True, errors="coerce")
#     df_rotture["Data Apertura"] = pd.to_datetime(df_rotture["Data Apertura"], dayfirst=True, errors="coerce")
#     modelli = df_componenti["Modello"].unique().tolist()
#     df_rotture2 = df_rotture[df_rotture["Modello"].isin(modelli)]
#     records = []
#     stock = df_componenti.copy()
#     stock["Residuo"] = stock["Quantità"]

#     # Associa rottura a lotto di produzione (FIFO)
#     for idx, rottura in df_rotture2.iterrows():
#         modello = rottura["Modello"]
#         codice = rottura["Codice Componente"]
#         data_rottura = rottura["Data Apertura"]
#         possibili = stock[
#             (stock["Modello"] == modello) &
#             (stock["Codice Componente"] == codice) &
#             (stock["Data Acquisto"] <= data_rottura) &
#             (stock["Residuo"] > 0)
#         ].sort_values("Data Acquisto")
#         if len(possibili) == 0:
#             continue
#         idx_disp = possibili.index[0]
#         stock.at[idx_disp, "Residuo"] -= 1
#         data_acq = stock.at[idx_disp, "Data Acquisto"]
#         tempo_vita = (data_rottura - data_acq).days
#         records.append({
#             "Modello": modello,
#             "Codice Componente": codice,
#             "Data Acquisto": data_acq,
#             "Data Rottura": data_rottura,
#             "Tempo di Vita": tempo_vita,
#             "Censura": 0  # Evento osservato (rottura)
#         })

#     # Inserisci componenti censurate (non rotte al 31/12/2024)
#     data_censura = pd.to_datetime(data_censura)
#     for idx, row in stock.iterrows():
#         for _ in range(int(row["Residuo"])):

#             # Calcola tempo di vita alla data di censura
#             #tempo_vita = (data_censura - row["Data Acquisto"]).days
#             data_acq = row.get("Data Acquisto")
#             # Normalizza o salta righe invalide
#             if pd.isna(data_acq):
#                 return None  # oppure continua, a seconda del ciclo
#             if isinstance(data_acq, str):
#                 try:
#                     data_acq = pd.to_datetime(data_acq, errors='coerce')
#                 except Exception:
#                     return None
#             if pd.isna(data_acq):
#                 return None
#             ## Ora sicuro che siano date
#             #tempo_vita = (data_censura - data_acq).days
#             data_censura = pd.to_datetime(data_censura, errors='coerce')
#             data_acq = pd.to_datetime(data_acq, errors='coerce')

#             if pd.isna(data_censura) or pd.isna(data_acq):
#                 tempo_vita = None
#             else:
#                 tempo_vita = (data_censura - data_acq).days

#             if tempo_vita < 0:
#                 continue  # produzione dopo data censura
#             records.append({
#                 "Modello": row["Modello"],
#                 "Codice Componente": row["Codice Componente"],
#                 "Data Acquisto": row["Data Acquisto"],
#                 "Data Rottura": None,
#                 "Tempo di Vita": tempo_vita,
#                 "Censura": 1  # censurato
#             })
#     return pd.DataFrame(records)


def build_df_affid(df_componenti, df_rotture, data_censura="2024-12-31"):
    """
    Costruisce il dataset di affidabilità (eventi/censure) partendo dalle componenti e dalle rotture note.
    """
    df_componenti = df_componenti.copy()
    df_rotture = df_rotture.copy()
    df_componenti["Data Acquisto"] = pd.to_datetime(df_componenti["Data Acquisto"], dayfirst=True, errors="coerce")
    df_rotture["Data Apertura"] = pd.to_datetime(df_rotture["Data Apertura"], dayfirst=True, errors="coerce")
    modelli = df_componenti["Modello"].unique().tolist()
    df_rotture2 = df_rotture[df_rotture["Modello"].isin(modelli)]
    records = []
    stock = df_componenti.copy()
    stock["Residuo"] = stock["Quantità"]

    # Associa rottura a lotto di produzione (FIFO)
    for idx, rottura in df_rotture2.iterrows():
        modello = rottura["Modello"]
        codice = rottura["Codice Componente"]
        data_rottura = rottura["Data Apertura"]
        possibili = stock[
            (stock["Modello"] == modello) &
            (stock["Codice Componente"] == codice) &
            (stock["Data Acquisto"] <= data_rottura) &
            (stock["Residuo"] > 0)
        ].sort_values("Data Acquisto")
        if len(possibili) == 0:
            continue
        idx_disp = possibili.index[0]
        stock.at[idx_disp, "Residuo"] -= 1
        data_acq = stock.at[idx_disp, "Data Acquisto"]
        tempo_vita = (data_rottura - data_acq).days
        records.append({
            "Modello": modello,
            "Codice Componente": codice,
            "Data Acquisto": data_acq,
            "Data Rottura": data_rottura,
            "Tempo di Vita": tempo_vita,
            "Censura": 0  # Evento osservato (rottura)
        })

    # Inserisci componenti censurate (non rotte al 31/12/2024) - OTTIMIZZATO
    data_censura = pd.to_datetime(data_censura, errors='coerce')
																
    
    # Filtra e prepara dati in bulk
    stock_censured = stock[stock["Residuo"] > 0].copy()
    stock_censured["Data Acquisto"] = pd.to_datetime(stock_censured["Data Acquisto"], errors='coerce')
    stock_censured = stock_censured.dropna(subset=["Data Acquisto"])
    stock_censured["Tempo di Vita"] = (data_censura - stock_censured["Data Acquisto"]).dt.days
    stock_censured = stock_censured[stock_censured["Tempo di Vita"] >= 0]
    
    # Espandi righe in base a Residuo
    for _, row in stock_censured.iterrows():
        residuo = int(row["Residuo"])
        if residuo <= 0:
            continue
        # Batch append per performance
        batch = [{
            "Modello": row["Modello"],
            "Codice Componente": row["Codice Componente"],
            "Data Acquisto": row["Data Acquisto"],
            "Data Rottura": None,
            "Tempo di Vita": row["Tempo di Vita"],
            "Censura": 1
        } for _ in range(residuo)]
        records.extend(batch)
    
    return pd.DataFrame(records)

def tronca_affidabilita(df_affid, max_mesi=36):
    """
    Tronca il tempo di vita a max_mesi (es: 36 mesi), crea flag di censura troncata.
    """
    MAX_GIORNI = max_mesi * 30.44
    df = df_affid.copy()
    df["Tempo di Vita Troncato"] = np.minimum(df["Tempo di Vita"], MAX_GIORNI)
    df["Censura Troncata"] = (
        (df["Tempo di Vita"] > MAX_GIORNI) | (df["Censura"] == 1)
    ).astype(int)
    return df

def get_componenti_stat_modello(modello, quantita, json_data):
    """
    Estrae componenti e stat per un modello, calcolando anche la quantità totale.
    """
    if modello not in json_data:
        return pd.DataFrame(), pd.DataFrame()
    componenti = json_data[modello].get("componenti", {})
    comp_records = []
    for codice_comp, qta in componenti.items():
        comp_records.append({
            "Codice": codice_comp,
            "Quantità per modello": qta,
            "Quantità totale lotto": qta * quantita
        })
    stat = json_data[modello].get("stat", {})
    stat_records = []
    for codice_stat, qta in stat.items():
        stat_records.append({
            "Codice": codice_stat,
            "Quantità per modello": qta,
            "Quantità totale lotto": qta * quantita
        })
    df_comp = pd.DataFrame(comp_records)
    df_stat = pd.DataFrame(stat_records)
    return df_comp, df_stat

def compute_comp_quantities_map(modelli, json_data, quantity=1):
    """
    Restituisce un dict {modello: {componente: quantità totale per lotto}} utile per precomputing predizioni.
    """
    comp_quantities_map = {}
    for m in modelli:
        comp_quantities_map[m] = {}
        comp, _ = get_componenti_stat_modello(m, quantity, json_data)
        for row in comp.to_dict("records"):
            comp_quantities_map[m][row["Codice"]] = row["Quantità totale lotto"]
    return comp_quantities_map

def save_json(obj, path):
    """
    Utility per salvare un oggetto Python in JSON con indentazione.
    """
    with open(path, "w") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
