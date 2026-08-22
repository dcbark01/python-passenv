from __future__ import annotations

import passenv
from passenv.errors import (
    KeyCollisionError,
    NamespaceNotFoundError,
    PassDecryptError,
    PassEnvError,
    PassNotFoundError,
)


def test_every_error_is_exported() -> None:
    for name in (
        "PassEnvError",
        "PassNotFoundError",
        "PassDecryptError",
        "NamespaceNotFoundError",
        "KeyCollisionError",
    ):
        assert name in passenv.__all__
        assert getattr(passenv, name) is not None


def test_public_api_is_exported() -> None:
    assert {"load_passenv", "passenv_values", "get_key"} <= set(passenv.__all__)


def test_hierarchy() -> None:
    for cls in (PassNotFoundError, PassDecryptError, NamespaceNotFoundError, KeyCollisionError):
        assert issubclass(cls, PassEnvError)
    assert issubclass(PassEnvError, Exception)


def test_decrypt_error_attributes() -> None:
    error = PassDecryptError("project_a/api_token", 2, "boom\n")
    assert (error.entry, error.returncode, error.stderr) == ("project_a/api_token", 2, "boom\n")


def test_decrypt_error_without_stderr() -> None:
    assert "exit code 1" in str(PassDecryptError("e", 1, ""))


def test_collision_error_attributes() -> None:
    error = KeyCollisionError("TOKEN", ["a/token", "b/token"])
    assert error.key == "TOKEN"
    assert error.entries == ("a/token", "b/token")
    assert "a/token" in str(error) and "b/token" in str(error)


def test_namespace_error_attributes() -> None:
    error = NamespaceNotFoundError("project_a", "/tmp/store")
    assert (error.namespace, error.store_dir) == ("project_a", "/tmp/store")
