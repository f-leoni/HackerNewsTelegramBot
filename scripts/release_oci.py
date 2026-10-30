"""Deploy a trusted source tree to the existing OCI systemd installation."""

import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import shutil
import subprocess
import sys


COMPONENTS = ("shared", "telegram_bot", "webserver", "scripts")
SERVICES = ("hackernewsweb.service", "hackernewsbot.service")
EXCLUDES = (
    ".env*", "*.session*", "*.db*", "__pycache__", "*.pyc",
    ".venv", "venv", "certs", "*.log", "*.bak", "server.err",
)


def run(*command, check=True):
    return subprocess.run(command, check=check)


def sync_code(source, destination, delete=False):
    for component in COMPONENTS:
        origin = source / component
        if not origin.is_dir():
            continue
        target = destination / component
        target.mkdir(parents=True, exist_ok=True)
        command = ["rsync", "-a", "--safe-links"]
        if delete:
            command.append("--delete")
        for pattern in EXCLUDES:
            command.extend(("--exclude", pattern))
        if component == "shared":
            command.extend(("--exclude", "/db/"))
        command.extend((str(origin) + "/", str(target) + "/"))
        run(*command)


def validate_source(source):
    for relative in (
        "shared/database.py", "shared/requirements.txt",
        "telegram_bot/bot.py", "telegram_bot/requirements.txt",
        "webserver/server.py", "webserver/requirements.txt",
        "webserver/htmldata.py", "webserver/static/app.js",
        "webserver/locales/en.json", "webserver/locales/it.json",
    ):
        if not (source / relative).is_file():
            raise ValueError("Missing release file: " + relative)
    for component in COMPONENTS:
        folder = source / component
        if folder.is_symlink():
            raise ValueError("Source component cannot be a symlink: " + component)
        if folder.is_dir() and any(path.is_symlink() for path in folder.rglob("*")):
            raise ValueError("Source tree cannot contain symlinks: " + component)


def is_active(service):
    return run("systemctl", "is-active", "--quiet", service, check=False).returncode == 0


def check_web():
    import time
    import urllib.error
    import urllib.request

    for attempt in range(10):
        try:
            with urllib.request.urlopen("http://127.0.0.1:8000/", timeout=3) as response:
                if response.status == 200:
                    return
        except (OSError, urllib.error.URLError):
            pass
        if attempt < 9:
            time.sleep(1)
    raise RuntimeError("Local web health check failed")


def deploy(source, acknowledge_linking):
    if sys.platform != "linux":
        raise ValueError("--apply is supported only on the Linux OCI VM")
    if os.geteuid() != 0:
        raise ValueError("--apply requires root (sudo)")
    import fcntl

    os.umask(0o022)
    if not acknowledge_linking:
        raise ValueError("Read the Telegram migration warning and add --acknowledge-telegram-linking")
    for executable in ("rsync", "systemctl", "runuser", "chown"):
        if shutil.which(executable) is None:
            raise ValueError("Required command not found: " + executable)

    project = Path("/opt/hnbot/app")
    environment = Path("/opt/hnbot/.venv")
    backup_script = Path("/usr/local/sbin/hnbot-backup.py")
    if source == project or project in source.parents:
        raise ValueError("Release source must be outside /opt/hnbot/app")
    for required in (
        backup_script, environment / "bin/python", project / "shared/db/bookmarks.db",
        project / "telegram_bot/.env", project / "webserver/.env",
    ):
        if not required.is_file():
            raise ValueError("Missing production file: " + str(required))
    if not all(is_active(service) for service in SERVICES):
        raise ValueError("Both production services must be active before deployment")

    with open("/run/hnbot-release.lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        releases = Path("/opt/hnbot/releases")
        releases.mkdir(mode=0o755, exist_ok=True)
        release = releases / timestamp
        release.mkdir(mode=0o755)
        staged = release / "code"
        staged.mkdir(mode=0o755)
        sync_code(source, staged)
        new_environment = release / "venv"
        run("/usr/bin/python3", "-m", "venv", str(new_environment))
        requirements = []
        for component in ("shared", "telegram_bot", "webserver"):
            requirements.extend(("-r", str(staged / component / "requirements.txt")))
        run(str(new_environment / "bin/python"), "-m", "pip", "install", *requirements)
        run(str(new_environment / "bin/python"), "-m", "pip", "check")
        run(str(new_environment / "bin/python"), "-m", "compileall", "-q", str(staged))
        run("runuser", "-u", "hnbot", "--", str(new_environment / "bin/python"),
            "-c", "import pyrogram, tgcrypto, dotenv, requests, bs4, werkzeug")

        rollback = Path("/var/backups/hnbot-releases") / timestamp
        rollback.mkdir(mode=0o700, parents=True)
        previous_code = rollback / "code"
        previous_code.mkdir(mode=0o700)
        sync_code(project, previous_code)
        previous_environment = Path("/opt/hnbot/.venv-before-" + timestamp)
        timer_active = is_active("hnbot-backup.timer")
        stopped = False
        environment_moved = False
        code_changed = False
        try:
            if timer_active:
                run("systemctl", "stop", "hnbot-backup.timer")
            run("systemctl", "stop", "hnbot-backup.service")
            stopped = True
            run("systemctl", "stop", *SERVICES)
            run("/usr/bin/python3", str(backup_script))
            environment.rename(previous_environment)
            environment_moved = True
            environment.symlink_to(new_environment, target_is_directory=True)
            code_changed = True
            sync_code(staged, project, delete=True)
            for component in COMPONENTS:
                if (project / component).is_dir():
                    run("chown", "-R", "hnbot:hnbot", str(project / component))
            run("systemctl", "start", SERVICES[0])
            check_web()
            run("systemctl", "start", SERVICES[1])
            import time
            time.sleep(5)
            if not all(is_active(service) for service in SERVICES):
                raise RuntimeError("A service exited after startup")
        except BaseException:
            if stopped:
                run("systemctl", "stop", *SERVICES)
                if code_changed:
                    sync_code(previous_code, project, delete=True)
                if environment_moved:
                    if environment.is_symlink():
                        environment.unlink()
                    previous_environment.rename(environment)
                run("systemctl", "start", *SERVICES)
                print("Previous code and environment restored. Database was NOT rolled back.", file=sys.stderr)
            raise
        finally:
            if timer_active:
                run("systemctl", "start", "hnbot-backup.timer")
        print("Release completed: " + timestamp)
        print("Previous code: " + str(previous_code))
        print("Previous environment: " + str(previous_environment))
        print("Verify Telegram /whoami, /count, saving a link, web editing and star ratings.")
        print("If unlinked: generate a token in /users, then send /link TOKEN to the bot.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="Trusted extracted release directory")
    parser.add_argument("--apply", action="store_true", help="Actually update the OCI installation")
    parser.add_argument("--acknowledge-telegram-linking", action="store_true",
                        help="Accept that Telegram users may need linking before saving bookmarks")
    args = parser.parse_args()
    source = args.source.resolve()
    try:
        validate_source(source)
        if not args.apply:
            print("PLAN ONLY: no services, files or databases changed.")
            print("Source: " + str(source))
            print("Target: /opt/hnbot/app; services: " + ", ".join(SERVICES))
            print("Prepare venv -> stop services -> backup -> sync code -> start and check.")
            print("Preserved: .env, SQLite databases, Telegram sessions, certificates.")
            print("WARNING: new bot requires Telegram/web account linking through /users and /link.")
            print("Rollback restores code/venv only; schema migrations and data remain unchanged.")
            return 0
        deploy(source, args.acknowledge_telegram_linking)
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        print("Release failed: " + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())