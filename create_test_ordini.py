"""
Script per creare file Excel di test per ordini
"""
import pandas as pd
import os
from datetime import datetime

# Dati di test
data = [
    # Ordine PO2024001 - 3 modelli
    {
        'Seller': 'SELL001',
        'Seller desc': 'Fornitore ABC S.p.A.',
        'Buyer': 'BUY001',
        'Buyer desc': 'Cliente XYZ Ltd.',
        'Date': '2024-01-15',
        'PO No.': 'PO2024001',
        'Brand': 'HISENSE',
        'Item': 'Condizionatore 12000 BTU',
        'EAN': '8001234567890',
        'Model No.': 'HS-AC12-2024',
        'CIF Price €': 450.00,
        'Q.TY': 10,
        'Amount €': 4500.00
    },
    {
        'Seller': 'SELL001',
        'Seller desc': 'Fornitore ABC S.p.A.',
        'Buyer': 'BUY001',
        'Buyer desc': 'Cliente XYZ Ltd.',
        'Date': '2024-01-15',
        'PO No.': 'PO2024001',
        'Brand': 'HISENSE',
        'Item': 'Condizionatore 18000 BTU',
        'EAN': '8001234567891',
        'Model No.': 'HS-AC18-2024',
        'CIF Price €': 650.00,
        'Q.TY': 5,
        'Amount €': 3250.00
    },
    {
        'Seller': 'SELL001',
        'Seller desc': 'Fornitore ABC S.p.A.',
        'Buyer': 'BUY001',
        'Buyer desc': 'Cliente XYZ Ltd.',
        'Date': '2024-01-15',
        'PO No.': 'PO2024001',
        'Brand': 'MIDEA',
        'Item': 'Frigorifero 300L',
        'EAN': '8001234567892',
        'Model No.': 'MD-FRIDGE-300',
        'CIF Price €': 380.00,
        'Q.TY': 8,
        'Amount €': 3040.00
    },

    # Ordine PO2024002 - 2 modelli
    {
        'Seller': 'SELL002',
        'Seller desc': 'Fornitore DEF Ltd.',
        'Buyer': 'BUY001',
        'Buyer desc': 'Cliente XYZ Ltd.',
        'Date': '2024-02-20',
        'PO No.': 'PO2024002',
        'Brand': 'HOMA',
        'Item': 'Lavatrice 8kg',
        'EAN': '8001234567893',
        'Model No.': 'HM-WASH-8KG',
        'CIF Price €': 320.00,
        'Q.TY': 12,
        'Amount €': 3840.00
    },
    {
        'Seller': 'SELL002',
        'Seller desc': 'Fornitore DEF Ltd.',
        'Buyer': 'BUY001',
        'Buyer desc': 'Cliente XYZ Ltd.',
        'Date': '2024-02-20',
        'PO No.': 'PO2024002',
        'Brand': 'HOMA',
        'Item': 'Asciugatrice 9kg',
        'EAN': '8001234567894',
        'Model No.': 'HM-DRY-9KG',
        'CIF Price €': 420.00,
        'Q.TY': 6,
        'Amount €': 2520.00
    }
]

# Crea DataFrame
df = pd.DataFrame(data)

# Salva in Excel
output_dir = '/home/user/mec-previsioni/INPUT/po/2024'
os.makedirs(output_dir, exist_ok=True)

output_file = os.path.join(output_dir, 'ordine_test_2024.xlsx')
df.to_excel(output_file, index=False, engine='openpyxl')

print(f"✅ File di test creato: {output_file}")
print(f"📊 Righe totali: {len(df)}")
print(f"📦 Ordini: {df['PO No.'].nunique()}")
print(f"🏷️ Modelli: {df['Model No.'].nunique()}")
print(f"💰 Importo totale: €{df['Amount €'].sum():,.2f}")
