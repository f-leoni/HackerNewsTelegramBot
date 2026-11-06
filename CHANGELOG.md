# Changelog

Il progetto usa tre numeri di versione indipendenti: webserver, bot Telegram e schema database.
Lo schema è tracciato anche in `PRAGMA user_version`.

## webserver 3.0.0 · bot 2.0.0 · schema DB 2 — 2026-11-06

Release multi-utente. **Breaking**: aggiornare bot e webserver insieme.

### Sicurezza
- Corretto IDOR su `DELETE /api/bookmarks/<id>`: la cancellazione è ora limitata al proprietario e risponde `404` per bookmark altrui o inesistenti.
- Cookie di sessione `HttpOnly`, `SameSite=Lax`, `Secure` automatico su HTTPS.
- Il cambio password revoca tutte le altre sessioni dell'utente.
- Rate limit sul login (10 tentativi falliti / 15 minuti per IP+username).
- CORS ristretto all'origine del servizio (niente più `Access-Control-Allow-Origin: *`).
- Il bot autorizza il mittente **prima** di scraping e tagging: un account non collegato non può usarlo come proxy.

### Dati
- `UNIQUE(user_id, url)` e foreign key su `users` applicate anche ai database esistenti tramite ricostruzione della tabella `bookmarks`.
- Duplicati `(user_id, url)` consolidati mantenendo la riga più recente.
- Indici su `bookmarks(user_id)` e `sessions(user_id)`; `PRAGMA user_version = 2`.
- `delete_user_api` rimuove anche collegamenti Telegram e token pendenti.
- WAL, `busy_timeout` e `foreign_keys=ON` su ogni connessione (bot e webserver scrivono lo stesso file).

### Bot
- Nuovo `/start` con stato del collegamento.
- Collegamento Telegram ↔ utente web tramite token monouso (`/register`, `/link`, `/whoami`, `/unlink`).
- Scraping, tagging e SQLite spostati fuori dall'event loop (`asyncio.to_thread`).
- Salvataggio non distruttivo: un URL già presente conserva `is_read`, `rating` e tag manuali.
- Cap di 10 URL per messaggio, rate limit per utente, gestione `FloodWait` e errore DB occupato.
- Sessione Pyrogram salvata in `SESSION_DIR` o in una directory persistente.

### Infrastruttura
- `ThreadingHTTPServer`, cache delle traduzioni, `check_env.py` con exit code reale.
- `.dockerignore` esclude `.env`, `*.session`, `*.db` e `privato.txt` dall'immagine.
- `scripts/migrate_bookmarks.py` collision-safe e con exit code corretto; su installazione senza utenti esce `0`.
- `backup_oci.py` riconosce la sessione Telegram nelle nuove posizioni.

### Migrazione
- I bookmark storici senza proprietario vengono assegnati al primo utente da `scripts/migrate_bookmarks.py`.
- Se non esiste alcun admin, il primo utente viene promosso automaticamente all'avvio.
- Dopo il rilascio ogni account Telegram deve essere collegato: pannello **Utenti** → genera token → `/link <token>`.
- Il rollback del codice non annulla la migrazione dello schema: ripristinare il database dal backup.
