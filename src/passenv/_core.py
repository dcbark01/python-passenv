"""Implementation of the public :mod:`passenv` API."""

from __future__ import annotations

import logging
import os
from collections.abc import Callable, Sequence

from . import _pass
from ._store import iter_entries, normalize_entry, resolve_store_dir
from .errors import KeyCollisionError, NamespaceNotFoundError

__all__ = ["get_key", "load_passenv", "logger", "passenv_values"]

logger = logging.getLogger("passenv")

_verbose_handler_installed = False


def _enable_verbose_logging() -> None:
    """Make ``logger`` emit INFO records even when the app configured no logging."""
    global _verbose_handler_installed
    if logger.getEffectiveLevel() > logging.INFO:
        logger.setLevel(logging.INFO)
    if not _verbose_handler_installed and not logger.hasHandlers():
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(name)s: %(message)s"))
        logger.addHandler(handler)
        _verbose_handler_installed = True


def _as_namespaces(namespace: str | Sequence[str] | None) -> list[str | None]:
    if namespace is None:
        return [None]
    if isinstance(namespace, str):
        return [namespace]
    return list(namespace)


def _extract_value(raw: str, multiline: bool) -> str:
    if not multiline:
        return raw.split("\n", 1)[0]
    return raw[:-1] if raw.endswith("\n") else raw


def passenv_values(
    namespace: str | Sequence[str] | None = None,
    *,
    multiline: bool = False,
    key_transform: Callable[[str], str] = str.upper,
    required: bool = False,
    store_dir: str | os.PathLike[str] | None = None,
) -> dict[str, str]:
    """Return the variables defined by ``namespace`` without touching ``os.environ``.

    ``namespace`` is a folder in the password store (or a sequence of them, where
    later namespaces override earlier ones); ``None`` means the store root. Each
    entry contributes one variable, named by applying ``key_transform`` to the
    entry's leaf name.
    """
    store = resolve_store_dir(store_dir)
    values: dict[str, str] = {}

    for ns in _as_namespaces(namespace):
        try:
            entries = iter_entries(ns, store)
        except NamespaceNotFoundError:
            if required:
                raise
            logger.info("namespace %r not found in %s, skipping", ns or "", str(store))
            continue

        keys: dict[str, str] = {}
        for entry in entries:
            key = key_transform(entry.rsplit("/", 1)[-1])
            if key in keys:
                raise KeyCollisionError(key, [keys[key], entry])
            keys[key] = entry

        for key, entry in keys.items():
            values[key] = _extract_value(
                _pass.run_pass_show(entry, store_dir=store), multiline=multiline
            )
            logger.info("read %s from entry %s", key, entry)

    return values


def load_passenv(
    namespace: str | Sequence[str] | None = None,
    *,
    override: bool = False,
    multiline: bool = False,
    key_transform: Callable[[str], str] = str.upper,
    required: bool = False,
    verbose: bool = False,
    store_dir: str | os.PathLike[str] | None = None,
) -> bool:
    """Load ``namespace`` from the password store into ``os.environ``.

    Returns ``True`` if at least one entry was read. Existing environment
    variables are left alone unless ``override=True``.
    """
    if verbose:
        _enable_verbose_logging()

    values = passenv_values(
        namespace,
        multiline=multiline,
        key_transform=key_transform,
        required=required,
        store_dir=store_dir,
    )

    for key, value in values.items():
        if not override and key in os.environ:
            logger.info("%s already set in the environment, not overridden", key)
            continue
        os.environ[key] = value
        logger.info("set %s", key)

    return bool(values)


def get_key(
    entry: str,
    *,
    multiline: bool = False,
    store_dir: str | os.PathLike[str] | None = None,
) -> str | None:
    """Return the value of a single ``pass`` entry, or ``None`` if it does not exist.

    Raises :class:`ValueError` for an empty entry name or one containing ``..`` —
    an entry is always resolved relative to the store, never outside it.
    """
    store = resolve_store_dir(store_dir)
    name = normalize_entry(entry)
    if not (store / f"{name}.gpg").is_file():
        logger.info("entry %s not found in %s", name, str(store))
        return None
    return _extract_value(_pass.run_pass_show(name, store_dir=store), multiline=multiline)
