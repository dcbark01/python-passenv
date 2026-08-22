"""Fixtures that stand up a throwaway GPG key and password store."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

REQUIRED_BINARIES = ("pass", "gpg")

ENTRIES = {
    "project_a/api_token": "integration-token\n",
    "project_a/db/dsn": "integration-db-dsn\n",
    "project_a/tls_cert": "-----BEGIN KEY-----\nline two\n-----END KEY-----\n",
    "shared/webhook_url": "https://hooks.example.invalid/integration\n",
}


@pytest.fixture(scope="session")
def _binaries() -> None:
    missing = [name for name in REQUIRED_BINARIES if shutil.which(name) is None]
    if missing:
        pytest.skip(f"missing required binaries: {', '.join(missing)}")


def _short_tempdir_base() -> str:
    """The shortest usable temp base: gpg-agent's unix socket path is length-capped."""
    candidates = [path for path in ("/tmp", tempfile.gettempdir()) if os.path.isdir(path)]
    return min(candidates, key=len)


@pytest.fixture(scope="session")
def gnupg_home(_binaries) -> Iterator[Path]:
    """A temporary GNUPGHOME containing one unprotected key."""
    home = Path(tempfile.mkdtemp(prefix="pe", dir=_short_tempdir_base()))
    home.chmod(0o700)
    params = home / "keyparams"
    params.write_text(
        "%no-protection\n"
        "Key-Type: RSA\n"
        "Key-Length: 2048\n"
        "Name-Real: passenv integration\n"
        "Name-Email: passenv@example.invalid\n"
        "Expire-Date: 0\n"
        "%commit\n"
    )
    env = {**os.environ, "GNUPGHOME": str(home)}
    subprocess.run(
        ["gpg", "--batch", "--gen-key", str(params)],
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    try:
        yield home
    finally:
        subprocess.run(
            ["gpgconf", "--homedir", str(home), "--kill", "all"],
            env=env,
            check=False,
            capture_output=True,
        )
        shutil.rmtree(home, ignore_errors=True)


@pytest.fixture(scope="session")
def gpg_fingerprint(gnupg_home: Path) -> str:
    env = {**os.environ, "GNUPGHOME": str(gnupg_home)}
    result = subprocess.run(
        ["gpg", "--batch", "--with-colons", "--list-secret-keys", "--fingerprint"],
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    for line in result.stdout.splitlines():
        if line.startswith("fpr:"):
            return line.split(":")[9]
    raise AssertionError("no fingerprint found in gpg output")


@pytest.fixture(scope="session")
def real_store(
    gnupg_home: Path, gpg_fingerprint: str, tmp_path_factory: pytest.TempPathFactory
) -> Path:
    """A real password store, initialised and populated via the `pass` CLI."""
    store = tmp_path_factory.mktemp("password-store")
    env = {
        **os.environ,
        "GNUPGHOME": str(gnupg_home),
        "PASSWORD_STORE_DIR": str(store),
    }
    subprocess.run(["pass", "init", gpg_fingerprint], env=env, check=True, capture_output=True)
    for entry, contents in ENTRIES.items():
        subprocess.run(
            ["pass", "insert", "-m", "-f", entry],
            input=contents,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
    return store


@pytest.fixture
def pass_env(gnupg_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Point `gpg` at the throwaway keyring for the duration of a test."""
    monkeypatch.setenv("GNUPGHOME", str(gnupg_home))
