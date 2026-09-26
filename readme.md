# HackerNews Bookmarks Bot

A Telegram bot and a companion web server to save and manage bookmarks from HackerNews and other websites. The application is fully containerized using Docker for easy setup and deployment.

## Features

*   **Telegram Bot**: Save links directly from your "Saved Messages" or any private chat with the bot.
*   **Web Interface**: A modern web UI to view, search, filter, and manage your bookmarks.
*   **Metadata Scraping**: Automatically fetches the title, description, and preview image for each link.
*   **HackerNews Integration**: Special handling for HackerNews links to associate an article with its comments page.
*   **Multi-user & Multilingual Support**: The web interface supports multiple users and is available in English and Italian, with automatic language detection and a manual selector. It's easily extensible to other languages.
*   **Dockerized**: All services (bot, webserver, database migration) are containerized for a consistent and isolated environment.
*   **Testing Suite**: Includes a suite of unit and integration tests to ensure code quality and reliability.

---

## 🚀 Getting Started with Docker

### Prerequisites

*   [Docker](https://www.docker.com/get-started)
*   [Docker Compose](https://docs.docker.com/compose/install/)

### 1. Setup

Before launching the application, you need to configure a few environment variables.

#### a. Configure the Bot

Create a file named `.env` inside the `telegram_bot/` folder.

```bash
# Example file: telegram_bot/.env
API_ID=1234567
API_HASH=abcdef1234567890abcdef1234567890
BOT_TOKEN=1234567890:ABC-DEF1234567890ABC-DEF1234567890

# Set the webserver username to which the bot will associate the bookmarks
WEB_USERNAME=my_web_user
```

*   `API_ID` e `API_HASH`: Ottienili da my.telegram.org.
*   `BOT_TOKEN`: Ottienilo da @BotFather su Telegram.
*   `WEB_USERNAME`: Inserisci il nome utente che creerai per l'interfaccia web (vedi passo successivo).

#### b. Crea un Utente per il Webserver

Il bot ha bisogno di un utente del webserver a cui associare i bookmark. Esegui lo script `add_user.py` per creare questo utente.

1.  Installa la dipendenza necessaria (solo per questo script):
    ```bash
    pip install werkzeug
    ```

2.  Esegui lo script e segui le istruzioni per creare un utente. **Assicurati che il nome utente corrisponda a `WEB_USERNAME`** impostato nel file `.env` del bot.
    ```bash
    python scripts/add_user.py
    ```

### 2. Avvio dell'Applicazione

Dalla cartella principale del progetto, esegui questo comando:

```bash
docker-compose up --build -d
```

Questo comando:
*   `--build`: Ricostruisce le immagini Docker per includere le tue configurazioni.
*   `-d`: Avvia i container in background (detached mode).

### 3. Accesso

*   **Web Interface**: Apri il browser e vai su **`https://localhost:8443`**.
    *   Il browser mostrerà un avviso di sicurezza a causa del certificato autofirmato. Accetta il rischio e procedi.
    *   Effettua il login con le credenziali create con `add_user.py`.
    *   L'interfaccia rileverà automaticamente la lingua del tuo browser. Puoi cambiarla manualmente usando il selettore in alto a destra.

*   **Telegram Bot**: Avvia una chat con il tuo bot su Telegram e inviagli dei link. Appariranno istantaneamente nell'interfaccia web!

### 3.1 Comandi del Bot (Italiano)

Il bot supporta i seguenti comandi nelle chat private.

1.  `/help`
Mostra guida rapida e riepilogo comandi.

2.  `/count`
Mostra quanti bookmark sono salvati per il tuo account web collegato.

3.  `/register`
Mostra le istruzioni per collegare il tuo account Telegram a un utente web.

4.  `/link <token>`
Collega il tuo account Telegram al tuo utente web usando un token monouso generato da un admin dal pannello web.

5.  `/whoami`
Mostra a quale utente web sei attualmente collegato.

6.  `/unlink`
Rimuove il collegamento tra il tuo account Telegram e l'utente web.

Note operative:
1.  Se non sei collegato, il bot non salva i bookmark e ti chiede di eseguire `/register` e `/link <token>`.
2.  Il token di linking e monouso e ha scadenza.
3.  Un admin puo generare token dal pannello utenti dell'interfaccia web.

### 4. Gestione dell'Applicazione

Per fermare tutti i container, esegui:

```bash
docker-compose down
```

Questo comando ferma e rimuove i container e la rete, ma **non cancella i dati** salvati nei volumi (database, sessione del bot e certificati SSL).

### 5. Test rapido dei tag Gemini in locale

Lo script [webserver/scripts/test_gemini_tags.py](webserver/scripts/test_gemini_tags.py) carica automaticamente [webserver/.env](webserver/.env) se presente, senza sovrascrivere eventuali variabili d'ambiente gia impostate nella shell. Dalla root del progetto puoi eseguirlo cosi:

```powershell
python webserver/scripts/test_gemini_tags.py --url https://example.com
```

Esempio con titolo e descrizione manuali:

```powershell
python webserver/scripts/test_gemini_tags.py --title "SQLite tips" --description "Practical notes for schema migrations"
```

---
## 🌐 Internazionalizzazione (i18n)

L'interfaccia web supporta più lingue (attualmente inglese e italiano).

### Come funziona

La lingua viene determinata con la seguente priorità:
1.  **Parametro URL**: Puoi forzare una lingua aggiungendo `?lang=it` o `?lang=en` all'URL.
2.  **Cookie**: Se hai già selezionato una lingua, la scelta viene salvata in un cookie (`lang`) e riutilizzata.
3.  **Header del Browser**: Se non ci sono cookie o parametri, il server controlla l'header `Accept-Language` inviato dal tuo browser.
4.  **Default**: Se nessuna delle opzioni precedenti ha successo, viene usato l'inglese (`en`).

### Come aggiungere una nuova lingua

1.  **Crea il file di traduzione**: Nella cartella `webserver/locales/`, crea un nuovo file JSON (es. `es.json` per lo spagnolo). Copia il contenuto di `en.json` e traduci tutti i valori.
2.  **Aggiorna il server**: Apri `webserver/server.py` e aggiungi il nuovo codice lingua alla lista `SUPPORTED_LANGUAGES`.
    ```python
    SUPPORTED_LANGUAGES = ['en', 'it', 'es'] # Aggiungi 'es'
    ```
3.  **Aggiorna l'interfaccia**: Apri `webserver/htmldata.py` e aggiungi la nuova opzione al menu a tendina `<select id="langSelector">`.

---

## 🇬🇧 English Instructions (Docker)

### Prerequisites

*   Docker
*   Docker Compose

### 1. Setup

**a. Configure the Bot:** Create a file named `.env` inside the `telegram_bot/` folder with your Telegram API credentials and the target web user.

```ini
# Example file: telegram_bot/.env
API_ID=...
API_HASH=...
BOT_TOKEN=...
WEB_USERNAME=my_web_user
```

**b. Create a Web User:** The bot needs a webserver user to associate bookmarks with. Run the `add_user.py` script. Make sure the username you create matches the `WEB_USERNAME` you set in the bot's `.env` file.

```bash
# Install dependency (for this script only)
pip install werkzeug
# Run the script and follow the prompts
python scripts/add_user.py
```

### 2. Run the Application

From the project root directory, run:
```bash
docker-compose up --build -d
```

### 3. Access

*   **Web Interface**: Open your browser and navigate to **`https://localhost:8443`**. You will see a security warning due to the self-signed certificate; please proceed. Log in with the credentials you created.
*   **Telegram Bot**: Start a chat with your bot on Telegram and send it links. They will appear in the web interface.
*   **Language**: The interface will automatically detect your browser's language. You can switch it manually using the selector in the top right.

### 3.1 Bot Commands (English)

The bot supports the following commands in private chats.

1.  `/help`
Shows quick help and command summary.

2.  `/count`
Shows how many bookmarks are saved for your linked web account.

3.  `/register`
Shows instructions to link your Telegram account to a web user.

4.  `/link <token>`
Links your Telegram account to your web user using a one-time token generated by an admin from the web panel.

5.  `/whoami`
Shows which web user your Telegram account is currently linked to.

6.  `/unlink`
Removes the link between your Telegram account and the web user.

Operational notes:
1.  If your account is not linked, the bot will not save bookmarks and will ask you to run `/register` and `/link <token>`.
2.  Linking tokens are one-time and expire.
3.  Admins can generate tokens from the web user management page.

### 4. Application Management

To stop all services, run:
```bash
docker-compose down
```

### 5. Quick local Gemini tag test

The script [webserver/scripts/test_gemini_tags.py](webserver/scripts/test_gemini_tags.py) automatically loads [webserver/.env](webserver/.env) when present, without overriding environment variables already set in the shell. From the project root, run:

```powershell
python webserver/scripts/test_gemini_tags.py --url https://example.com
```

Manual title/description example:

```powershell
python webserver/scripts/test_gemini_tags.py --title "SQLite tips" --description "Practical notes for schema migrations"
```