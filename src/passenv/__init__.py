"""Load environment variables from the `pass` password store.

`passenv` is to `pass` what `python-dotenv` is to `.env` files: one password-store
entry becomes one environment variable, and folders act as namespaces.

    >>> from passenv import load_passenv
    >>> load_passenv("project_a")  # doctest: +SKIP
    True
"""

from __future__ import annotations

from ._core import get_key, load_passenv, logger, passenv_values
from .errors import (
    KeyCollisionError,
    NamespaceNotFoundError,
    PassDecryptError,
    PassEnvError,
    PassNotFoundError,
)

__version__ = "0.1.1"

__all__ = [
    "KeyCollisionError",
    "NamespaceNotFoundError",
    "PassDecryptError",
    "PassEnvError",
    "PassNotFoundError",
    "__version__",
    "get_key",
    "load_passenv",
    "logger",
    "passenv_values",
]
