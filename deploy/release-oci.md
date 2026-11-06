# Rilascio sulla VM OCI

Lo script `scripts/release_oci.py` aggiorna l'installazione esistente in
`/opt/hnbot/app`, gestita da `hackernewsbot.service` e `hackernewsweb.service`.
Non viene eseguito automaticamente e non modifica Caddy, DNS o firewall.

## Preparazione

- Eseguire i test della release e provare le migrazioni su una copia del database.
- Caricare una directory sorgente completa e fidata, per esempio
  `/home/ubuntu/hnbot-release`, fuori dalla directory dell'applicazione attiva.
- Includere `shared`, `telegram_bot`, `webserver` e, se presente, `scripts`.
  Includere i rispettivi `requirements.txt`, le traduzioni e gli asset statici.
- Non caricare database, sessioni o segreti dal PC. Quelli della VM rimangono in uso.
- Caricare lo script di rilascio in `/home/ubuntu/release_oci.py`.
- Verificare che il backup esterno sul NAS sia aggiornato.

La cartella sorgente si costruisce in locale con:

```powershell
.\deploy\build_release.ps1 -Archive
```

Lo script copia i quattro componenti applicando le stesse esclusioni di
`release_oci.py` (`.env`, sessioni, database, cache, certificati), verifica la
presenza dei file obbligatori, verifica che non siano finiti segreti e stampa le
versioni dichiarate dal codice. Con `-Archive` crea anche `hnbot-release.zip`
con hash SHA256 per il trasferimento.

Comando PowerShell per trasferire il solo script dalla root del workspace:

```powershell
& "$env:WINDIR\System32\OpenSSH\scp.exe" -i "$env:USERPROFILE\.ssh\hnbot-oci.pem" scripts/release_oci.py ubuntu@129.152.20.179:/home/ubuntu/release_oci.py
```

## Piano senza modifiche

Sulla VM:

```bash
python3 /home/ubuntu/release_oci.py --source /home/ubuntu/hnbot-release
```

Questo controllo verifica la struttura dei sorgenti, non sostituisce test,
simulazione delle migrazioni o controlli delle dipendenze.

## Applicazione esplicita

Solo dopo aver approvato e verificato la release:

```bash
sudo python3 /home/ubuntu/release_oci.py \
  --source /home/ubuntu/hnbot-release \
  --apply --acknowledge-telegram-linking
```

Lo script richiede Linux, `rsync`, `runuser`, `chown`, systemd, l'utente `hnbot`,
entrambi i servizi applicativi attivi e il backup gia installato in
`/usr/local/sbin/hnbot-backup.py`.

Prepara un ambiente Python separato in `/opt/hnbot/releases`, installa le
dipendenze e ne verifica gli import prima di fermare i servizi. Poi sospende
il timer dei backup, ferma i servizi, crea un backup, sostituisce solo il codice
e il riferimento all'ambiente Python, riavvia e controlla i servizi.
Database, file `.env`, sessioni Telegram e certificati sono esclusi dalla
sincronizzazione. Il sito puo rispondere 502 durante il breve fermo.

Se il controllo web o l'avvio falliscono, tenta il ripristino di codice e
ambiente precedenti. Il database NON viene ripristinato automaticamente:
le migrazioni devono essere compatibili con il vecchio codice. Un rollback
fallito richiede intervento manuale e verifica dei log. Non rimuovere vecchie
release o ambienti finche si vuole conservarne la possibilita di ripristino.

## Collegamento Telegram e verifiche finali

La nuova versione richiede un collegamento esplicito tra account Telegram e
utente web. Se manca, il bot non salva nuovi bookmark: accedere a `/users`
come amministratore, generare un token e inviare `/link TOKEN` al bot.
In assenza di amministratori, la migrazione promuove l'utente web piu vecchio.
Non vengono dedotte associazioni dai bookmark storici.

La verifica automatica copre la pagina di login e lo stato dei servizi, non
la connessione Telegram o il funzionamento completo. Dopo il rilascio verificare
`/whoami`, `/count`, un nuovo link, modifica e valutazione di un bookmark.
Controllare inoltre `journalctl` e il successivo backup scaricato dal NAS.

Le copie di codice precedenti sono in `/var/backups/hnbot-releases`;
gli ambienti precedenti hanno prefisso `/opt/hnbot/.venv-before-`.
Queste directory non sono soggette alla rotazione dei backup giornalieri e
vanno rimosse manualmente soltanto quando non servono piu per il rollback.