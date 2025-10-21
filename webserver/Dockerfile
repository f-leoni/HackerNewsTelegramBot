# Immagine di base
FROM python:3.10-slim

# Imposta la directory di lavoro
WORKDIR /app

# Copia il file delle dipendenze e installale
# Mettiamo il requirements.txt nella root del webserver
COPY webserver/requirements.txt ./webserver-requirements.txt
COPY shared/requirements.txt ./shared-requirements.txt
RUN pip install --no-cache-dir -r webserver-requirements.txt -r shared-requirements.txt

# Copia il codice sorgente del webserver e della libreria condivisa
COPY webserver/server.py .
COPY webserver/htmldata.py .
COPY webserver/static/ /app/static/
COPY shared/ /app/shared/

# Esponi la porta su cui il server è in ascolto
EXPOSE 8443

# Comando di avvio
CMD ["python3", "server.py"]