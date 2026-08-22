"""Password-store layout: locating the store and enumerating its entries."""

from __future__ import annotations

import os
from pathlib import Path

from .errors import NamespaceNotFoundError

__all__ = [
    "DEFAULT_STORE_DIR",
    "iter_entries",
    "normalize_entry",
    "normalize_namespace",
    "resolve_store_dir",
]

DEFAULT_STORE_DIR = "~/.password-store"


def resolve_store_dir(store_dir: str | os.PathLike[str] | None = None) -> Path:
    """Return the password-store directory.

    Precedence: the explicit ``store_dir`` argument, then ``$PASSWORD_STORE_DIR``,
    then ``~/.password-store``. The path is expanded but not required to exist.
    """
    candidate = store_dir if store_dir is not None else os.environ.get("PASSWORD_STORE_DIR")
    if not candidate:
        candidate = DEFAULT_STORE_DIR
    return Path(candidate).expanduser()


def _normalize(value: str, kind: str) -> str:
    """Normalize a store-relative path, refusing anything that climbs out of the store."""
    parts = [part for part in str(value).replace(os.sep, "/").split("/") if part and part != "."]
    if any(part == ".." for part in parts):
        raise ValueError(f"{kind} must not contain '..': {value!r}")
    return "/".join(parts)


def normalize_namespace(namespace: str | None) -> str:
    """Normalize a namespace to a ``/``-joined relative path (``""`` for the store root)."""
    if namespace is None:
        return ""
    return _normalize(namespace, "namespace")


def normalize_entry(entry: str) -> str:
    """Normalize a single entry name, refusing empty names and parent traversal."""
    normalized = _normalize(entry, "entry")
    if not normalized:
        raise ValueError(f"entry must not be empty: {entry!r}")
    return normalized


def _is_hidden(name: str) -> bool:
    return name.startswith(".")


def iter_entries(namespace: str | None = None, store_dir: Path | None = None) -> list[str]:
    """Return the ``pass`` entry names under ``namespace``, sorted.

    Recurses into subfolders. Only ``*.gpg`` files are considered; dotfiles and
    dot-directories (``.git``, ``.gpg-id``, ``.extensions``) are skipped. Raises
    :class:`~passenv.errors.NamespaceNotFoundError` when the namespace directory
    does not exist.
    """
    root = resolve_store_dir() if store_dir is None else Path(store_dir)
    prefix = normalize_namespace(namespace)
    base = root / prefix if prefix else root
    if not base.is_dir():
        raise NamespaceNotFoundError(prefix, str(root))

    entries: list[str] = []
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = sorted(name for name in dirnames if not _is_hidden(name))
        rel_dir = Path(dirpath).relative_to(root)
        for filename in sorted(filenames):
            if _is_hidden(filename) or not filename.endswith(".gpg"):
                continue
            rel = rel_dir / filename[: -len(".gpg")]
            entries.append(rel.as_posix())
    return sorted(entries)
