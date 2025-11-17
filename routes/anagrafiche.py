"""
Blueprint per la gestione Anagrafiche File Excel (CRUD + Upload)
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, send_from_directory, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from models import db, AnagraficaFile, Modello, Componente, ModelloComponente
from forms import AnagraficaFileForm, AnagraficaFileEditForm, NuovaMarcaForm
from utils.decorators import admin_required
import os
import shutil
import random
from datetime import datetime, date
import pandas as pd
from decimal import Decimal, InvalidOperation

anagrafiche_bp = Blueprint('anagrafiche', __name__)

# Marche iniziali di default
MARCHE_DEFAULT = ['HISENSE', 'HOMA', 'MIDEA']

def get_marche_disponibili():
    """
    Restituisce la lista di tutte le marche disponibili
    Scansiona le cartelle INPUT/anagrafiche/ e OUTPUT/anagrafiche/
    """
    base_dir = current_app.root_path   # <<< più affidabile di risalire da __file__
    input_dir = os.path.join(base_dir, 'INPUT', 'anagrafiche')
    output_dir = os.path.join(base_dir, 'OUTPUT', 'anagrafiche')

    marche = set()

    def _accumula_cartelle(root):
        if os.path.exists(root):
            for entry in os.listdir(root):
                try:
                    p = os.path.join(root, entry)
                    # Prendi SOLO directory, evita file/shortcut/ecc.
                    if os.path.isdir(p):
                        name = str(entry).strip()  # forza a str
                        if name:
                            marche.add(name)
                except Exception:
                    # Ignora qualunque voce "strana"
                    continue

    _accumula_cartelle(input_dir)
    _accumula_cartelle(output_dir)

    # Se non c'è nulla, usa le marche di default
    if not marche:
        marche = set(MARCHE_DEFAULT)

    # Ordina in modo deterministico e "case-insensitive"
    return sorted(marche, key=lambda s: s.lower())


def crea_cartelle_marca(marca):
    """
    Crea le cartelle INPUT/anagrafiche/{marca}/ e OUTPUT/anagrafiche/{marca}/
    """
    base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    
    input_dir = os.path.join(base_dir, 'INPUT', 'anagrafiche', marca)
    output_dir = os.path.join(base_dir, 'OUTPUT', 'anagrafiche', marca)
    
    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    
    return input_dir


def get_filepath_by_status(marca, filename, esito):
    """
    Restituisce il path completo del file in base allo stato
    - Da processare / Errore: INPUT/anagrafiche/{marca}/
    - Processato: OUTPUT/anagrafiche/{marca}/
    """
    base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    
    if esito == 'Processato':
        folder = os.path.join(base_dir, 'OUTPUT', 'anagrafiche', marca)
    else:
        folder = os.path.join(base_dir, 'INPUT', 'anagrafiche', marca)
    
    return os.path.join(folder, filename)


def scan_anagrafiche_folder():
    """
    Scansiona le cartelle INPUT/anagrafiche/ e OUTPUT/anagrafiche/
    e sincronizza con il database
    """
    base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    input_base = os.path.join(base_dir, 'INPUT', 'anagrafiche')
    output_base = os.path.join(base_dir, 'OUTPUT', 'anagrafiche')
    
    # Crea cartelle base se non esistono
    os.makedirs(input_base, exist_ok=True)
    os.makedirs(output_base, exist_ok=True)
    
    files_trovati = set()  # Set di tutti i filepath trovati
    
    # Scansiona INPUT
    if os.path.exists(input_base):
        for marca in os.listdir(input_base):
            marca_path = os.path.join(input_base, marca)
            
            if not os.path.isdir(marca_path):
                continue
            
            for filename in os.listdir(marca_path):
                if not filename.lower().endswith(('.xls', '.xlsx')):
                    continue
                
                filepath = os.path.join(marca_path, filename)
                files_trovati.add(filepath)
                
                # Controlla se già  nel DB
                existing = AnagraficaFile.query.filter_by(filepath=filepath).first()
                
                if not existing:
                    # Aggiungi al database
                    nuova_anagrafica = AnagraficaFile(
                        anno=date.today().year,
                        marca=marca,
                        filename=filename,
                        filepath=filepath,
                        data_acquisizione=date.today(),
                        esito='Da processare'
                    )
                    db.session.add(nuova_anagrafica)
                    print(f"[SYNC] Aggiunto: {filepath}")
    
    # Scansiona OUTPUT
    if os.path.exists(output_base):
        for marca in os.listdir(output_base):
            marca_path = os.path.join(output_base, marca)
            
            if not os.path.isdir(marca_path):
                continue
            
            for filename in os.listdir(marca_path):
                if not filename.lower().endswith(('.xls', '.xlsx')):
                    continue
                
                filepath = os.path.join(marca_path, filename)
                files_trovati.add(filepath)
                
                # Controlla se già  nel DB
                existing = AnagraficaFile.query.filter_by(filepath=filepath).first()
                
                if not existing:
                    # Aggiungi al database
                    nuova_anagrafica = AnagraficaFile(
                        anno=date.today().year,
                        marca=marca,
                        filename=filename,
                        filepath=filepath,
                        data_acquisizione=date.today(),
                        esito='Processato',
                        data_elaborazione=date.today()
                    )
                    db.session.add(nuova_anagrafica)
                    print(f"[SYNC] Aggiunto: {filepath}")
    
    # Rimuovi record orfani
    tutte_anagrafiche = AnagraficaFile.query.all()
    for anagrafica in tutte_anagrafiche:
        if anagrafica.filepath not in files_trovati:
            print(f"[SYNC] Rimosso record orfano: {anagrafica.filepath}")
            db.session.delete(anagrafica)
    
    db.session.commit()




def normalizza_codice(codice):
    """Normalizza un codice: lowercase e rimuove spazi"""
    if not codice or pd.isna(codice):
        return None
    return str(codice).strip().lower().replace(' ', '')


def safe_decimal(value, default=None):
    """Converte un valore in Decimal in modo sicuro"""
    if pd.isna(value) or value is None or value == '':
        return default

    try:
        # Rimuovi spazi e simboli di valuta
        if isinstance(value, str):
            value = value.strip().replace('€', '').replace('$', '').replace(',', '.')
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return default


def safe_int(value, default=None):
    """Converte un valore in int in modo sicuro"""
    if pd.isna(value) or value is None or value == '':
        return default

    try:
        return int(float(value))
    except (ValueError, TypeError):
        return default


def safe_str(value, default=''):
    """Converte un valore in stringa in modo sicuro"""
    if pd.isna(value) or value is None:
        return default
    return str(value).strip()


def elabora_anagrafica(anagrafica_id):
    """
    Elabora un file di anagrafica Excel e inserisce i dati nel database.

    Processo:
    1. Legge file Excel
    2. Valida formato e colonne richieste
    3. Per ogni riga:
       - UPSERT modello (cod_modello, cod_modello_fabbrica)
       - UPSERT componente (tutti i campi)
       - INSERT modello_componente (con DELETE preventivo per questo file)
    4. Sposta file in OUTPUT
    5. Aggiorna stato nel database

    Gestione errori:
    - Rollback automatico in caso di errori
    - Messaggi dettagliati negli errori
    - File rimane in INPUT in caso di errore
    """
    anagrafica = AnagraficaFile.query.get_or_404(anagrafica_id)

    # Verifica che il file esista
    if not os.path.exists(anagrafica.filepath):
        anagrafica.esito = 'Errore'
        anagrafica.data_elaborazione = date.today()
        anagrafica.note = '❌ File non trovato sul filesystem'
        anagrafica.updated_by = current_user.username if current_user.is_authenticated else 'system'
        db.session.commit()
        return False, 'File non trovato sul filesystem'

    try:
        # Leggi il file Excel
        try:
            df = pd.read_excel(anagrafica.filepath)
        except Exception as e:
            raise ValueError(f"Impossibile leggere il file Excel: {str(e)}")

        # Valida colonne richieste
        colonne_richieste = [
            'file', 'anno', 'modello', 'modello fabbrica', 'M&C code', 'qtà',
            'pos number', 'part no', 'alt code', 'alt code 2', 'ean code', 'barcode',
            'part name', 'chinese name', 'descr ita',
            'unit price usd',
            'prezzo EURO al CAT NO trasporto - NO iva - NETTO',
            'prezzo EURO al CAT con trasporto - NO iva - NETTO',
            'prezzo EURO al PUBBLICO (suggerito) con IVA',
            'stat', 'softech stat'
        ]

        # Normalizza nomi colonne per confronto case-insensitive
        df_columns_lower = {col.lower().strip(): col for col in df.columns}
        colonne_richieste_lower = [col.lower().strip() for col in colonne_richieste]

        colonne_mancanti = []
        colonne_mapping = {}

        for col_req in colonne_richieste:
            col_req_lower = col_req.lower().strip()
            if col_req_lower not in df_columns_lower:
                colonne_mancanti.append(col_req)
            else:
                # Mappa colonna originale → colonna standardizzata
                colonne_mapping[df_columns_lower[col_req_lower]] = col_req

        if colonne_mancanti:
            raise ValueError(f"Colonne mancanti nel file Excel: {', '.join(colonne_mancanti)}")

        # Rinomina colonne per standardizzazione
        df = df.rename(columns=colonne_mapping)

        # Verifica che ci siano righe da elaborare
        if len(df) == 0:
            raise ValueError("Il file Excel non contiene righe da elaborare")

        # Contatori per statistiche
        modelli_inseriti = 0
        modelli_aggiornati = 0
        componenti_inseriti = 0
        componenti_aggiornati = 0
        relazioni_inserite = 0
        errori = []

        # DELETE preventivo: rimuovi tutti i modelli_componenti di questo file
        # (gestisce cancellazione logica dei record del file)
        try:
            deleted_count = ModelloComponente.query.filter_by(
                id_file_anagrafiche=anagrafica.id
            ).delete()
            db.session.flush()
            print(f"[ELABORAZIONE] Rimossi {deleted_count} record precedenti modelli_componenti")
        except Exception as e:
            raise ValueError(f"Errore durante la pulizia dei record esistenti: {str(e)}")

        # Elabora ogni riga
        for idx, row in df.iterrows():
            try:
                # Estrai dati modello
                cod_modello = safe_str(row['modello'])
                cod_modello_fabbrica = safe_str(row['modello fabbrica'])

                # Estrai dati componente
                cod_componente = safe_str(row['M&C code'])

                # Validazione base
                if not cod_modello:
                    errori.append(f"Riga {idx + 2}: cod_modello vuoto")
                    continue

                if not cod_componente:
                    errori.append(f"Riga {idx + 2}: cod_componente vuoto")
                    continue

                # Normalizza codici
                cod_modello_norm = normalizza_codice(cod_modello)
                cod_componente_norm = normalizza_codice(cod_componente)

                if not cod_modello_norm:
                    errori.append(f"Riga {idx + 2}: cod_modello_norm vuoto dopo normalizzazione")
                    continue

                if not cod_componente_norm:
                    errori.append(f"Riga {idx + 2}: cod_componente_norm vuoto dopo normalizzazione")
                    continue

                # === UPSERT MODELLO ===
                modello = Modello.query.filter_by(cod_modello=cod_modello).first()

                if modello:
                    # UPDATE: aggiorna solo i campi della pipeline anagrafiche
                    modello.cod_modello_fabbrica = cod_modello_fabbrica
                    modello.updated_at = datetime.utcnow()
                    modello.updated_by = current_user.username if current_user.is_authenticated else 'system'
                    modello.updated_from = 'ana'
                    modelli_aggiornati += 1
                else:
                    # INSERT: crea nuovo modello
                    modello = Modello(
                        cod_modello=cod_modello,
                        cod_modello_norm=cod_modello_norm,
                        cod_modello_fabbrica=cod_modello_fabbrica,
                        created_at=datetime.utcnow(),
                        created_by=current_user.username if current_user.is_authenticated else 'system',
                        updated_at=datetime.utcnow(),
                        updated_by=current_user.username if current_user.is_authenticated else 'system',
                        updated_from='ana'
                    )
                    db.session.add(modello)
                    modelli_inseriti += 1

                db.session.flush()  # Assicura che il modello esista prima di procedere

                # === UPSERT COMPONENTE ===
                componente = Componente.query.filter_by(cod_componente=cod_componente).first()

                # Estrai tutti i dati componente
                desc_componente_it = safe_str(row['descr ita'])
                cod_alt = safe_str(row['alt code'])
                cod_alt_2 = safe_str(row['alt code 2'])
                pos_no = safe_str(row['pos number'])
                part_no = safe_str(row['part no'])
                part_name_en = safe_str(row['part name'])
                part_name_cn = safe_str(row['chinese name'])
                part_name_it = desc_componente_it  # Uguale a desc_componente_it
                cod_ean = safe_str(row['ean code'])
                barcode = safe_str(row['barcode'])

                # Prezzi
                unit_price_usd = safe_decimal(row['unit price usd'])
                unit_price_notra_noiva_netto_eur = safe_decimal(row['prezzo EURO al CAT NO trasporto - NO iva - NETTO'])
                unit_price_tra_noiva_netto_eur = safe_decimal(row['prezzo EURO al CAT con trasporto - NO iva - NETTO'])
                unit_price_public_eur = safe_decimal(row['prezzo EURO al PUBBLICO (suggerito) con IVA'])

                stat = safe_str(row['stat'])
                softech_stat = safe_str(row['softech stat'])

                if componente:
                    # UPDATE: aggiorna tutti i campi
                    componente.desc_componente_it = desc_componente_it
                    componente.cod_alt = cod_alt
                    componente.cod_alt_2 = cod_alt_2
                    componente.pos_no = pos_no
                    componente.part_no = part_no
                    componente.part_name_en = part_name_en
                    componente.part_name_cn = part_name_cn
                    componente.part_name_it = part_name_it
                    componente.cod_ean = cod_ean
                    componente.barcode = barcode
                    componente.unit_price_usd = unit_price_usd
                    componente.unit_price_notra_noiva_netto_eur = unit_price_notra_noiva_netto_eur
                    componente.unit_price_tra_noiva_netto_eur = unit_price_tra_noiva_netto_eur
                    componente.unit_price_public_eur = unit_price_public_eur
                    componente.stat = stat
                    componente.softech_stat = softech_stat
                    componente.updated_at = datetime.utcnow()
                    componente.updated_by = current_user.username if current_user.is_authenticated else 'system'
                    componenti_aggiornati += 1
                else:
                    # INSERT: crea nuovo componente
                    componente = Componente(
                        cod_componente=cod_componente,
                        cod_componente_norm=cod_componente_norm,
                        desc_componente_it=desc_componente_it,
                        cod_alt=cod_alt,
                        cod_alt_2=cod_alt_2,
                        pos_no=pos_no,
                        part_no=part_no,
                        part_name_en=part_name_en,
                        part_name_cn=part_name_cn,
                        part_name_it=part_name_it,
                        cod_ean=cod_ean,
                        barcode=barcode,
                        unit_price_usd=unit_price_usd,
                        unit_price_notra_noiva_netto_eur=unit_price_notra_noiva_netto_eur,
                        unit_price_tra_noiva_netto_eur=unit_price_tra_noiva_netto_eur,
                        unit_price_public_eur=unit_price_public_eur,
                        stat=stat,
                        softech_stat=softech_stat,
                        created_at=datetime.utcnow(),
                        created_by=current_user.username if current_user.is_authenticated else 'system',
                        updated_at=datetime.utcnow(),
                        updated_by=current_user.username if current_user.is_authenticated else 'system'
                    )
                    db.session.add(componente)
                    componenti_inseriti += 1

                db.session.flush()  # Assicura che il componente esista prima di procedere

                # === INSERT MODELLO_COMPONENTE ===
                qta = safe_int(row['qtà'], default=1)

                # Chiave primaria composita
                modello_componente_pk = f"{cod_modello}|{cod_componente}"

                # Inserisci relazione
                modello_componente = ModelloComponente(
                    modello_componente=modello_componente_pk,
                    id_file_anagrafiche=anagrafica.id,
                    cod_modello=cod_modello,
                    cod_componente=cod_componente,
                    qta=qta,
                    created_at=datetime.utcnow(),
                    created_by=current_user.username if current_user.is_authenticated else 'system',
                    updated_at=datetime.utcnow(),
                    updated_by=current_user.username if current_user.is_authenticated else 'system'
                )
                db.session.add(modello_componente)
                relazioni_inserite += 1

            except Exception as e:
                errori.append(f"Riga {idx + 2}: {str(e)}")
                continue

        # Verifica se ci sono errori critici
        if errori and len(errori) >= len(df) * 0.5:  # Se più del 50% delle righe hanno errori
            raise ValueError(f"Troppi errori durante l'elaborazione ({len(errori)}/{len(df)} righe):\n" + "\n".join(errori[:10]))

        # COMMIT delle modifiche al database
        db.session.commit()

        # === SPOSTA FILE IN OUTPUT ===
        base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
        output_dir = os.path.join(base_dir, 'OUTPUT', 'anagrafiche', anagrafica.marca)
        os.makedirs(output_dir, exist_ok=True)

        new_filepath = os.path.join(output_dir, anagrafica.filename)

        try:
            shutil.move(anagrafica.filepath, new_filepath)
        except Exception as e:
            # File spostato con errore - log ma non fallire
            print(f"[WARNING] Errore durante lo spostamento del file: {str(e)}")
            new_filepath = anagrafica.filepath  # Mantieni il path originale

        # Aggiorna record anagrafica
        anagrafica.filepath = new_filepath
        anagrafica.esito = 'Processato'
        anagrafica.data_elaborazione = date.today()
        anagrafica.updated_by = current_user.username if current_user.is_authenticated else 'system'

        # Componi nota con statistiche
        note_parts = [
            f'✓ Elaborazione completata con successo',
            f'Modelli: {modelli_inseriti} inseriti, {modelli_aggiornati} aggiornati',
            f'Componenti: {componenti_inseriti} inseriti, {componenti_aggiornati} aggiornati',
            f'Relazioni modelli-componenti: {relazioni_inserite} inserite',
            f'Righe totali: {len(df)}'
        ]

        if errori:
            note_parts.append(f'\n⚠ Avvisi ({len(errori)} righe con problemi):')
            note_parts.extend(errori[:5])  # Mostra solo i primi 5 errori
            if len(errori) > 5:
                note_parts.append(f'... e altri {len(errori) - 5} avvisi')

        anagrafica.note = '\n'.join(note_parts)

        db.session.commit()

        return True, f'Elaborazione completata! {relazioni_inserite} relazioni modelli-componenti inserite.'

    except Exception as e:
        # ROLLBACK in caso di errore
        db.session.rollback()

        # Aggiorna record anagrafica con errore
        anagrafica.esito = 'Errore'
        anagrafica.data_elaborazione = date.today()
        anagrafica.updated_by = current_user.username if current_user.is_authenticated else 'system'
        anagrafica.note = f'❌ Errore durante l\'elaborazione:\n{str(e)}'

        db.session.commit()

        return False, f'Errore: {str(e)}'


@anagrafiche_bp.route('/')
@login_required
def list():
    """Lista tutte le anagrafiche con paginazione, filtri e ordinamento"""
    # Sincronizza con filesystem
    scan_anagrafiche_folder()
    
    page = request.args.get('page', 1, type=int)
    marca_filter = request.args.get('marca', '')
    esito_filter = request.args.get('esito', '')
    anno_filter = request.args.get('anno', type=int)
    q = request.args.get('q', '').strip()
    sort_by = request.args.get('sort', 'created_at')
    order = request.args.get('order', 'desc')
    
    query = AnagraficaFile.query
    
    # Filtri
    if marca_filter:
        query = query.filter_by(marca=marca_filter)
    if esito_filter:
        query = query.filter_by(esito=esito_filter)
    if anno_filter:
        query = query.filter_by(anno=anno_filter)
    if q:
        query = query.filter(AnagraficaFile.filename.ilike(f"%{q}%"))
    
    # Ordinamento dinamico
    sortable_columns = ['anno','marca','filename','data_acquisizione','data_elaborazione','esito','created_at','updated_at']
    if sort_by in sortable_columns and hasattr(AnagraficaFile, sort_by):
        column = getattr(AnagraficaFile, sort_by)
        if order == 'desc':
            query = query.order_by(column.desc())
        else:
            query = query.order_by(column.asc())
    else:
        # Default: ordina per data creazione decrescente
        query = query.order_by(AnagraficaFile.created_at.desc())
    
    anagrafiche = query.paginate(page=page, per_page=20, error_out=False)
    
    # Liste per filtri
    marche_disponibili = get_marche_disponibili()
    anni_disponibili = [r[0] for r in db.session.query(AnagraficaFile.anno).distinct().order_by(AnagraficaFile.anno.desc())]
    
    return render_template('anagrafiche/list.html',
                         anagrafiche=anagrafiche,
                         marca_filter=marca_filter,
                         esito_filter=esito_filter,
                         anno_filter=anno_filter,
                         q=q,
                         marche_disponibili=marche_disponibili,
                         anni_disponibili=anni_disponibili,
                         sort_by=sort_by,
                         order=order)


@anagrafiche_bp.route('/create', methods=['GET', 'POST'])
@admin_required
def create():
    """Upload nuovo file anagrafica"""
    form = AnagraficaFileForm()
    
    # Popola le scelte della select marca
    marche = get_marche_disponibili()
    form.marca.choices = [(m, m) for m in marche]
 
    # Inizializza data corrente al primo caricamento
    if request.method == 'GET':
        form.data_acquisizione.data = datetime.now().date()
        
    if form.validate_on_submit():
        file = form.file.data
        marca = form.marca.data
        anno = int(form.anno.data)
        
        # Verifica estensione
        if not file.filename.lower().endswith(('.xls', '.xlsx')):
            flash('Solo file Excel (.xls, .xlsx) sono permessi!', 'danger')
            return redirect(url_for('anagrafiche.create'))
        
        # Nome file sicuro
        filename = secure_filename(file.filename)
        
        # Crea cartelle marca se non esistono
        input_dir = crea_cartelle_marca(marca)
        
        filepath = os.path.join(input_dir, filename)
        
        # Verifica se file esiste già
        if os.path.exists(filepath):
            flash(f'Un file con nome {filename} esiste già per la marca {marca}!', 'warning')
            return redirect(url_for('anagrafiche.create'))
        
        # Salva il file
        file.save(filepath)
        
        # Crea record nel database
        anagrafica = AnagraficaFile(
            anno=anno,
            marca=marca,
            filename=filename,
            filepath=filepath,
            data_acquisizione=form.data_acquisizione.data,  # ← già date object
            esito='Da processare',
            note=form.note.data
        )
        
        db.session.add(anagrafica)
        db.session.commit()
        
        flash(f'File {filename} caricato con successo per la marca {marca}!', 'success')
        return redirect(url_for('anagrafiche.list'))
    
    return render_template('anagrafiche/create.html', form=form)


@anagrafiche_bp.route('/nuova-marca', methods=['GET', 'POST'])
@admin_required
def nuova_marca():
    """Crea una nuova marca"""
    form = NuovaMarcaForm()
    
    if form.validate_on_submit():
        nome_marca = form.nome_marca.data.strip().upper()
        
        # Verifica se esiste già
        marche_esistenti = get_marche_disponibili()
        if nome_marca in marche_esistenti:
            flash(f'La marca {nome_marca} esiste già!', 'warning')
            return redirect(url_for('anagrafiche.nuova_marca'))
        
        # Crea le cartelle
        crea_cartelle_marca(nome_marca)
        
        flash(f'Marca {nome_marca} creata con successo!', 'success')
        return redirect(url_for('anagrafiche.create'))
    
    return render_template('anagrafiche/nuova_marca.html', form=form)


@anagrafiche_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def edit(id):
    """Modifica un'anagrafica esistente"""
    anagrafica = AnagraficaFile.query.get_or_404(id)
    form = AnagraficaFileEditForm(obj=anagrafica)  # ← WTForms popola automaticamente
    
    if form.validate_on_submit():
        anagrafica.anno = int(form.anno.data)
        anagrafica.data_acquisizione = form.data_acquisizione.data
        anagrafica.data_elaborazione = form.data_elaborazione.data
        anagrafica.esito = form.esito.data
        anagrafica.note = form.note.data
        
        db.session.commit()
        flash(f'Anagrafica {anagrafica.filename} aggiornata!', 'success')
        return redirect(url_for('anagrafiche.list'))
    
    return render_template('anagrafiche/edit.html', form=form, anagrafica=anagrafica)

@anagrafiche_bp.route('/<int:id>/elabora', methods=['POST'])
@admin_required
def elabora(id):
    """Elabora un file di anagrafica"""
    success, message = elabora_anagrafica(id)
    
    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')
    
    return redirect(url_for('anagrafiche.list'))


@anagrafiche_bp.route('/<int:id>/delete', methods=['POST'])
@admin_required
def delete(id):
    """Elimina un'anagrafica e i suoi record modelli_componenti"""
    anagrafica = AnagraficaFile.query.get_or_404(id)
    filename = anagrafica.filename
    filepath = anagrafica.filepath

    try:
        # 1. Elimina i record modelli_componenti associati al file (CASCADE)
        deleted_count = ModelloComponente.query.filter_by(
            id_file_anagrafiche=anagrafica.id
        ).delete()

        # 2. Elimina il file dal filesystem
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except Exception as e:
                db.session.rollback()
                flash(f'Errore nell\'eliminazione del file: {str(e)}', 'danger')
                return redirect(url_for('anagrafiche.list'))

        # 3. Elimina il record anagrafica dal database
        db.session.delete(anagrafica)
        db.session.commit()

        flash(f'Anagrafica {filename} eliminata ({deleted_count} relazioni modelli-componenti rimosse).', 'info')
        return redirect(url_for('anagrafiche.list'))

    except Exception as e:
        db.session.rollback()
        flash(f'Errore durante l\'eliminazione: {str(e)}', 'danger')
        return redirect(url_for('anagrafiche.list'))


@anagrafiche_bp.route('/download/<int:id>')
@login_required
def download(id):
    """Download del file Excel"""
    anagrafica = AnagraficaFile.query.get_or_404(id)
    
    if not os.path.exists(anagrafica.filepath):
        flash('File non trovato sul server!', 'danger')
        return redirect(url_for('anagrafiche.list'))
    
    directory = os.path.dirname(anagrafica.filepath)
    filename = os.path.basename(anagrafica.filepath)
    
    return send_from_directory(directory, filename, as_attachment=True)


@anagrafiche_bp.route('/view/<int:id>')
@login_required
def view(id):
    """Apri il file Excel nel browser (se possibile)"""
    anagrafica = AnagraficaFile.query.get_or_404(id)
    
    if not os.path.exists(anagrafica.filepath):
        flash('File non trovato sul server!', 'danger')
        return redirect(url_for('anagrafiche.list'))
    
    directory = os.path.dirname(anagrafica.filepath)
    filename = os.path.basename(anagrafica.filepath)
    
    # Excel non si può aprire direttamente nel browser, quindi scarica
    return send_from_directory(directory, filename, as_attachment=False)


@anagrafiche_bp.route('/sync')
@admin_required
def sync():
    """Sincronizza manualmente il database con il filesystem"""
    scan_anagrafiche_folder()
    flash('Sincronizzazione completata!', 'success')
    return redirect(url_for('anagrafiche.list'))


#from flask import Markup
from markupsafe import Markup
import pandas as pd

@anagrafiche_bp.route('/preview/<int:id>')
@login_required
def preview(id):
    """Anteprima HTML del file Excel (prime righe del primo foglio)."""
    ana = AnagraficaFile.query.get_or_404(id)

    # Verifica path e stato/cartella
    filepath = ana.filepath
    if not os.path.isfile(filepath):
        flash("File non trovato sul filesystem.", "danger")
        return redirect(url_for('anagrafiche.list'))

    # Carica prime righe
    try:
        # Legge solo il primo foglio; in futuro puoi esporre un selettore dei fogli
        df = pd.read_excel(filepath, nrows=200)  # limite anti-memoria
        table_html = Markup(df.to_html(classes="table table-striped table-sm", index=False, border=0))
        error = None
    except Exception as e:
        table_html = None
        error = f"Impossibile generare anteprima: {e}"

    return render_template(
        'anagrafiche/preview.html',
        ana=ana,
        table_html=table_html,
        error=error
    )
