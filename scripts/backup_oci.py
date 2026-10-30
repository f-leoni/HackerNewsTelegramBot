"""Create consistent SQLite snapshots and a private deployment archive."""

import argparse
from contextlib import closing
from datetime import datetime, timezone
import os
from pathlib import Path
import shutil
import sqlite3
import tarfile
import tempfile


def backup_database(source, destination):
    source = Path(source).resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as original:
        with closing(sqlite3.connect(str(destination))) as snapshot:
            original.backup(snapshot)
            if snapshot.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
                raise RuntimeError("Invalid SQLite snapshot: " + str(source))


def archive_filter(member):
    parts = Path(member.name).parts
    if any(part in {"__pycache__", ".git", ".venv", "venv", "certs"} for part in parts):
        return None
    if member.name == "app/shared/db" or member.name.startswith("app/shared/db/"):
        return None
    if ".session" in parts[-1] or parts[-1].endswith((".log", ".pyc")):
        return None
    return member


def create_backup(project, output, keep=14, config_paths=()):
    if keep < 1:
        raise ValueError("keep must be at least 1")
    project = Path(project)
    output = Path(output)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    with tempfile.TemporaryDirectory(prefix="hnbot-backup-") as temporary:
        staging = Path(temporary)
        database = Path("app/shared/db/bookmarks.db")
        backup_database(project / "shared/db/bookmarks.db", staging / database)
        snapshots = [database]
        session = Path("app/telegram_bot/bookmark_bot_session.session")
        if (project / "telegram_bot/bookmark_bot_session.session").is_file():
            backup_database(project / "telegram_bot/bookmark_bot_session.session", staging / session)
            snapshots.append(session)

        output.mkdir(parents=True, exist_ok=True, mode=0o750)
        with tempfile.NamedTemporaryFile(dir=output, prefix=".hnbot-", delete=False) as handle:
            pending = Path(handle.name)
        try:
            with tarfile.open(pending, "w:gz") as archive:
                for directory in ("telegram_bot", "shared", "webserver", "scripts"):
                    source = project / directory
                    if source.is_dir():
                        archive.add(source, arcname="app/" + directory, filter=archive_filter)
                for snapshot in snapshots:
                    archive.add(staging / snapshot, arcname=snapshot.as_posix())
                for config_path in config_paths:
                    config = Path(config_path)
                    archive.add(config, arcname="config/" + config.as_posix().lstrip("/"))
            pending.chmod(0o640)
            completed = output / ("hnbot-" + timestamp + ".tar.gz")
            os.replace(pending, completed)
        finally:
            if pending.exists():
                pending.unlink()

        with tempfile.NamedTemporaryFile(dir=output, prefix=".latest-", delete=False) as handle:
            pending_latest = Path(handle.name)
        try:
            shutil.copyfile(completed, pending_latest)
            pending_latest.chmod(0o640)
            os.replace(pending_latest, output / "latest.tar.gz")
        finally:
            if pending_latest.exists():
                pending_latest.unlink()

    for expired in sorted(output.glob("hnbot-*.tar.gz"), reverse=True)[keep:]:
        expired.unlink()
    return completed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=Path("/opt/hnbot/app"))
    parser.add_argument("--output", type=Path, default=Path("/var/backups/hnbot"))
    parser.add_argument("--keep", type=int, default=14)
    args = parser.parse_args()
    configs = (
        "/etc/caddy/Caddyfile",
        "/etc/systemd/system/hackernewsbot.service",
        "/etc/systemd/system/hackernewsweb.service",
    )
    print(create_backup(args.project, args.output, args.keep, configs))


if __name__ == "__main__":
    main()