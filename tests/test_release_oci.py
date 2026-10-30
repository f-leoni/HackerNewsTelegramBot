from pathlib import Path
from unittest.mock import patch

import pytest

from scripts import release_oci


@pytest.fixture
def source(tmp_path):
    root = tmp_path / "release"
    for relative in (
        "shared/database.py", "shared/requirements.txt",
        "telegram_bot/bot.py", "telegram_bot/requirements.txt",
        "webserver/server.py", "webserver/requirements.txt",
        "webserver/htmldata.py", "webserver/static/app.js",
        "webserver/locales/en.json", "webserver/locales/it.json",
    ):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.touch()
    return root


def test_default_is_plan_only(source, monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["release_oci.py", "--source", str(source)])
    with patch.object(release_oci, "deploy") as deploy:
        assert release_oci.main() == 0
        deploy.assert_not_called()
    assert "PLAN ONLY" in capsys.readouterr().out


def test_missing_source_file_rejected(source):
    (source / "webserver/locales/it.json").unlink()
    with pytest.raises(ValueError, match="Missing release file"):
        release_oci.validate_source(source)


def test_rsync_preserves_production_data(source, tmp_path):
    with patch.object(release_oci, "run") as run:
        release_oci.sync_code(source, tmp_path / "target", delete=True)
    assert run.call_count == 3
    for call in run.call_args_list:
        command = call.args
        assert command[:3] == ("rsync", "-a", "--safe-links")
        assert "--delete" in command
        for pattern in (".env*", "*.session*", "*.db*", "certs"):
            assert command[command.index(pattern) - 1] == "--exclude"
    shared_command = run.call_args_list[0].args
    assert shared_command[shared_command.index("/db/") - 1] == "--exclude"


def test_apply_rejected_outside_linux(source, monkeypatch):
    monkeypatch.setattr("sys.platform", "win32")
    with pytest.raises(ValueError, match="Linux OCI VM"):
        release_oci.deploy(Path(source), acknowledge_linking=True)