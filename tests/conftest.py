"""Shared fixtures for the passenv test suite."""

from __future__ import annotations

import os
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _isolated_environ(monkeypatch: pytest.MonkeyPatch):
    """Keep the developer's real store out of every test and undo env writes."""
    monkeypatch.delenv("PASSWORD_STORE_DIR", raising=False)
    snapshot = dict(os.environ)
    yield
    os.environ.clear()
    os.environ.update(snapshot)


@pytest.fixture
def store(tmp_path: Path) -> Path:
    """An empty fake password store directory."""
    root = tmp_path / "store"
    root.mkdir()
    (root / ".gpg-id").write_text("fake@example.com\n")
    return root


@pytest.fixture
def make_entry(store: Path):
    """Create a fake ``<entry>.gpg`` file inside the fake store."""

    def _make(entry: str, contents: str = "") -> Path:
        path = store / f"{entry}.gpg"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents)
        return path

    return _make


@pytest.fixture
def fake_pass(monkeypatch: pytest.MonkeyPatch):
    """Replace ``_pass.run_pass_show`` with a lookup into a dict of raw contents."""
    from passenv import _core

    contents: dict[str, str] = {}
    calls: list[str] = []

    def _run_pass_show(entry: str, store_dir: os.PathLike[str] | None = None) -> str:
        calls.append(entry)
        return contents[entry]

    monkeypatch.setattr(_core._pass, "run_pass_show", _run_pass_show)
    return type("FakePass", (), {"contents": contents, "calls": calls})()
