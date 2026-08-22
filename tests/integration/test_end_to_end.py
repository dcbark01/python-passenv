from __future__ import annotations

import os
from pathlib import Path

import pytest

from passenv import get_key, load_passenv, passenv_values
from passenv.errors import NamespaceNotFoundError

pytestmark = pytest.mark.integration


def test_load_namespace(real_store: Path, pass_env) -> None:
    assert load_passenv("project_a", store_dir=real_store) is True
    assert os.environ["API_TOKEN"] == "integration-token"
    assert os.environ["DSN"] == "integration-db-dsn"
    assert os.environ["TLS_CERT"] == "-----BEGIN KEY-----"
    assert "WEBHOOK_URL" not in os.environ


def test_multiline_round_trip(real_store: Path, pass_env) -> None:
    values = passenv_values("project_a", multiline=True, store_dir=real_store)
    assert values["TLS_CERT"] == "-----BEGIN KEY-----\nline two\n-----END KEY-----"


def test_root_namespace_spans_folders(real_store: Path, pass_env) -> None:
    values = passenv_values(store_dir=real_store)
    assert {"API_TOKEN", "DSN", "TLS_CERT", "WEBHOOK_URL"} <= set(values)


def test_multiple_namespaces(real_store: Path, pass_env) -> None:
    values = passenv_values(["shared", "project_a"], store_dir=real_store)
    assert values["WEBHOOK_URL"] == "https://hooks.example.invalid/integration"
    assert values["API_TOKEN"] == "integration-token"


def test_password_store_dir_environment_variable(
    real_store: Path, pass_env, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PASSWORD_STORE_DIR", str(real_store))
    assert passenv_values("project_a")["API_TOKEN"] == "integration-token"


def test_get_key(real_store: Path, pass_env) -> None:
    assert get_key("project_a/db/dsn", store_dir=real_store) == "integration-db-dsn"
    assert get_key("project_a/does_not_exist", store_dir=real_store) is None


def test_missing_namespace(real_store: Path, pass_env) -> None:
    assert passenv_values("nope", store_dir=real_store) == {}
    with pytest.raises(NamespaceNotFoundError):
        passenv_values("nope", required=True, store_dir=real_store)


def test_override_semantics(real_store: Path, pass_env, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_TOKEN", "already-set")
    load_passenv("project_a", store_dir=real_store)
    assert os.environ["API_TOKEN"] == "already-set"
    load_passenv("project_a", override=True, store_dir=real_store)
    assert os.environ["API_TOKEN"] == "integration-token"
