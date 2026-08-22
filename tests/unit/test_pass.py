from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from passenv import _pass
from passenv.errors import PassDecryptError, PassNotFoundError


class _Result:
    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


@pytest.fixture
def spy_run(monkeypatch: pytest.MonkeyPatch):
    calls: list[dict] = []
    result = _Result(stdout="s3cret\n")

    def _run(cmd, **kwargs):
        calls.append({"cmd": cmd, **kwargs})
        return result

    monkeypatch.setattr(subprocess, "run", _run)
    return type("SpyRun", (), {"calls": calls, "result": result})()


def test_invokes_pass_show(spy_run) -> None:
    assert _pass.run_pass_show("project_a/api_token") == "s3cret\n"
    assert spy_run.calls[0]["cmd"] == ["pass", "show", "--", "project_a/api_token"]
    assert spy_run.calls[0]["capture_output"] is True
    assert spy_run.calls[0]["text"] is True


def test_inherits_environment_when_no_store_dir(spy_run) -> None:
    _pass.run_pass_show("project_a/api_token")
    assert spy_run.calls[0]["env"] is None


def test_sets_password_store_dir_and_keeps_the_rest(
    spy_run, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("PASSENV_MARKER", "kept")
    _pass.run_pass_show("project_a/api_token", store_dir=tmp_path)
    env = spy_run.calls[0]["env"]
    assert env["PASSWORD_STORE_DIR"] == str(tmp_path)
    assert env["PASSENV_MARKER"] == "kept"
    assert os.environ.get("PASSWORD_STORE_DIR") is None


def test_missing_binary_raises_pass_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    def _run(cmd, **kwargs):
        raise FileNotFoundError(2, "No such file or directory", "pass")

    monkeypatch.setattr(subprocess, "run", _run)
    with pytest.raises(PassNotFoundError, match="PATH"):
        _pass.run_pass_show("project_a/api_token")


def test_nonzero_exit_raises_decrypt_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda cmd, **kw: _Result(returncode=2, stderr="gpg: decryption failed\n"),
    )
    with pytest.raises(PassDecryptError) as excinfo:
        _pass.run_pass_show("project_a/api_token")
    error = excinfo.value
    assert error.entry == "project_a/api_token"
    assert error.returncode == 2
    assert error.stderr == "gpg: decryption failed\n"
    assert "decryption failed" in str(error)


def test_returns_stdout_verbatim(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(subprocess, "run", lambda cmd, **kw: _Result(stdout="  padded \n\nmore\n"))
    assert _pass.run_pass_show("x") == "  padded \n\nmore\n"


def test_entry_names_cannot_become_pass_flags(spy_run) -> None:
    """`--` keeps a leading-dash entry from being parsed as an option (e.g. `-c`/--clip)."""
    _pass.run_pass_show("-c")
    cmd = spy_run.calls[0]["cmd"]
    assert cmd == ["pass", "show", "--", "-c"]
    assert cmd.index("--") < cmd.index("-c")
