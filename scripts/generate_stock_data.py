#!/usr/bin/env python3
"""
Script per generare dati stock simulati (3 file TSV mensili)

Genera 3 snapshot di giacenze componenti:
- 2024-09-01 (Settembre)
- 2024-10-01 (Ottobre)
- 2024-11-01 (Novembre - corrente)

Ogni file contiene ~150-200 componenti con giacenze simulate.
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
    date(2024, 9, 1),
    date(2024, 10, 1),
    date(2024, 11, 1),
]

# Categorie componenti realistiche
COMPONENT_PREFIXES = ['PCB', 'MOT', 'SENS', 'DISP', 'CTRL', 'FAN', 'PWR', 'LED', 'BTN', 'CONN']
COMPONENT_TYPES = ['MAIN', 'SUB', 'AUX', 'SPARE']

# Ubicazioni magazzino
WAREHOUSES = ['A', 'B', 'C']
BINS = list(range(1, 51))  # Scaffali 1-50

# Marche/famiglie prodotti
BRANDS = ['HISENSE', 'CANDY', 'HAIER', 'WHIRLPOOL', 'ARISTON']


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


def generate_location():
    """Genera ubicazione magazzino"""
    warehouse = random.choice(WAREHOUSES)
    bin_num = random.choice(BINS)
    return f"MAG-{warehouse}-SC{bin_num:02d}"


def generate_stock_quantity(mean=500, std=200):
    """Genera quantità stock con distribuzione normale"""
    qty = int(random.gauss(mean, std))
    return max(0, qty)  # No negativi


def simulate_stock_evolution(initial_qty, month_delta):
    """
    Simula evoluzione stock nel tempo
    - Consumo medio mensile: -5% to -15%
    - Possibili rifornimenti: +50% to +100%
    - Probabilità rifornimento: 20%
    """
    qty = initial_qty

    for _ in range(month_delta):
        # Consumo mensile
        consumption_rate = random.uniform(0.05, 0.15)
        qty = int(qty * (1 - consumption_rate))

        # Rifornimento casuale
        if random.random() < 0.20:  # 20% probabilità
            restock_rate = random.uniform(0.5, 1.0)
            qty = int(qty * (1 + restock_rate))

    return max(0, qty)


def generate_stock_snapshot(snapshot_date, num_components=180, base_components=None):
    """
    Genera snapshot giacenze per una data specifica

    Args:
        snapshot_date: Data dello snapshot
        num_components: Numero di componenti da generare
        base_components: Lista componenti base (per mantenere consistenza tra snapshot)

    Returns:
        Lista di dict con dati stock
    """
    records = []

    # Se non abbiamo componenti base, li generiamo
    if base_components is None:
        base_components = [
            {
                'cod_componente': generate_component_code(i),
                'base_qty': generate_stock_quantity(),
                'ubicazione': generate_location(),
            }
            for i in range(1, num_components + 1)
        ]

    # Calcola mese delta per simulare evoluzione
    first_date = SNAPSHOTS[0]
    month_delta = (snapshot_date.year - first_date.year) * 12 + (snapshot_date.month - first_date.month)

    for comp in base_components:
        # Evolvi quantità nel tempo
        qty = simulate_stock_evolution(comp['base_qty'], month_delta)

        # Skip se esaurito da troppo tempo
        if qty == 0 and random.random() < 0.3:  # 30% di componenti esauriti vengono rimossi
            continue

        # Genera lotto (può cambiare con rifornimenti)
        lotto = generate_lot_number(snapshot_date.year, snapshot_date.month)
        if random.random() < 0.7:  # 70% mantiene lotto precedente
            lotto = generate_lot_number(2024, random.randint(1, snapshot_date.month))

        # Note opzionali
        note = None
        if qty < 50:
            note = "SCORTA BASSA - Verificare riordino"
        elif qty == 0:
            note = "ESAURITO"

        records.append({
            'cod_componente': comp['cod_componente'],
            'qtà': qty,
            'data_rilevazione': snapshot_date.strftime('%Y-%m-%d'),
            'ubicazione': comp['ubicazione'],
            'lotto': lotto,
            'note': note or '',
        })

    return records, base_components


def write_tsv(filename, records):
    """Scrive records in file TSV"""
    filepath = OUTPUT_DIR / filename

    fieldnames = ['cod_componente', 'qtà', 'data_rilevazione', 'ubicazione', 'lotto', 'note']

    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter='\t')
        writer.writeheader()
        writer.writerows(records)

    print(f"✓ Creato: {filepath}")
    print(f"  Righe: {len(records)}")
    print(f"  Totale giacenza: {sum(r['qtà'] for r in records):,} unità")

    # Statistiche
    zero_stock = sum(1 for r in records if r['qtà'] == 0)
    low_stock = sum(1 for r in records if 0 < r['qtà'] < 50)
    print(f"  Esauriti: {zero_stock} | Scorta bassa (<50): {low_stock}")
    print()


def main():
    """Main execution"""
    print("=" * 60)
    print("GENERAZIONE DATI STOCK SIMULATI")
    print("=" * 60)
    print()

    base_components = None

    for idx, snapshot_date in enumerate(SNAPSHOTS, 1):
        print(f"Snapshot {idx}/3: {snapshot_date.strftime('%Y-%m-%d')}")

        # Genera snapshot
        records, base_components = generate_stock_snapshot(
            snapshot_date,
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
