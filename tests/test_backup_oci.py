import os
from contextlib import closing
from pathlib import Path
import sqlite3
import tarfile

import pytest

from scripts.backup_oci import create_backup


def make_project(root):
    project = root / "app"
    database = project / "shared/db/bookmarks.db"
    database.parent.mkdir(parents=True)
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute("CREATE TABLE bookmarks (title TEXT)")
        connection.execute("INSERT INTO bookmarks VALUES ('Saved bookmark')")
    bot = project / "telegram_bot"
    bot.mkdir()
    (bot / ".env").write_text("BOT_TOKEN=test-placeholder", encoding="utf-8")
    (bot / "bot.py").write_text("print('bot')", encoding="utf-8")
    with closing(sqlite3.connect(bot / "bookmark_bot_session.session")) as connection, connection:
        connection.execute("CREATE TABLE sessions (id INTEGER)")
    (bot / "bookmark_bot_session.session-journal").write_bytes(b"")
    (bot / "old.session").write_bytes(b"obsolete session")
    return project


def test_archive_contains_valid_snapshots_config_and_code(tmp_path):
    project = make_project(tmp_path)
    output = tmp_path / "backups"
    completed = create_backup(project, output)
    with tarfile.open(completed) as archive:
        names = archive.getnames()
        assert "app/telegram_bot/.env" in names
        assert "app/telegram_bot/bot.py" in names
        assert "app/telegram_bot/old.session" not in names
        assert not any(name.endswith("-journal") for name in names)
        for name in (
            "app/shared/db/bookmarks.db",
            "app/telegram_bot/bookmark_bot_session.session",
        ):
            assert names.count(name) == 1
            restored = tmp_path / Path(name).name
            restored.write_bytes(archive.extractfile(name).read())
            with sqlite3.connect(restored) as connection:
                assert connection.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        with sqlite3.connect(tmp_path / "bookmarks.db") as connection:
            assert connection.execute("SELECT title FROM bookmarks").fetchone() == ("Saved bookmark",)
    assert (output / "latest.tar.gz").read_bytes() == completed.read_bytes()
    if os.name != "nt":
        assert completed.stat().st_mode & 0o777 == 0o640


def test_backup_includes_committed_wal_data(tmp_path):
    project = make_project(tmp_path)
    with sqlite3.connect(project / "shared/db/bookmarks.db") as writer:
        writer.execute("PRAGMA journal_mode=WAL")
        writer.execute("INSERT INTO bookmarks VALUES ('WAL bookmark')")
        writer.commit()
        completed = create_backup(project, tmp_path / "backups")
    with tarfile.open(completed) as archive:
        snapshot = tmp_path / "wal-snapshot.db"
        snapshot.write_bytes(archive.extractfile("app/shared/db/bookmarks.db").read())
    with sqlite3.connect(snapshot) as connection:
        assert connection.execute("SELECT COUNT(*) FROM bookmarks").fetchone() == (2,)


def test_retention_and_missing_database_preserve_latest(tmp_path):
    project = make_project(tmp_path)
    output = tmp_path / "backups"
    first = create_backup(project, output, keep=1)
    second = create_backup(project, output, keep=1)
    assert not first.exists()
    assert second.exists()
    latest = (output / "latest.tar.gz").read_bytes()
    (project / "shared/db/bookmarks.db").unlink()
    with pytest.raises(FileNotFoundError):
        create_backup(project, output, keep=1)
    assert (output / "latest.tar.gz").read_bytes() == latest
    assert not (project / "shared/db/bookmarks.db").exists()