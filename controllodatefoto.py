import tkinter as tk
from tkinter import filedialog
import os
import piexif 
import datetime
import shutil
import re

# =================================================================
# 1. FUNZIONI DI DIALOGO E DI SCRITTURA EXIF
# =================================================================
def scegli_cartella_sorgente():
    """Apre un dialogo grafico per la selezione della cartella sorgente."""
    root = tk.Tk()
    root.withdraw()
    
    cartella_sorgente = filedialog.askdirectory(title="Seleziona la Cartella Sorgente con SOLI File JPG/JPEG")
    
    if cartella_sorgente:
        print(f"✅ Cartella selezionata: {cartella_sorgente}")
        return cartella_sorgente
    else:
        print("❌ Nessuna cartella selezionata. Uscita.")
        return None

def scrivi_data_scatto_exif(file_path, data_datetime):
    """
    Scrive i metadati di data e ora di scatto (DateTimeOriginal) in un file JPEG.
    La data e ora vengono impostate su YYYY:MM:DD 00:00:00.
    """
    try:
        # 1. Carica metadati esistenti (se ci sono)
        exif_dict = piexif.load(file_path)

        # Formatta la data nel formato EXIF richiesto: "YYYY:MM:DD HH:MM:SS"
        data_str = data_datetime.strftime("%Y:%m:%d %H:%M:%S")

        # 2. Scrivi i tag EXIF più importanti in bytes
        data_bytes = data_str.encode('utf-8')
        
        # Aggiorna il dizionario EXIF:
        exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal] = data_bytes
        exif_dict["0th"][piexif.ImageIFD.DateTime] = data_bytes 
        
        # 3. Serializza i metadati
        exif_bytes = piexif.dump(exif_dict)

        # 4. Inserisci i metadati nel file.
        piexif.insert(exif_bytes, file_path)
        
        return True
    except Exception as e:
        print(f"    [ERRORE EXIF WRITE] Impossibile scrivere EXIF su {os.path.basename(file_path)}: {e}")
        return False


# =================================================================
# 2. FUNZIONI PER LA LETTURA DELLE DATE
# =================================================================
def leggi_data_scatto_exif(file_path):
    """Estrae la data e ora di scatto (DateTimeOriginal) dai metadati EXIF."""
    try:
        exif_dict = piexif.load(file_path)
        
        if piexif.ExifIFD.DateTimeOriginal in exif_dict.get("Exif", {}):
            data_str = exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal].decode('utf-8')
        elif piexif.ImageIFD.DateTime in exif_dict.get("0th", {}):
             data_str = exif_dict["0th"][piexif.ImageIFD.DateTime].decode('utf-8')
        else:
            return None

        return datetime.datetime.strptime(data_str, "%Y:%m:%d %H:%M:%S")

    except Exception:
        return None

def estrai_data_da_nome_file(nome_file):
    """
    Cerca nel nome del file una sequenza di otto cifre (YYYYMMDD).
    """
    nome_pulito, _ = os.path.splitext(nome_file) 
    nome_pulito = re.sub(r'^\.?trashed-?\d*[\-_]?', '', nome_pulito, flags=re.IGNORECASE)

    # Pattern Regex migliorato: cerca (IMG o non-cifra) + 8 cifre
    match = re.search(r'(IMG|\D*)(\d{8})', nome_pulito, re.IGNORECASE)
    
    if match:
        data_str = match.group(2) # Le 8 cifre
        
        try:
            data_trovata = datetime.datetime.strptime(data_str, "%Y%m%d")
            
            if data_trovata > datetime.datetime.now():
                return None
            
            # Se la data viene dal nome, impostiamo l'orario a mezzanotte (00:00:00)
            return data_trovata.replace(hour=0, minute=0, second=0)
        except ValueError:
            return None
    
    return None

# =================================================================
# 3. FUNZIONE PER IMPOSTARE LA DATA DEL FILE (mtime)
# =================================================================
def imposta_data_file(file_path, data_datetime):
    """Imposta la data di modifica (mtime) e accesso (atime) del filesystem."""
    timestamp_unix = data_datetime.timestamp()
    
    try:
        os.utime(file_path, (timestamp_unix, timestamp_unix))
        return True
    except Exception as e:
        print(f"    [ERRORE MTIME] Errore nell'impostare la data del file: {e}")
        return False

# =================================================================
# 4. LOGICA PRINCIPALE DI ESECUZIONE
# =================================================================
def esegui_correzione_date(cartella_sorgente):
    """
    Esegue la scansione, verifica, corregge le date e scrive EXIF se necessario.
    """
    if not cartella_sorgente:
        return

    # Inizializzazione contatori
    total_files_processed = 0
    files_date_corrected = 0
    files_exif_written = 0
    files_date_consistent = 0
    files_moved_to_incomplete = 0

    # Preparazione della cartella per file incompleti
    cartella_incompleti = os.path.join(cartella_sorgente, "EXIF_INCOMPLETO")
    if not os.path.exists(cartella_incompleti):
        os.makedirs(cartella_incompleti)
        print(f"   - Creata cartella per file incompleti: {os.path.basename(cartella_incompleti)}")

    # Estensioni VALIDE: Solo JPG e JPEG (come specificato)
    estensioni_valide = ('.jpg', '.jpeg')
    
    print("-" * 40)
    for nome_file in os.listdir(cartella_sorgente):
        file_path = os.path.join(cartella_sorgente, nome_file)

        if os.path.isdir(file_path) or nome_file == os.path.basename(cartella_incompleti):
            continue

        # Processa SOLO file JPG e JPEG
        if nome_file.lower().endswith(estensioni_valide):
            total_files_processed += 1
            print(f"Processing: {nome_file}")
            
            data_scatto = None
            fonte_data = None
            
            # TENTATIVO 1: Leggi la data dai metadati EXIF
            data_scatto = leggi_data_scatto_exif(file_path)

            if data_scatto:
                fonte_data = "EXIF"
            else:
                # TENTATIVO 2: Leggi la data dal nome del file
                data_scatto = estrai_data_da_nome_file(nome_file)
                if data_scatto:
                    fonte_data = "Nome File"
                
            
            if data_scatto:
                mtime_timestamp = os.path.getmtime(file_path)
                mtime_datetime = datetime.datetime.fromtimestamp(mtime_timestamp)

                # Verifica se la data sul file è incoerente
                differenza_tempo = abs(data_scatto - mtime_datetime)
                
                if differenza_tempo.total_seconds() > 10 or mtime_datetime.year < 2000:
                    
                    data_corretta = data_scatto
                    
                    # --- 🌟 LOGICA SCRITTURA EXIF PERMANENTE (SOLO SE DA NOME FILE) ---
                    if fonte_data == "Nome File":
                        # Poiché siamo sicuri che sono solo JPG/JPEG, procediamo direttamente
                        if scrivi_data_scatto_exif(file_path, data_corretta):
                            files_exif_written += 1
                            print(f"    - SCRITTO EXIF PERMANENTE: Data {data_corretta.strftime('%Y-%m-%d')} aggiunta.")
                        
                    # Imposta la data del filesystem (mtime)
                    if imposta_data_file(file_path, data_corretta):
                        files_date_corrected += 1
                        print(f"    - AGGIORNATA mtime file a: {data_corretta.strftime('%Y-%m-%d %H:%M:%S')} (da {fonte_data})")
                    
                else:
                    files_date_consistent += 1
                    print(f"    - Data file già coerente con {fonte_data}. Saltato.")
                    
            else:
                # Nessun dato valido trovato (EXIF o Nome File)
                nuovo_path = os.path.join(cartella_incompleti, nome_file)
                if os.path.dirname(file_path) != cartella_incompleti:
                    shutil.move(file_path, nuovo_path)
                    files_moved_to_incomplete += 1
                    print(f"    - NESSUNA data trovata. Spostato in EXIF_INCOMPLETO.")
        
        else:
            # File con estensioni diverse da JPG/JPEG verranno ignorati
            print(f"File saltato (estensione non JPG/JPEG): {nome_file}")

    print("-" * 40)
    print("Processo di correzione date completato!")
    
    # === MESSAGGIO DI RIEPILOGO FINALE ===
    print("\n" + "=" * 50)
    print("RIEPILOGO PROCESSO DI CORREZIONE DATE:")
    print("-" * 50)
    print(f"File totali analizzati (JPG/JPEG): {total_files_processed}")
    print(f"   - Date già coerenti (Saltate):   {files_date_consistent}")
    print(f"   - Date corrette (mtime aggiornata): {files_date_corrected}")
    print(f"     -> Di cui, Metadati EXIF scritti: {files_exif_written} 🌟")
    print("-" * 50)
    print(f"File con dati incompleti/Spostati:    {files_moved_to_incomplete}")
    print("=" * 50)

# =================================================================
# MAIN ENTRY POINT (PUNTO DI AVVIO)
# =================================================================
if __name__ == "__main__":
    cartella_selezionata = scegli_cartella_sorgente()
    
    if cartella_selezionata:
        esegui_correzione_date(cartella_selezionata)
        
        