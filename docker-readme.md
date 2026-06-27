Viewed Dockerfile:1-23
Listed directory HackerNewsTelegramBot
Viewed docker-compose.yml:1-58

Visto che il tuo progetto è già predisposto con un file `docker-compose.yml` ben strutturato, eseguire il bot e il webserver sul Raspberry Pi come un servizio continuo è piuttosto semplice. 

Il tuo file `docker-compose.yml` include già l'istruzione `restart: always` per entrambi i servizi (bot e webserver). Questo significa che Docker stesso agirà da gestore: avvierà automaticamente i container ogni volta che accendi il Raspberry Pi e li riavvierà in caso di crash.

Ecco la procedura passo-passo per fare il setup sul Raspberry Pi:

### 1. Installa Docker sul Raspberry Pi
Se non hai ancora installato Docker sul tuo Raspberry, apri il terminale del Raspberry ed esegui:

```bash
# Scarica e avvia lo script di installazione ufficiale di Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Aggiungi il tuo utente (es. "pi") al gruppo docker per usarlo senza 'sudo'
sudo usermod -aG docker $USER

# Riavvia il Raspberry Pi per applicare le modifiche ai permessi
sudo reboot
```

### 2. Trasferisci o Clona il progetto
Porta il codice del tuo progetto sul Raspberry. Puoi clonarlo tramite Git oppure copiarlo via SCP/SFTP. Entra nella cartella del progetto:

```bash
cd /percorso/del/tuo/progetto/HackerNewsTelegramBot
```

### 3. Configura i file d'ambiente
Dal tuo `docker-compose.yml` vedo che il sistema si aspetta due file `.env`. Assicurati di crearli e compilarli correttamente sul Raspberry Pi:

- `telegram_bot/.env`
- `webserver/.env`

*Nota: Non committare mai i file `.env` con chiavi reali su GitHub o altri repository pubblici.*

### 4. Avvia come Servizio (Metodo Docker Compose - Consigliato)
Poiché hai già `restart: always` nel docker-compose, il modo più semplice è lasciare che sia Docker a gestire il ciclo di vita. 

Dal terminale, nella cartella del progetto, esegui:

```bash
docker compose up -d --build
```

- `-d` (detached) avvia i container in background.
- `--build` forza la costruzione delle immagini Docker per la prima volta.

**È tutto!** I tuoi container sono ora in esecuzione come un servizio. Sopravviveranno ai riavvii del Raspberry e ai crash. Puoi controllare i log in tempo reale con:
```bash
docker compose logs -f
```

---

### Opzionale: Metodo Systemd (Se preferisci usare `systemctl`)
Se vuoi controllare l'avvio tramite i classici comandi del sistema operativo (es. `sudo systemctl start mio-bot`), puoi creare un servizio *Systemd* personalizzato che invoca Docker Compose. 

1. Crea un nuovo file di servizio:
```bash
sudo nano /etc/systemd/system/hackernews.service
```

2. Inserisci questa configurazione (cambia `/percorso/assoluto/del/tuo/progetto` con la cartella reale dove si trova il file `docker-compose.yml` sul Raspberry):
```ini
[Unit]
Description=HackerNews Telegram Bot e Webserver (Docker Compose)
Requires=docker.service
After=docker.service network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/percorso/assoluto/del/tuo/progetto
# Avvia i container
ExecStart=/usr/bin/docker compose up -d
# Stoppa i container quando il servizio viene fermato
ExecStop=/usr/bin/docker compose down

[Install]
WantedBy=multi-user.target
```

3. Ricarica i servizi, abilita il tuo nuovo servizio all'avvio e fallo partire:
```bash
sudo systemctl daemon-reload
sudo systemctl enable hackernews.service
sudo systemctl start hackernews.service
```

Ora potrai usare i comandi classici come `sudo systemctl status hackernews.service` per gestire l'intero blocco bot+webserver a livello di sistema operativo.