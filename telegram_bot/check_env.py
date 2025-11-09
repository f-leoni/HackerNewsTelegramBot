from dotenv import load_dotenv
import os
env_path = 'telegram_bot/.env'
print(f"Checking for .env file at: {env_path}")
print(f"Exists: {os.path.exists(env_path)}")
if os.path.exists(env_path):
    load_dotenv(env_path)
print(f"BOT_TOKEN set: {bool(os.getenv('BOT_TOKEN'))}")
print(f"SESSION_STRING set: {bool(os.getenv('SESSION_STRING'))}")
print(f"API_ID set: {bool(os.getenv('API_ID'))}")
print(f"API_HASH set: {bool(os.getenv('API_HASH'))}")