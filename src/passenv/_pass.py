"""Thin wrapper around the ``pass`` command-line tool."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from .errors import PassDecryptError, PassNotFoundError

__all__ = ["run_pass_show"]


def run_pass_show(entry: str, store_dir: Path | None = None) -> str:
    """Return the raw decrypted content of ``entry`` via ``pass show``.

    ``store_dir`` — when given — is exported as ``PASSWORD_STORE_DIR`` for the
    child process, leaving the rest of the environment untouched.
    """
    env = None
    if store_dir is not None:
        env = dict(os.environ)
        env["PASSWORD_STORE_DIR"] = str(store_dir)

    try:
        result = subprocess.run(
            # `--` stops option parsing: an entry named `-c` is an entry, not a flag.
            ["pass", "show", "--", entry],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
    except FileNotFoundError as exc:
        raise PassNotFoundError() from exc

    if result.returncode != 0:
        raise PassDecryptError(entry, result.returncode, result.stderr or "")
    return result.stdout
