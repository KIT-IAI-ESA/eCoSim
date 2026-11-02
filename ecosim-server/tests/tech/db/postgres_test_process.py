import os
import shutil
import socket
import subprocess
from pathlib import Path

HOST = "127.0.0.1"
SUPERUSER = "cluster_admin"
SUPERUSER_PASSWORD = "cluster_admin_password"
GROUP_REJECTED_ON_MAINTENANCE_DATABASE = "rejected_on_maintenance_database"
ROLE_THAT_DOES_NOT_EXIST = "role_that_does_not_exist"
# without a UTF-8 locale initdb creates SQL_ASCII databases
UTF8_ENVIRONMENT = {**os.environ, "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"}


LOG_SETTINGS = ["log_connections=on", "log_line_prefix='database=%d user=%u '"]


def find_postgres_binaries() -> Path | None:
    on_path = shutil.which("initdb")
    if on_path:
        return Path(on_path).parent
    return next((initdb.parent for initdb in Path("/usr/lib/postgresql").glob("*/bin/initdb")), None)


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind((HOST, 0))
        return int(probe.getsockname()[1])


def start_postgres(
    binaries: Path,
    directory: Path,
    port: int,
    tls: bool,
) -> None:
    _initialize(binaries=binaries, directory=directory)
    _add_access_rules(directory)
    settings = [f"port={port}", f"listen_addresses='{HOST}'", "unix_socket_directories=''", "fsync=off", *LOG_SETTINGS]
    if tls:
        settings += _tls_settings(directory)
    with open(directory / "data" / "postgresql.conf", "a", encoding="utf-8") as file:
        file.write("\n".join(settings) + "\n")
    run_command(binaries / "pg_ctl", "-D", directory / "data", "-l", directory / "server.log", "-w", "start")


def stop_postgres(
    binaries: Path,
    directory: Path,
    check: bool = True,
) -> None:
    run_command(binaries / "pg_ctl", "-D", directory / "data", "-m", "immediate", "-w", "stop", check=check)


def _initialize(
    binaries: Path,
    directory: Path,
) -> None:
    password_file = directory / "superuser_password"
    password_file.write_text(SUPERUSER_PASSWORD, encoding="utf-8")
    run_command(
        binaries / "initdb",
        "-D",
        directory / "data",
        "-U",
        SUPERUSER,
        "--auth=scram-sha-256",
        f"--pwfile={password_file}",
        "--encoding=UTF8",
    )


def _add_access_rules(directory: Path) -> None:
    rules_file = directory / "data" / "pg_hba.conf"
    rules = [
        f"host postgres +{GROUP_REJECTED_ON_MAINTENANCE_DATABASE} {HOST}/32 reject",
        f"host all {ROLE_THAT_DOES_NOT_EXIST} {HOST}/32 trust",
    ]
    rules_file.write_text("\n".join(rules) + "\n" + rules_file.read_text(encoding="utf-8"), encoding="utf-8")


def _tls_settings(directory: Path) -> list[str]:
    certificate = directory / "server.crt"
    key = directory / "server.key"
    run_command("openssl", "req", "-new", "-x509", "-nodes", "-days", "1", "-subj", "/CN=localhost", "-out", certificate, "-keyout", key)
    key.chmod(0o600)
    return ["ssl=on", f"ssl_cert_file='{certificate}'", f"ssl_key_file='{key}'"]


def run_command(
    *command: str | Path,
    check: bool = True,
) -> None:
    subprocess.run([str(part) for part in command], check=check, capture_output=True, env=UTF8_ENVIRONMENT, timeout=60)
