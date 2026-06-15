"""Tests for cc_forge.promote orchestration."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import click
import pytest

from cc_forge import promote as promote_mod
from cc_forge.config import ForgeConfig

PR = {
    "title": "Add feature",
    "body": "Body.",
    "head": {"ref": "agent/feature"},
    "base": {"ref": "main"},
}


def _config(**kw) -> ForgeConfig:
    defaults = dict(
        forgejo_url="http://localhost:3000",
        forgejo_token="t",
        github_owner="me",
        github_repo="",
        github_token="",
    )
    defaults.update(kw)
    return ForgeConfig(**defaults)


def _fake_forgejo(pr: dict) -> MagicMock:
    client = MagicMock()
    client.__enter__.return_value = client
    client.__exit__.return_value = False
    client.get_current_user.return_value = "admin"
    client.get_pull_request.return_value = pr
    return client


def _wire(monkeypatch, *, remote_url="https://github.com/me/cc_forge.git",
          has_forgejo=True, gh_rc=0, gh_stdout="https://github.com/me/cc_forge/pull/3\n",
          gh_stderr="", captured=None):
    captured = captured if captured is not None else {}
    monkeypatch.setattr(promote_mod, "get_repo_root", lambda p: Path("/repo"))
    monkeypatch.setattr(promote_mod, "get_repo_name", lambda p: "cc_forge")
    monkeypatch.setattr(promote_mod, "ForgejoClient", lambda c: _fake_forgejo(PR))
    monkeypatch.setattr(promote_mod, "has_remote",
                        lambda root, name: has_forgejo if name == "forgejo" else True)
    monkeypatch.setattr(promote_mod, "fetch_remote", lambda root, remote: None)
    monkeypatch.setattr(promote_mod, "create_branch_from_ref",
                        lambda root, b, s: captured.update(branch=b, start=s))
    monkeypatch.setattr(promote_mod, "get_remote_url", lambda root, name: remote_url)
    monkeypatch.setattr(promote_mod, "push_to_remote",
                        lambda root, remote, branch: captured.update(push_remote=remote, push_branch=branch))

    def fake_run(args, **kwargs):
        captured["gh_args"] = args
        return MagicMock(returncode=gh_rc, stdout=gh_stdout, stderr=gh_stderr)

    monkeypatch.setattr(promote_mod.subprocess, "run", fake_run)
    return captured


def test_promote_happy_path(monkeypatch):
    captured = _wire(monkeypatch)
    url = promote_mod.promote_pull_request(_config(), 7, repo_path="/repo")

    assert url == "https://github.com/me/cc_forge/pull/3"
    assert captured["branch"] == "agent/feature"
    assert captured["start"] == "forgejo/agent/feature"
    assert captured["push_remote"] == "origin"
    assert captured["push_branch"] == "agent/feature"

    args = captured["gh_args"]
    assert args[:3] == ["gh", "pr", "create"]
    assert "me/cc_forge" in args  # -R target
    assert args[args.index("--head") + 1] == "agent/feature"
    assert args[args.index("--base") + 1] == "main"
    assert args[args.index("--title") + 1] == "Add feature"


def test_promote_warns_on_remote_mismatch(monkeypatch, capsys):
    _wire(monkeypatch, remote_url="https://github.com/other/repo.git")
    promote_mod.promote_pull_request(_config(), 7, repo_path="/repo")
    err = capsys.readouterr().err
    assert "does not match" in err
    assert "me/cc_forge" in err


def test_promote_errors_without_forgejo_remote(monkeypatch):
    _wire(monkeypatch, has_forgejo=False)
    with pytest.raises(click.ClickException, match="forgejo"):
        promote_mod.promote_pull_request(_config(), 7, repo_path="/repo")


def test_promote_errors_when_gh_fails(monkeypatch):
    _wire(monkeypatch, gh_rc=1, gh_stdout="", gh_stderr="boom")
    with pytest.raises(click.ClickException, match="gh pr create failed"):
        promote_mod.promote_pull_request(_config(), 7, repo_path="/repo")
