"""Preflight check for the Telegram bot environment.

Exits with a non-zero status when the configuration cannot start the bot, so it
can be wired into systemd/docker entrypoints instead of being a debug printer.
"""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

REQUIRED_ONE_OF = ("BOT_TOKEN", "SESSION_STRING")


def main() -> int:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    print(f"Checking for .env file at: {env_path}")
    print(f"Exists: {env_path.exists()}")
    if env_path.exists():
        load_dotenv(env_path, override=False)

    values = {key: bool(os.getenv(key)) for key in ("BOT_TOKEN", "SESSION_STRING", "API_ID", "API_HASH")}
    for key, present in values.items():
        print(f"{key} set: {present}")

    errors = []
    if not any(values[key] for key in REQUIRED_ONE_OF):
        errors.append("Set BOT_TOKEN (bot account) or SESSION_STRING (user account).")

    if values["SESSION_STRING"] and not (values["API_ID"] and values["API_HASH"]):
        errors.append("SESSION_STRING requires both API_ID and API_HASH.")

    if errors:
        print()
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print()
    print("Configuration OK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())