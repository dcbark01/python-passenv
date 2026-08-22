from __future__ import annotations

import logging
import os
from pathlib import Path

import pytest

from passenv import get_key, load_passenv, passenv_values
from passenv.errors import KeyCollisionError, NamespaceNotFoundError


@pytest.fixture
def populated(store: Path, make_entry, fake_pass):
    """A store with a handful of entries whose contents are served by ``fake_pass``."""
    entries = {
        "project_a/api_token": "t0ken-aaa\n",
        "project_a/db/dsn": "dsn-bbb\n",
        "shared/webhook_url": "url-ccc\n",
        "top_level": "root-value\n",
    }
    for entry, contents in entries.items():
        make_entry(entry)
        fake_pass.contents[entry] = contents
    return fake_pass


class TestPassenvValues:
    def test_root_namespace(self, store: Path, populated) -> None:
        assert passenv_values(store_dir=store) == {
            "API_TOKEN": "t0ken-aaa",
            "DSN": "dsn-bbb",
            "WEBHOOK_URL": "url-ccc",
            "TOP_LEVEL": "root-value",
        }

    def test_single_namespace_scopes_keys(self, store: Path, populated) -> None:
        assert passenv_values("project_a", store_dir=store) == {
            "API_TOKEN": "t0ken-aaa",
            "DSN": "dsn-bbb",
        }

    def test_uses_leaf_name_only(self, store: Path, populated) -> None:
        assert "DSN" in passenv_values("project_a", store_dir=store)
        assert "DB_DSN" not in passenv_values("project_a", store_dir=store)

    def test_key_transform_is_applied_to_the_leaf(self, store: Path, populated) -> None:
        values = passenv_values(
            "project_a", key_transform=lambda leaf: f"pfx_{leaf}", store_dir=store
        )
        assert set(values) == {"pfx_api_token", "pfx_dsn"}

    def test_first_line_only_by_default(self, store: Path, make_entry, fake_pass) -> None:
        make_entry("ns/key")
        fake_pass.contents["ns/key"] = "first\nsecond\nthird\n"
        assert passenv_values("ns", store_dir=store) == {"KEY": "first"}

    def test_multiline_keeps_content_minus_one_trailing_newline(
        self, store: Path, make_entry, fake_pass
    ) -> None:
        make_entry("ns/key")
        fake_pass.contents["ns/key"] = "-----BEGIN-----\nbody\n-----END-----\n"
        assert passenv_values("ns", multiline=True, store_dir=store) == {
            "KEY": "-----BEGIN-----\nbody\n-----END-----"
        }

    def test_multiline_strips_only_one_trailing_newline(
        self, store: Path, make_entry, fake_pass
    ) -> None:
        make_entry("ns/key")
        fake_pass.contents["ns/key"] = "body\n\n"
        assert passenv_values("ns", multiline=True, store_dir=store) == {"KEY": "body\n"}

    def test_values_are_never_stripped(self, store: Path, make_entry, fake_pass) -> None:
        make_entry("ns/key")
        fake_pass.contents["ns/key"] = "  spaced value \n"
        assert passenv_values("ns", store_dir=store) == {"KEY": "  spaced value "}

    def test_later_namespaces_override_earlier(self, store: Path, make_entry, fake_pass) -> None:
        make_entry("a/token")
        make_entry("b/token")
        fake_pass.contents.update({"a/token": "from-a\n", "b/token": "from-b\n"})
        assert passenv_values(["a", "b"], store_dir=store) == {"TOKEN": "from-b"}
        assert passenv_values(["b", "a"], store_dir=store) == {"TOKEN": "from-a"}

    def test_namespaces_are_merged_not_replaced(self, store: Path, make_entry, fake_pass) -> None:
        make_entry("a/only_a")
        make_entry("b/only_b")
        fake_pass.contents.update({"a/only_a": "1\n", "b/only_b": "2\n"})
        assert passenv_values(["a", "b"], store_dir=store) == {"ONLY_A": "1", "ONLY_B": "2"}

    def test_collision_within_a_namespace_raises(self, store: Path, make_entry, fake_pass) -> None:
        make_entry("ns/token")
        make_entry("ns/sub/token")
        with pytest.raises(KeyCollisionError) as excinfo:
            passenv_values("ns", store_dir=store)
        assert excinfo.value.key == "TOKEN"
        assert set(excinfo.value.entries) == {"ns/token", "ns/sub/token"}

    def test_collision_is_detected_before_decrypting(
        self, store: Path, make_entry, fake_pass
    ) -> None:
        make_entry("ns/token")
        make_entry("ns/sub/token")
        with pytest.raises(KeyCollisionError):
            passenv_values("ns", store_dir=store)
        assert fake_pass.calls == []

    def test_key_transform_induced_collisions_are_caught(
        self, store: Path, make_entry, fake_pass
    ) -> None:
        make_entry("ns/api-token")
        make_entry("ns/api_token")
        with pytest.raises(KeyCollisionError) as excinfo:
            passenv_values(
                "ns", key_transform=lambda leaf: leaf.replace("-", "_").upper(), store_dir=store
            )
        assert excinfo.value.key == "API_TOKEN"

    def test_missing_namespace_returns_empty_by_default(self, store: Path) -> None:
        assert passenv_values("absent", store_dir=store) == {}

    def test_missing_namespace_raises_when_required(self, store: Path) -> None:
        with pytest.raises(NamespaceNotFoundError):
            passenv_values("absent", required=True, store_dir=store)

    def test_missing_namespace_is_skipped_among_present_ones(
        self, store: Path, make_entry, fake_pass
    ) -> None:
        make_entry("a/token")
        fake_pass.contents["a/token"] = "v\n"
        assert passenv_values(["a", "absent"], store_dir=store) == {"TOKEN": "v"}

    def test_does_not_touch_the_environment(self, store: Path, populated) -> None:
        passenv_values("project_a", store_dir=store)
        assert "API_TOKEN" not in os.environ

    def test_store_dir_environment_variable_is_honoured(
        self, monkeypatch: pytest.MonkeyPatch, store: Path, populated
    ) -> None:
        monkeypatch.setenv("PASSWORD_STORE_DIR", str(store))
        assert set(passenv_values("project_a")) == {"API_TOKEN", "DSN"}


class TestLoadPassenv:
    def test_sets_variables_and_returns_true(
        self, store: Path, populated, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("API_TOKEN", raising=False)
        assert load_passenv("project_a", store_dir=store) is True
        assert os.environ["API_TOKEN"] == "t0ken-aaa"

    def test_returns_false_when_nothing_loaded(self, store: Path) -> None:
        assert load_passenv("absent", store_dir=store) is False

    def test_empty_namespace_returns_false(self, store: Path) -> None:
        (store / "empty").mkdir()
        assert load_passenv("empty", store_dir=store) is False

    def test_does_not_override_existing_variables_by_default(
        self, store: Path, populated, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("API_TOKEN", "pre-existing")
        assert load_passenv("project_a", store_dir=store) is True
        assert os.environ["API_TOKEN"] == "pre-existing"

    def test_override_replaces_existing_variables(
        self, store: Path, populated, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("API_TOKEN", "pre-existing")
        load_passenv("project_a", override=True, store_dir=store)
        assert os.environ["API_TOKEN"] == "t0ken-aaa"

    def test_namespace_layering_is_resolved_before_the_write(
        self, store: Path, make_entry, fake_pass, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        make_entry("a/token")
        make_entry("b/token")
        fake_pass.contents.update({"a/token": "from-a\n", "b/token": "from-b\n"})
        monkeypatch.delenv("TOKEN", raising=False)
        load_passenv(["a", "b"], store_dir=store)
        assert os.environ["TOKEN"] == "from-b"

    def test_required_propagates(self, store: Path) -> None:
        with pytest.raises(NamespaceNotFoundError):
            load_passenv("absent", required=True, store_dir=store)

    def test_logs_keys_but_never_values(
        self,
        store: Path,
        populated,
        caplog: pytest.LogCaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.delenv("API_TOKEN", raising=False)
        with caplog.at_level(logging.INFO, logger="passenv"):
            load_passenv("project_a", verbose=True, store_dir=store)
        text = caplog.text
        assert "API_TOKEN" in text
        assert "t0ken-aaa" not in text
        assert "dsn-bbb" not in text

    def test_quiet_by_default(
        self, store: Path, populated, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.WARNING, logger="passenv"):
            load_passenv("project_a", store_dir=store)
        assert caplog.text == ""


class TestGetKey:
    def test_returns_the_first_line(self, store: Path, populated) -> None:
        assert get_key("project_a/api_token", store_dir=store) == "t0ken-aaa"

    def test_multiline(self, store: Path, make_entry, fake_pass) -> None:
        make_entry("ns/key")
        fake_pass.contents["ns/key"] = "a\nb\n"
        assert get_key("ns/key", multiline=True, store_dir=store) == "a\nb"

    def test_returns_none_for_a_missing_entry(self, store: Path, populated) -> None:
        assert get_key("project_a/absent", store_dir=store) is None

    def test_does_not_shell_out_for_a_missing_entry(self, store: Path, populated) -> None:
        get_key("project_a/absent", store_dir=store)
        assert populated.calls == []

    def test_refuses_to_read_outside_the_store(self, store: Path, populated) -> None:
        outside = store.parent / "outside"
        outside.mkdir()
        (outside / "loot.gpg").write_text("")
        with pytest.raises(ValueError, match=r"\.\."):
            get_key("../outside/loot", store_dir=store)
        assert populated.calls == []

    def test_refuses_an_empty_entry_name(self, store: Path, populated) -> None:
        with pytest.raises(ValueError, match="empty"):
            get_key("", store_dir=store)
        assert populated.calls == []

    def test_nested_entry(self, store: Path, populated) -> None:
        assert get_key("project_a/db/dsn", store_dir=store) == "dsn-bbb"
