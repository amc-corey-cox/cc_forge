"""Tests for cc_forge.prune module."""

from __future__ import annotations

import re
from datetime import datetime, timezone

import pytest

from cc_forge.config import ForgeConfig
from cc_forge.prune import plan_prune, prune_branches, render_summary

NOW = datetime(2026, 6, 30, tzinfo=timezone.utc)
CUTOFF = datetime(2026, 6, 23, tzinfo=timezone.utc)  # NOW - 7 days


def _branch(name: str, timestamp: str | None = None) -> dict:
    commit = {"timestamp": timestamp} if timestamp else {}
    return {"name": name, "commit": commit}


@pytest.fixture()
def config() -> ForgeConfig:
    return ForgeConfig(
        forgejo_url="http://localhost:3000",
        forgejo_token="test-token",
        compose_file="/dev/null",
    )


# --- plan_prune (pure classification) ---------------------------------------

def test_keeps_default_branch() -> None:
    plans = plan_prune([_branch("main", "2020-01-01T00:00:00Z")], set(), "main", CUTOFF)
    assert plans[0].delete is False
    assert plans[0].reason == "default branch"


def test_keeps_open_pr_branch_even_if_stale() -> None:
    plans = plan_prune(
        [_branch("feature/x", "2020-01-01T00:00:00Z")], {"feature/x"}, "main", CUTOFF
    )
    assert plans[0].delete is False
    assert plans[0].reason == "open PR"


def test_keeps_recently_active_branch() -> None:
    plans = plan_prune(
        [_branch("feature/fresh", "2026-06-28T12:00:00Z")], set(), "main", CUTOFF
    )
    assert plans[0].delete is False
    assert "active since" in plans[0].reason


def test_deletes_stale_branch_without_pr() -> None:
    plans = plan_prune(
        [_branch("test/hello", "2026-06-01T00:00:00Z")], set(), "main", CUTOFF
    )
    assert plans[0].delete is True
    assert plans[0].reason == "no open PR, stale"


def test_deletes_branch_with_missing_timestamp() -> None:
    plans = plan_prune([_branch("test/hello")], set(), "main", CUTOFF)
    assert plans[0].delete is True


# --- prune_branches (client integration, mocked) ----------------------------

def _register_common(httpx_mock) -> None:
    httpx_mock.add_response(
        url="http://localhost:3000/api/v1/user", json={"login": "forge-admin"}
    )
    httpx_mock.add_response(
        url=re.compile(r".*/repos/forge-admin/myrepo$"),
        json={"default_branch": "main"},
    )
    httpx_mock.add_response(
        url=re.compile(r".*/repos/forge-admin/myrepo/branches.*"),
        json=[
            _branch("main", "2026-06-29T00:00:00Z"),
            _branch("feature/open", "2026-05-01T00:00:00Z"),
            _branch("test/hello", "2026-05-01T00:00:00Z"),
        ],
    )
    httpx_mock.add_response(
        url=re.compile(r".*/repos/forge-admin/myrepo/pulls.*"),
        json=[{"head": {"ref": "feature/open"}}],
    )


def test_dry_run_deletes_nothing(config: ForgeConfig, httpx_mock) -> None:
    _register_common(httpx_mock)
    result = prune_branches(config, "myrepo", days=7, apply=False, now=NOW)

    assert result.applied is False
    assert result.deleted == []
    doomed = [p.name for p in result.plans if p.delete]
    assert doomed == ["test/hello"]
    # no DELETE request was issued
    assert not any(r.method == "DELETE" for r in httpx_mock.get_requests())


def test_apply_deletes_only_stale(config: ForgeConfig, httpx_mock) -> None:
    _register_common(httpx_mock)
    httpx_mock.add_response(
        url=re.compile(r".*/repos/forge-admin/myrepo/branches/test/hello$"),
        method="DELETE",
        status_code=204,
    )
    result = prune_branches(config, "myrepo", days=7, apply=True, now=NOW)

    assert result.applied is True
    assert result.deleted == ["test/hello"]
    deletes = [r for r in httpx_mock.get_requests() if r.method == "DELETE"]
    assert len(deletes) == 1
    assert deletes[0].url.path.endswith("/branches/test/hello")


def test_render_summary_dry_run_hints_apply(config: ForgeConfig, httpx_mock) -> None:
    _register_common(httpx_mock)
    result = prune_branches(config, "myrepo", days=7, apply=False, now=NOW)
    out = render_summary(result)
    assert "Would delete (1)" in out
    assert "--apply" in out
