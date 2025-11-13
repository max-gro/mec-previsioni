"""
Chart Service - Generazione Grafici
Gestisce la creazione e salvataggio dei grafici di affidabilità
"""

import os
import uuid
import matplotlib.pyplot as plt
from typing import Optional
from matplotlib.figure import Figure


def save_chart(fig: Figure, img_dir: str) -> str:
    """
    Salva un grafico matplotlib in una directory e ritorna il path relativo

    Args:
        fig: Oggetto matplotlib Figure da salvare
        img_dir: Directory dove salvare l'immagine

    Returns:
        Path relativo dell'immagine salvata (formato: /static/pred_charts/<uuid>.png)

    Example:
        >>> fig = plt.figure()
        >>> plt.plot([1, 2, 3], [4, 5, 6])
        >>> path = save_chart(fig, "static/pred_charts")
        >>> print(path)
        /static/pred_charts/a1b2c3d4-e5f6-7890-abcd-ef1234567890.png
    """
    # Crea directory se non esiste
    if not os.path.exists(img_dir):
        os.makedirs(img_dir)

    # Genera nome file univoco
    img_id = str(uuid.uuid4()) + ".png"
    img_path = os.path.join(img_dir, img_id)

    # Salva figura
    fig.savefig(img_path, bbox_inches="tight", dpi=100)

    # Chiudi figura per liberare memoria
    plt.close(fig)

    # Ritorna path relativo (con forward slash per URL)
    return "/" + img_path.replace("\\", "/")


def create_reliability_chart(
    mesi_grid,
    km_surv,
    km_ci_lower,
    km_ci_upper,
    weibull_surv,
    weibull_lower,
    weibull_upper,
    last_reliable_month: int,
    title: str,
    figsize: tuple = (9, 5)
) -> Figure:
    """
    Crea un grafico di affidabilità con curve Kaplan-Meier e Weibull

    Args:
        mesi_grid: Griglia mesi (asse x)
        km_surv: Sopravvivenza Kaplan-Meier
        km_ci_lower: Banda inferiore IC 95% KM
        km_ci_upper: Banda superiore IC 95% KM
        weibull_surv: Sopravvivenza Weibull
        weibull_lower: Banda inferiore IC 95% Weibull
        weibull_upper: Banda superiore IC 95% Weibull
        last_reliable_month: Ultimo mese con stima affidabile
        title: Titolo del grafico
        figsize: Dimensioni figura (default: (9, 5))

    Returns:
        Oggetto matplotlib Figure
    """
    fig = plt.figure(figsize=figsize)

    # Kaplan-Meier
    plt.step(mesi_grid, km_surv, label='Kaplan-Meier', where='post', color='C0', linewidth=2)
    plt.fill_between(
        mesi_grid, km_ci_lower, km_ci_upper,
        color='C0', alpha=0.20, step='post',
        label='KM 95% CI'
    )

    # Weibull
    plt.plot(mesi_grid, weibull_surv, 'r--', label='Weibull tuned', linewidth=2)
    plt.fill_between(
        mesi_grid, weibull_lower, weibull_upper,
        color='r', alpha=0.15,
        label='Weibull 95% CI'
    )

    # Linea ultimo mese affidabile
    plt.axvline(
        last_reliable_month,
        color='orange',
        linestyle='-.',
        linewidth=1.5,
        label=f'Stima affidabile fino a {last_reliable_month} mesi'
    )

    # Formattazione
    plt.xlabel("Mesi", fontsize=11)
    plt.ylabel("Probabilità di sopravvivenza", fontsize=11)
    plt.title(title, fontsize=12, fontweight='bold')
    plt.legend(loc='best', fontsize=9)
    plt.ylim(0.85, 1.01)
    plt.xlim(0, 36)
    plt.grid(True, alpha=0.3, linestyle='--')
    plt.tight_layout()

    return fig
