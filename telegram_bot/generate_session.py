"""
Helper to generate a Pyrogram user session file interactively.

Run this from a regular terminal (PowerShell) to avoid debugger/IDE interference
which can sometimes cause the Telegram auth flow to fail with low-level errors
like: "'BadMsgNotification' object has no attribute 'type'".

Usage:
  pwsh> python telegram_bot/generate_session.py

This script will:
- load API_ID and API_HASH from the local `.env` inside `telegram_bot/` (or from parent)
- start a temporary Pyrogram Client which will prompt for the phone/code
- create a local `.session` file (e.g. `bookmark_bot.session`) on success

If the interactive auth fails with the BadMsgNotification error, the script prints
diagnostics and recommended next steps (sync clock, upgrade pyrogram/tgcrypto,
run from a non-debug terminal, or try a different network).
"""
import os
import sys
import logging
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def find_env_locations():
    roots = [os.getcwd(), os.path.dirname(__file__), os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))]
    seen = []
    for r in roots:
        if r and r not in seen:
            seen.append(r)
            yield os.path.join(r, '.env')


def main():
    # Load any .env found in the project or telegram_bot folder
    for envpath in find_env_locations():
        if os.path.exists(envpath):
            logger.info('Loading env from %s', envpath)
            load_dotenv(envpath, override=False)

    api_id = os.getenv('API_ID')
    api_hash = os.getenv('API_HASH')
    bot_token = os.getenv('BOT_TOKEN')

    if bot_token:
        logger.error('BOT_TOKEN is set. This helper creates a user session (not a bot). Remove BOT_TOKEN from .env and re-run.')
        sys.exit(2)

    if not api_id or not api_hash:
        logger.error('API_ID and API_HASH must be set in .env (see .env.example). Aborting.')
        sys.exit(2)

    # Create a temporary client which will generate a local .session file
    try:
        from pyrogram import Client
    except Exception as e:
        logger.error('Could not import pyrogram: %s', e)
        logger.info('Install requirements: pip install -r requirements-full.txt')
        sys.exit(1)

    session_name = 'bookmark_bot'
    logger.info('Starting Pyrogram client (session: %s). Please run this from a normal terminal (not VSCode debugger).', session_name)

    app = Client(session_name, api_id=api_id, api_hash=api_hash)

    try:
        app.start()
        me = app.get_me()
        logger.info('Success! Logged in as: %s (id=%s)', getattr(me, 'username', None) or getattr(me, 'first_name', ''), me.id)
        logger.info('A session file was created: %s.session (or equivalent). You can now run the main bot.', session_name)
        logger.info('If you need a StringSession for headless runs, let me know and I can add a generator that exports a StringSession.')
    except AttributeError as e:
        # Surface the specific BadMsgNotification issue seen in some environments
        logger.error('AttributeError during interactive auth: %s', e)
        logger.error("This commonly happens when the system time is out of sync or when the IDE/debugger interferes with the auth flow.")
        logger.info('Recommended steps:')
        logger.info('  1) Ensure your system clock is correct (enable internet time sync).')
        logger.info('  2) Update Pyrogram and tgcrypto: pip install -U pyrogram tgcrypto')
        logger.info('  3) Run this script from a plain terminal (PowerShell) rather than from inside an IDE debugger.')
        logger.info('  4) If the error persists, try on a different network or device. You can also create the session string on another machine and copy it here.')
        logger.debug('Full exception:', exc_info=True)
        sys.exit(3)
    except Exception:
        logger.exception('Unexpected error during session creation')
        sys.exit(4)
    finally:
        try:
            app.stop()
        except Exception:
            pass


if __name__ == '__main__':
    main()
