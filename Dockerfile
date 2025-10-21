# Immagine di base Python
FROM python:3.10-slim

# Imposta la directory di lavoro nel container
WORKDIR /app

# Installa le dipendenze di sistema necessarie (se ce ne fossero)
# RUN apt-get update && apt-get install -y ...

# Copia i file delle dipendenze prima del codice per sfruttare la cache di Docker
COPY telegram_bot/requirements.txt ./bot-requirements.txt
COPY shared/requirements.txt ./shared-requirements.txt

# Installa le dipendenze Python
RUN pip install --no-cache-dir -r bot-requirements.txt -r shared-requirements.txt

# Copia il codice sorgente del bot e della libreria condivisa
COPY telegram_bot/ /app/telegram_bot/
COPY shared/ /app/shared/
COPY migrate_bookmarks.py .

# Comando di default per avviare il bot
CMD ["python3", "-m", "telegram_bot.bot"]