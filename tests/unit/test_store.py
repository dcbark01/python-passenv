from __future__ import annotations

from pathlib import Path

import pytest

from passenv._store import (
    DEFAULT_STORE_DIR,
    iter_entries,
    normalize_entry,
    normalize_namespace,
    resolve_store_dir,
)
from passenv.errors import NamespaceNotFoundError


class TestResolveStoreDir:
    def test_explicit_argument_wins(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.setenv("PASSWORD_STORE_DIR", str(tmp_path / "from-env"))
        assert resolve_store_dir(tmp_path / "explicit") == tmp_path / "explicit"

    def test_environment_variable_is_second(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("PASSWORD_STORE_DIR", str(tmp_path / "from-env"))
        assert resolve_store_dir() == tmp_path / "from-env"

    def test_falls_back_to_home(self) -> None:
        assert resolve_store_dir() == Path(DEFAULT_STORE_DIR).expanduser()

    def test_empty_environment_variable_falls_back(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PASSWORD_STORE_DIR", "")
        assert resolve_store_dir() == Path(DEFAULT_STORE_DIR).expanduser()

    def test_expands_user(self) -> None:
        assert resolve_store_dir("~/somewhere") == Path.home() / "somewhere"


class TestNormalizeNamespace:
    @pytest.mark.parametrize(
        ("given", "expected"),
        [
            (None, ""),
            ("", ""),
            ("project_a", "project_a"),
            ("/project_a/", "project_a"),
            ("project_a//sub", "project_a/sub"),
            ("./project_a", "project_a"),
        ],
    )
    def test_normalization(self, given: str | None, expected: str) -> None:
        assert normalize_namespace(given) == expected

    def test_rejects_parent_traversal(self) -> None:
        with pytest.raises(ValueError, match=r"\.\."):
            normalize_namespace("../../etc")


class TestIterEntries:
    def test_root_namespace_lists_everything(self, store: Path, make_entry) -> None:
        make_entry("top")
        make_entry("project_a/api_token")
        make_entry("shared/webhook_url")
        assert iter_entries(None, store) == ["project_a/api_token", "shared/webhook_url", "top"]

    def test_namespace_scopes_the_listing(self, store: Path, make_entry) -> None:
        make_entry("top")
        make_entry("project_a/api_token")
        make_entry("project_a/db/dsn")
        assert iter_entries("project_a", store) == ["project_a/api_token", "project_a/db/dsn"]

    def test_recurses_into_subfolders(self, store: Path, make_entry) -> None:
        make_entry("project_a/a/b/c/deep")
        assert iter_entries("project_a", store) == ["project_a/a/b/c/deep"]

    def test_ignores_non_gpg_files(self, store: Path, make_entry) -> None:
        make_entry("project_a/real")
        (store / "project_a" / "notes.txt").write_text("hello")
        assert iter_entries("project_a", store) == ["project_a/real"]

    def test_skips_dotfiles_and_dot_directories(self, store: Path, make_entry) -> None:
        make_entry("project_a/real")
        make_entry(".hidden")
        git_dir = store / ".git" / "objects"
        git_dir.mkdir(parents=True)
        (git_dir / "packed.gpg").write_text("")
        (store / ".gpg-id").write_text("id")
        assert iter_entries(None, store) == ["project_a/real"]

    def test_missing_namespace_raises(self, store: Path) -> None:
        with pytest.raises(NamespaceNotFoundError) as excinfo:
            iter_entries("nope", store)
        assert excinfo.value.namespace == "nope"
        assert excinfo.value.store_dir == str(store)

    def test_missing_store_raises(self, tmp_path: Path) -> None:
        with pytest.raises(NamespaceNotFoundError):
            iter_entries(None, tmp_path / "absent")

    def test_empty_namespace_is_not_an_error(self, store: Path) -> None:
        (store / "empty").mkdir()
        assert iter_entries("empty", store) == []

    def test_uses_resolved_store_when_omitted(
        self, monkeypatch: pytest.MonkeyPatch, store: Path, make_entry
    ) -> None:
        make_entry("project_a/api_token")
        monkeypatch.setenv("PASSWORD_STORE_DIR", str(store))
        assert iter_entries("project_a") == ["project_a/api_token"]


class TestNormalizeEntry:
    @pytest.mark.parametrize(
        ("given", "expected"),
        [
            ("project_a/api_token", "project_a/api_token"),
            ("/project_a/api_token", "project_a/api_token"),
            ("./project_a//api_token", "project_a/api_token"),
        ],
    )
    def test_normalization(self, given: str, expected: str) -> None:
        assert normalize_entry(given) == expected

    @pytest.mark.parametrize("given", ["../outside", "project_a/../../outside", ".."])
    def test_rejects_parent_traversal(self, given: str) -> None:
        with pytest.raises(ValueError, match=r"\.\."):
            normalize_entry(given)

    @pytest.mark.parametrize("given", ["", "/", "."])
    def test_rejects_empty(self, given: str) -> None:
        with pytest.raises(ValueError, match="empty"):
            normalize_entry(given)
