#!/usr/bin/env python3
"""
Script per generare dati stock simulati (3 file TSV mensili)

Genera 3 snapshot di giacenze componenti:
- 2024-09-01 (Settembre)
- 2024-10-01 (Ottobre)
- 2024-11-01 (Novembre - corrente con flag_corrente=TRUE)

Ogni file contiene ~150-200 componenti con giacenze simulate.
Schema: warehouse, ubicazione, giacenze (disponibile/impegnata/fisica), soglie, flag_corrente
"""

import csv
import random
from datetime import datetime, date
from pathlib import Path

# Configurazione
BASE_DIR = Path(__file__).parent.parent
OUTPUT_DIR = BASE_DIR / 'data' / 'stock_tsv'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Date snapshot
SNAPSHOTS = [
    {'date': date(2024, 9, 1), 'flag_corrente': False},
    {'date': date(2024, 10, 1), 'flag_corrente': False},
    {'date': date(2024, 11, 1), 'flag_corrente': True},  # Corrente
]

# Categorie componenti realistiche
COMPONENT_PREFIXES = ['PCB', 'MOT', 'SENS', 'DISP', 'CTRL', 'FAN', 'PWR', 'LED', 'BTN', 'CONN']
COMPONENT_TYPES = ['MAIN', 'SUB', 'AUX', 'SPARE']

# Warehouses
WAREHOUSES = ['A', 'B', 'C']
BINS = list(range(1, 51))  # Scaffali 1-50


def generate_component_code(idx):
    """Genera codice componente realistico"""
    prefix = random.choice(COMPONENT_PREFIXES)
    type_code = random.choice(COMPONENT_TYPES)
    number = f"{idx:04d}"
    return f"{prefix}-{type_code}-{number}"


def generate_lot_number(year, month):
    """Genera numero lotto formato YYYYMM-BATCH"""
    batch = random.randint(100, 999)
    return f"{year}{month:02d}-{batch}"


def generate_warehouse_location():
    """Genera warehouse e ubicazione"""
    warehouse = random.choice(WAREHOUSES)
    bin_num = random.choice(BINS)
    ubicazione = f"SC{bin_num:02d}"
    return warehouse, ubicazione


def generate_stock_quantity(mean=500, std=200):
    """Genera quantità stock fisica con distribuzione normale"""
    qty = int(random.gauss(mean, std))
    return max(0, qty)


def calculate_giacenze(giacenza_fisica):
    """
    Calcola giacenza_disponibile e giacenza_impegnata da giacenza_fisica

    Regola: giacenza_fisica = giacenza_disponibile + giacenza_impegnata
    """
    if giacenza_fisica == 0:
        return 0, 0

    # 10-30% della giacenza fisica è impegnata
    perc_impegnata = random.uniform(0.10, 0.30)
    giacenza_impegnata = int(giacenza_fisica * perc_impegnata)
    giacenza_disponibile = giacenza_fisica - giacenza_impegnata

    return giacenza_disponibile, giacenza_impegnata


def calculate_soglie(giacenza_fisica):
    """
    Calcola soglie basate sulla giacenza fisica

    - scorta_minima: 10-20% della fisica
    - punto_riordino: 20-30% della fisica
    - scorta_massima: 150-200% della fisica
    - lead_time_days: 45-90 giorni (import dalla Cina)
    """
    if giacenza_fisica == 0:
        scorta_minima = random.randint(10, 50)
        punto_riordino = scorta_minima + random.randint(10, 30)
        scorta_massima = random.randint(200, 500)
    else:
        scorta_minima = max(10, int(giacenza_fisica * random.uniform(0.10, 0.20)))
        punto_riordino = max(scorta_minima + 10, int(giacenza_fisica * random.uniform(0.20, 0.30)))
        scorta_massima = max(punto_riordino + 50, int(giacenza_fisica * random.uniform(1.5, 2.0)))

    lead_time_days = random.randint(45, 90)

    return scorta_minima, punto_riordino, scorta_massima, lead_time_days


def simulate_stock_evolution(initial_fisica, month_delta):
    """
    Simula evoluzione stock nel tempo
    - Consumo medio mensile: -5% to -15%
    - Possibili rifornimenti: +50% to +100%
    - Probabilità rifornimento: 20%
    """
    fisica = initial_fisica

    for _ in range(month_delta):
        # Consumo mensile
        consumption_rate = random.uniform(0.05, 0.15)
        fisica = int(fisica * (1 - consumption_rate))

        # Rifornimento casuale
        if random.random() < 0.20:  # 20% probabilità
            restock_rate = random.uniform(0.5, 1.0)
            fisica = int(fisica * (1 + restock_rate))

    return max(0, fisica)


def generate_stock_snapshot(snapshot_info, num_components=180, base_components=None):
    """
    Genera snapshot giacenze per una data specifica

    Args:
        snapshot_info: Dict con 'date' e 'flag_corrente'
        num_components: Numero di componenti da generare
        base_components: Lista componenti base (per mantenere consistenza tra snapshot)

    Returns:
        Lista di dict con dati stock
    """
    snapshot_date = snapshot_info['date']
    flag_corrente = snapshot_info['flag_corrente']
    records = []

    # Se non abbiamo componenti base, li generiamo
    if base_components is None:
        base_components = []
        for i in range(1, num_components + 1):
            warehouse, ubicazione = generate_warehouse_location()
            base_components.append({
                'cod_componente': generate_component_code(i),
                'base_fisica': generate_stock_quantity(),
                'warehouse': warehouse,
                'ubicazione': ubicazione,
            })

    # Calcola mese delta per simulare evoluzione
    first_date = SNAPSHOTS[0]['date']
    month_delta = (snapshot_date.year - first_date.year) * 12 + (snapshot_date.month - first_date.month)

    for comp in base_components:
        # Evolvi quantità nel tempo
        giacenza_fisica = simulate_stock_evolution(comp['base_fisica'], month_delta)

        # Skip se esaurito da troppo tempo (30% di componenti esauriti vengono rimossi)
        if giacenza_fisica == 0 and random.random() < 0.3:
            continue

        # Calcola giacenze
        giacenza_disponibile, giacenza_impegnata = calculate_giacenze(giacenza_fisica)

        # Calcola soglie
        scorta_minima, punto_riordino, scorta_massima, lead_time_days = calculate_soglie(giacenza_fisica)

        # Genera lotto (può cambiare con rifornimenti)
        lotto = generate_lot_number(snapshot_date.year, snapshot_date.month)
        if random.random() < 0.7:  # 70% mantiene lotto precedente
            lotto = generate_lot_number(2024, random.randint(1, snapshot_date.month))

        # Data stock (stessa dello snapshot o qualche giorno prima)
        data_stock = snapshot_date.strftime('%Y-%m-%d')

        records.append({
            'cod_componente': comp['cod_componente'],
            'warehouse': comp['warehouse'],
            'ubicazione': comp['ubicazione'],
            'lotto': lotto,
            'giacenza_disponibile': giacenza_disponibile,
            'giacenza_impegnata': giacenza_impegnata,
            'giacenza_fisica': giacenza_fisica,
            'scorta_minima': scorta_minima,
            'scorta_massima': scorta_massima,
            'punto_riordino': punto_riordino,
            'lead_time_days': lead_time_days,
            'data_snapshot': snapshot_date.strftime('%Y-%m-%d %H:%M:%S'),
            'data_stock': data_stock,
            'flag_corrente': 'TRUE' if flag_corrente else 'FALSE',
        })

    return records, base_components


def write_tsv(filename, records):
    """Scrive records in file TSV"""
    filepath = OUTPUT_DIR / filename

    fieldnames = [
        'cod_componente', 'warehouse', 'ubicazione', 'lotto',
        'giacenza_disponibile', 'giacenza_impegnata', 'giacenza_fisica',
        'scorta_minima', 'scorta_massima', 'punto_riordino', 'lead_time_days',
        'data_snapshot', 'data_stock', 'flag_corrente'
    ]

    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter='\t')
        writer.writeheader()
        writer.writerows(records)

    print(f"✓ Creato: {filepath}")
    print(f"  Righe: {len(records)}")
    print(f"  Giacenza totale: {sum(r['giacenza_fisica'] for r in records):,} unità")
    print(f"  Disponibile: {sum(r['giacenza_disponibile'] for r in records):,} | Impegnata: {sum(r['giacenza_impegnata'] for r in records):,}")

    # Statistiche
    zero_stock = sum(1 for r in records if r['giacenza_fisica'] == 0)
    low_stock = sum(1 for r in records if 0 < r['giacenza_fisica'] < r['scorta_minima'])
    alert_riordino = sum(1 for r in records if 0 < r['giacenza_disponibile'] < r['punto_riordino'])

    print(f"  Esauriti: {zero_stock} | Sotto scorta min: {low_stock} | Sotto punto riordino: {alert_riordino}")
    print(f"  Flag corrente: {records[0]['flag_corrente'] if records else 'N/D'}")
    print()


def main():
    """Main execution"""
    print("=" * 60)
    print("GENERAZIONE DATI STOCK SIMULATI")
    print("=" * 60)
    print()

    base_components = None

    for idx, snapshot_info in enumerate(SNAPSHOTS, 1):
        snapshot_date = snapshot_info['date']
        print(f"Snapshot {idx}/3: {snapshot_date.strftime('%Y-%m-%d')} (flag_corrente={snapshot_info['flag_corrente']})")

        # Genera snapshot
        records, base_components = generate_stock_snapshot(
            snapshot_info,
            num_components=180,
            base_components=base_components
        )

        # Nome file
        filename = f"stock_{snapshot_date.strftime('%Y-%m-%d')}.tsv"

        # Scrivi TSV
        write_tsv(filename, records)

    print("=" * 60)
    print("✓ GENERAZIONE COMPLETATA")
    print("=" * 60)
    print(f"\nFile creati in: {OUTPUT_DIR}")
    print("\nPer importare i file:")
    print("1. Accedi all'applicazione web")
    print("2. Vai su Area C - Stock > Import")
    print("3. Carica i 3 file TSV nell'ordine cronologico")


if __name__ == '__main__':
    main()
