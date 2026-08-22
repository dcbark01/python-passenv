"""Exception hierarchy for :mod:`passenv`."""

from __future__ import annotations

__all__ = [
    "KeyCollisionError",
    "NamespaceNotFoundError",
    "PassDecryptError",
    "PassEnvError",
    "PassNotFoundError",
]


class PassEnvError(Exception):
    """Base class for every error raised by :mod:`passenv`."""


class PassNotFoundError(PassEnvError):
    """The ``pass`` executable could not be found on ``$PATH``."""

    def __init__(self, message: str = "the `pass` executable was not found on PATH") -> None:
        super().__init__(message)


class PassDecryptError(PassEnvError):
    """``pass show`` exited with a non-zero status for an entry."""

    def __init__(self, entry: str, returncode: int, stderr: str) -> None:
        self.entry = entry
        self.returncode = returncode
        self.stderr = stderr
        detail = stderr.strip()
        message = f"`pass show {entry}` failed with exit code {returncode}"
        if detail:
            message = f"{message}: {detail}"
        super().__init__(message)


class NamespaceNotFoundError(PassEnvError):
    """A requested namespace does not exist in the password store."""

    def __init__(self, namespace: str, store_dir: str) -> None:
        self.namespace = namespace
        self.store_dir = store_dir
        super().__init__(f"namespace {namespace!r} not found in password store {store_dir!r}")


class KeyCollisionError(PassEnvError):
    """Two entries in the same load map to the same environment variable name."""

    def __init__(self, key: str, entries: tuple[str, ...] | list[str]) -> None:
        self.key = key
        self.entries = tuple(entries)
        joined = ", ".join(self.entries)
        super().__init__(f"key {key!r} is produced by multiple entries: {joined}")
