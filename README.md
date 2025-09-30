
# 📸 Progetto: Correzione e Conservazione Cronologica Metadati Foto JPEG

## 📝 Descrizione del Problema

La conservazione a lungo termine e l'ordinamento cronologico di collezioni fotografiche digitali vengono spesso compromessi da servizi di messaggistica (es. WhatsApp) e operazioni di copia/spostamento. Questi processi eliminano o danneggiano i metadati di scatto originali (**EXIF**), lasciando il sistema operativo con la sola **Data di Modifica del Filesystem (mtime)**, un dato fragile che si aggiorna ad ogni operazione di copia.

**Il problema principale:** Molti file (soprattutto da WhatsApp) sono privi di EXIF ma contengono una data (approssimativa, di inoltro) nel nome file (es. `IMG-YYYYMMDD-WA...`).

## 💡 Soluzione Adottata: Strategia a Cascata e Scrittura EXIF Permanente

Questo script Python adotta una strategia a cascata per recuperare la data più affidabile per ogni file e, in caso di successo, la **scrive in modo permanente** nel metadato EXIF del file stesso, garantendo la conservazione nel tempo.

### Strategia di Recupero della Data (Priorità)

1.  **Priorità 1: Metadati EXIF:** Tentativo di leggere la data e l'ora precise dal tag `DateTimeOriginal`.
2.  **Priorità 2: Nome File:** Se l'EXIF è assente, si cerca una sequenza di 8 cifre (`YYYYMMDD`) nel nome del file (ottimizzato per nomi file come `IMG-YYYYMMDD...` e gestione di prefissi di cestino/backup come `.trashed`). Questa data è considerata la **data di scatto approssimativa**.
3.  **Ultima Spiaggia:** Se entrambe falliscono, il file viene spostato in una cartella per la revisione manuale.

### Azioni di Correzione

| Fonte della Data | Azione sul Metadato EXIF (Permanente) | Azione sul Filesystem (mtime) |
| :--- | :--- | :--- |
| **EXIF Trovato** | Nessuna modifica (il dato è già valido). | Aggiornata per coerenza con l'EXIF. |
| **Nome File Trovato** | **SCRITTA permanentemente** la data (`YYYY:MM:DD 00:00:00`) nel tag `DateTimeOriginal`. | Aggiornata per coerenza con la data estratta dal nome. |

-----

## 💻 Architettura del Codice

Il programma è strutturato attorno al punto di ingresso `if __name__ == "__main__":` e utilizza le seguenti funzioni principali:

### 1\. Funzioni di Supporto

  * `scegli_cartella_sorgente()`: Utilizza `tkinter` per aprire un dialogo grafico per la selezione della cartella.
  * `imposta_data_file(file_path, data_datetime)`: Utilizza `os.utime()` per impostare la Data di Modifica del Filesystem (**mtime**) per l'ordinamento immediato.

### 2\. Funzioni di Lettura e Scrittura (Il Core)

  * `leggi_data_scatto_exif(file_path)`: Legge i metadati di scatto (tag `DateTimeOriginal`) tramite la libreria `piexif`.
  * `estrai_data_da_nome_file(nome_file)`: Utilizza il modulo `re` (espressioni regolari) per isolare il pattern di data a 8 cifre nel nome file, anche in presenza di prefissi di sistema (`.trashed-`).
  * `scrivi_data_scatto_exif(file_path, data_datetime)`: Funzione critica che utilizza `piexif.insert()` per scrivere permanentemente la data corretta nel tag **EXIF** del file JPEG.

### 3\. Logica Principale

  * `esegui_correzione_date(cartella_sorgente)`: Contiene il *main loop* di scansione. Applica la logica a cascata, confronta le date e chiama le funzioni di scrittura EXIF e aggiornamento mtime quando è necessario correggere i dati.
  * **Gestione Incompleti:** I file in cui non è stato possibile recuperare la data da nessuna fonte vengono spostati nella sottocartella `EXIF_INCOMPLETO`.
  * **Riepilogo Finale:** Genera un log a terminale con il conteggio dei file analizzati, corretti (mtime), con EXIF scritto permanentemente, e spostati.

-----

## 🛠️ Requisiti e Avvio

### Requisiti

  * Python 3.x
  * Librerie: `tkinter` (standard in Python), `piexif` (da installare).

<!-- end list -->

```bash
pip install piexif
```

### Avvio

Salvare il codice come `correggi_foto.py` ed eseguire:

```bash
python correggi_foto.py
```