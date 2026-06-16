"""Tests for cc_forge.config helpers."""

from __future__ import annotations

import pytest

from cc_forge.config import ForgeConfig, _resolve_int


def test_resolve_int_parses_valid(monkeypatch):
    monkeypatch.setenv("FORGE_AGENT_PIDS_LIMIT", "1024")
    assert _resolve_int("FORGE_AGENT_PIDS_LIMIT") == 1024


def test_resolve_int_reports_bad_value(monkeypatch):
    monkeypatch.setenv("FORGE_AGENT_PIDS_LIMIT", "lots")
    with pytest.raises(ValueError, match="FORGE_AGENT_PIDS_LIMIT must be an integer"):
        _resolve_int("FORGE_AGENT_PIDS_LIMIT")


def test_resolve_github_repo_explicit_wins():
    cfg = ForgeConfig(github_repo="owner/explicit", github_owner="someone")
    assert cfg.resolve_github_repo("myrepo") == "owner/explicit"


def test_resolve_github_repo_owner_plus_basename():
    cfg = ForgeConfig(github_owner="amc-corey-cox", github_repo="")
    assert cfg.resolve_github_repo("cc_forge") == "amc-corey-cox/cc_forge"


def test_resolve_github_repo_rejects_bare_repo():
    cfg = ForgeConfig(github_repo="not-owner-slash-repo")
    with pytest.raises(ValueError, match="owner/repo"):
        cfg.resolve_github_repo("myrepo")


def test_resolve_github_repo_rejects_too_many_segments():
    cfg = ForgeConfig(github_repo="owner/repo/extra")
    with pytest.raises(ValueError, match="owner/repo"):
        cfg.resolve_github_repo("myrepo")


def test_resolve_github_repo_rejects_empty_segment():
    cfg = ForgeConfig(github_repo="/repo")
    with pytest.raises(ValueError, match="owner/repo"):
        cfg.resolve_github_repo("myrepo")


def test_resolve_github_repo_unset_errors():
    cfg = ForgeConfig(github_repo="", github_owner="")
    with pytest.raises(ValueError, match="FORGE_GITHUB_REPO or FORGE_GITHUB_OWNER"):
        cfg.resolve_github_repo("myrepo")
