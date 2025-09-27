from dotenv import load_dotenv
import os
here = 'telegram_bot/.env'
print('exists', os.path.exists(here))
if os.path.exists(here):
    load_dotenv(here)
print('BOT_TOKEN=', bool(os.getenv('BOT_TOKEN')))
print('SESSION_STRING=', bool(os.getenv('SESSION_STRING')))
print('API_ID=', os.getenv('API_ID'))
print('API_HASH=', bool(os.getenv('API_HASH')))