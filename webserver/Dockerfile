# Base image
FROM python:3.10-slim

# Set the working directory
WORKDIR /app

# Copy the dependency file and install them
# We put the requirements.txt in the webserver root
COPY webserver/requirements.txt ./webserver-requirements.txt
COPY shared/requirements.txt ./shared-requirements.txt
RUN pip install --no-cache-dir -r webserver-requirements.txt -r shared-requirements.txt

# Copy the webserver source code and the shared library
COPY webserver/server.py .
COPY webserver/htmldata.py .
COPY webserver/static/ /app/static/
COPY shared/ /app/shared/

# Expose the port the server is listening on
EXPOSE 8443

# Startup command
CMD ["python3", "server.py"]