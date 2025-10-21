# Python base image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Install necessary system dependencies (if any)
# RUN apt-get update && apt-get install -y ...

# Copy dependency files before the code to leverage Docker's cache
COPY telegram_bot/requirements.txt ./bot-requirements.txt
COPY shared/requirements.txt ./shared-requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r bot-requirements.txt -r shared-requirements.txt

# Copy the source code of the bot and the shared library
COPY telegram_bot/ /app/telegram_bot/
COPY shared/ /app/shared/
COPY migrate_bookmarks.py .

# Default command to start the bot
CMD ["python3", "-m", "telegram_bot.bot"]