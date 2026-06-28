from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_dockerfile_uses_migration_script_from_scripts_folder():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "COPY scripts/migrate_bookmarks.py /app/scripts/migrate_bookmarks.py" in dockerfile


def test_compose_db_init_points_to_new_script_path():
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert "command: python3 scripts/migrate_bookmarks.py" in compose


def test_readme_uses_new_add_user_command_path():
    readme = (ROOT / "readme.md").read_text(encoding="utf-8")
    assert "python scripts/add_user.py" in readme