#!/usr/bin/env python3
"""
Test script for Gemini-based tag generation.

Examples:
  python webserver/scripts/test_gemini_tags.py --url https://example.com
  python webserver/scripts/test_gemini_tags.py --title "SQLite tips" --description "Practical notes for schema migrations"
"""
import argparse
import json
import os
from pathlib import Path
import sys

# Ensure shared package is importable
SCRIPT_DIR = Path(__file__).resolve().parents[2]
sys.path.append(str(SCRIPT_DIR))

from shared.utils import extract_domain, get_article_metadata, generate_tags_llm  # noqa: E402


def load_local_env(env_path):
    """Load a simple KEY=VALUE .env file without overriding existing env vars."""
    if not env_path.exists():
        return False

    for raw_line in env_path.read_text(encoding='utf-8').splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue

        key, value = line.split('=', 1)
        key = key.strip()
        if not key or key in os.environ:
            continue

        value = value.strip().strip('"').strip("'")
        os.environ[key] = value

    return True


def main():
    env_path = SCRIPT_DIR / 'webserver' / '.env'
    env_loaded = load_local_env(env_path)

    parser = argparse.ArgumentParser(description="Test Gemini-based bookmark tag generation")
    parser.add_argument('--url', help='Bookmark URL to scrape before generating tags')
    parser.add_argument('--title', default='', help='Title to use for tag generation')
    parser.add_argument('--description', default='', help='Description to use for tag generation')
    parser.add_argument('--domain', default='', help='Domain to use for tag generation')
    parser.add_argument('--count', type=int, default=3, help='Number of tags to request')
    args = parser.parse_args()

    title = args.title
    description = args.description
    domain = args.domain

    if args.url:
        metadata = get_article_metadata(args.url)
        title = metadata.get('title', '') or title
        description = metadata.get('description', '') or description
        domain = metadata.get('domain', '') or domain or extract_domain(args.url)
        print('Scraped metadata:')
        print(json.dumps(metadata, indent=2, ensure_ascii=False))
        print()

    if not title and not description:
        parser.error('Provide --url or at least one of --title/--description')

    gemini_enabled = os.getenv('GEMINI_ENABLED', '').strip().lower() in {'1', 'true', 'yes', 'on'}
    gemini_api_key_present = bool(os.getenv('GEMINI_API_KEY', '').strip())
    gemini_model = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash').strip()

    print('Configuration:')
    print(f'  env file loaded: {env_loaded} ({env_path})')
    print(f'  GEMINI_ENABLED: {gemini_enabled}')
    print(f'  GEMINI_API_KEY present: {gemini_api_key_present}')
    print(f'  GEMINI_MODEL: {gemini_model}')
    print()

    tags = generate_tags_llm(title, description, domain=domain, n=args.count)

    print('Input used for tag generation:')
    print(json.dumps({
        'title': title,
        'description': description,
        'domain': domain,
    }, indent=2, ensure_ascii=False))
    print()

    print('Generated tags:')
    print(json.dumps(tags, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()