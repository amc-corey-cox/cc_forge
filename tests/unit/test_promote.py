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
    "html_url": "http://localhost:3000/cc_forge_admin/cc_forge/pulls/7",
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
    client.get_issue.return_value = {"state": "open"}
    client.list_issue_comments.return_value = []  # unmarked → guard passes
    return client


def _wire(monkeypatch, *, remote_url="https://github.com/me/cc_forge.git",
          has_forgejo=True, current_branch="main", is_repo=True, gh_missing=False,
          gh_rc=0, gh_stdout="https://github.com/me/cc_forge/pull/3\n", gh_stderr="",
          captured=None):
    captured = captured if captured is not None else {}
    monkeypatch.setattr(promote_mod, "is_git_repo", lambda p: is_repo)
    monkeypatch.setattr(promote_mod, "get_repo_root", lambda p: Path("/repo"))
    monkeypatch.setattr(promote_mod, "get_repo_name", lambda p: "cc_forge")
    monkeypatch.setattr(promote_mod, "get_current_branch", lambda root: current_branch)
    monkeypatch.setattr(promote_mod, "ForgejoClient", lambda c: _fake_forgejo(PR))
    monkeypatch.setattr(promote_mod, "has_remote",
                        lambda root, name: has_forgejo if name == "forgejo" else True)
    monkeypatch.setattr(promote_mod, "fetch_remote", lambda root, remote: None)
    monkeypatch.setattr(promote_mod, "create_branch_from_ref",
                        lambda root, b, s: captured.update(branch=b, start=s))
    monkeypatch.setattr(promote_mod, "get_remote_url", lambda root, name: remote_url)

    def fake_push(root, remote, branch, set_upstream=True):
        captured.update(push_remote=remote, push_branch=branch, push_set_upstream=set_upstream)

    monkeypatch.setattr(promote_mod, "push_to_remote", fake_push)

    def fake_run(args, **kwargs):
        if gh_missing:
            raise FileNotFoundError("gh")
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
    assert captured["push_set_upstream"] is False

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


def test_promote_warns_on_substring_remote(monkeypatch, capsys):
    # A fork whose URL *contains* the resolved repo as a substring must still warn.
    _wire(monkeypatch, remote_url="https://github.com/me/cc_forge-fork.git")
    promote_mod.promote_pull_request(_config(), 7, repo_path="/repo")
    assert "does not match" in capsys.readouterr().err


def test_promote_errors_without_forgejo_remote(monkeypatch):
    _wire(monkeypatch, has_forgejo=False)
    with pytest.raises(click.ClickException, match="forgejo"):
        promote_mod.promote_pull_request(_config(), 7, repo_path="/repo")


def test_promote_errors_when_gh_fails(monkeypatch):
    _wire(monkeypatch, gh_rc=1, gh_stdout="", gh_stderr="boom")
    with pytest.raises(click.ClickException, match="gh pr create failed"):
        promote_mod.promote_pull_request(_config(), 7, repo_path="/repo")


def test_promote_errors_when_not_git_repo(monkeypatch):
    _wire(monkeypatch, is_repo=False)
    with pytest.raises(click.ClickException, match="not a git repository"):
        promote_mod.promote_pull_request(_config(), 7, repo_path="/repo")


def test_promote_errors_without_github_repo_config(monkeypatch):
    _wire(monkeypatch)
    cfg = _config(github_owner="", github_repo="")
    with pytest.raises(click.ClickException, match="Cannot resolve GitHub repo"):
        promote_mod.promote_pull_request(cfg, 7, repo_path="/repo")


def test_promote_issue_errors_without_github_repo_config(monkeypatch):
    _wire_repo(monkeypatch)
    cfg = _config(github_owner="", github_repo="")
    with pytest.raises(click.ClickException, match="Cannot resolve GitHub repo"):
        promote_mod.promote_issue(cfg, 12, repo_path="/repo")


def test_promote_errors_when_head_checked_out(monkeypatch):
    _wire(monkeypatch, current_branch="agent/feature")
    with pytest.raises(click.ClickException, match="currently checked out"):
        promote_mod.promote_pull_request(_config(), 7, repo_path="/repo")


def test_promote_errors_when_gh_missing(monkeypatch):
    _wire(monkeypatch, gh_missing=True)
    with pytest.raises(click.ClickException, match="gh CLI not found"):
        promote_mod.promote_pull_request(_config(), 7, repo_path="/repo")


def test_promote_git_fetch_failure_becomes_clean_message(monkeypatch):
    from cc_forge.git import GitError

    _wire(monkeypatch)

    def boom(root, remote):
        raise GitError("Could not resolve host")

    monkeypatch.setattr(promote_mod, "fetch_remote", boom)
    with pytest.raises(click.ClickException, match="is Forgejo reachable"):
        promote_mod.promote_pull_request(_config(), 7, repo_path="/repo")


def test_pr_metadata_happy(monkeypatch):
    monkeypatch.setattr(promote_mod, "ForgejoClient", lambda c: _fake_forgejo(PR))
    meta = promote_mod.pr_metadata(_config(), 7, "cc_forge")
    assert meta == {
        "head": "agent/feature", "base": "main", "title": "Add feature", "body": "Body.",
        "url": "http://localhost:3000/cc_forge_admin/cc_forge/pulls/7",
    }


@pytest.mark.parametrize("err", ["ConnectError", "ReadError", "ProtocolError"])
def test_pr_metadata_unreachable(monkeypatch, err):
    import httpx

    def boom(c):
        m = MagicMock()
        m.__enter__.return_value = m
        m.__exit__.return_value = False
        m.get_current_user.side_effect = getattr(httpx, err)("boom")
        return m

    monkeypatch.setattr(promote_mod, "ForgejoClient", boom)
    with pytest.raises(click.ClickException, match="unreachable"):
        promote_mod.pr_metadata(_config(), 7, "cc_forge")


@pytest.mark.parametrize("url,expected", [
    ("https://github.com/me/cc_forge.git", "me/cc_forge"),
    ("https://github.com/me/cc_forge", "me/cc_forge"),
    ("git@github.com:me/cc_forge.git", "me/cc_forge"),
    ("ssh://git@github.com/me/cc_forge.git", "me/cc_forge"),
])
def test_remote_owner_repo(url, expected):
    assert promote_mod._remote_owner_repo(url) == expected


# --- issue promotion + walker ------------------------------------------------

ISSUE = {
    "title": "Bug: thing broken",
    "body": "Steps to reproduce.",
    "html_url": "http://localhost:3000/cc_forge_admin/cc_forge/issues/12",
}
PR_AS_ISSUE = {**ISSUE, "pull_request": {"merged": False}}


def _fake_client(**returns) -> MagicMock:
    client = MagicMock()
    client.__enter__.return_value = client
    client.__exit__.return_value = False
    client.get_current_user.return_value = "admin"
    client.get_issue.return_value = {"state": "open"}
    client.list_issue_comments.return_value = []  # unmarked → guard passes
    for name, value in returns.items():
        getattr(client, name).return_value = value
    return client


def _wire_repo(monkeypatch):
    monkeypatch.setattr(promote_mod, "is_git_repo", lambda p: True)
    monkeypatch.setattr(promote_mod, "get_repo_root", lambda p: Path("/repo"))
    monkeypatch.setattr(promote_mod, "get_repo_name", lambda p: "cc_forge")


def test_issue_metadata_distinguishes_issue_from_pr(monkeypatch):
    monkeypatch.setattr(promote_mod, "ForgejoClient", lambda c: _fake_client(get_issue=ISSUE))
    meta = promote_mod.issue_metadata(_config(), 12, "cc_forge")
    assert meta["is_pr"] is False
    assert meta["title"] == "Bug: thing broken"

    monkeypatch.setattr(promote_mod, "ForgejoClient",
                        lambda c: _fake_client(get_issue=PR_AS_ISSUE))
    assert promote_mod.issue_metadata(_config(), 7, "cc_forge")["is_pr"] is True


def test_promote_issue_creates_gh_issue_with_provenance_and_closes(monkeypatch):
    _wire_repo(monkeypatch)
    fake = _fake_client(get_issue=ISSUE)
    monkeypatch.setattr(promote_mod, "ForgejoClient", lambda c: fake)
    captured = {}

    def fake_run(args, **kw):
        captured["gh_args"] = args
        return MagicMock(returncode=0,
                         stdout="https://github.com/me/cc_forge/issues/5\n", stderr="")

    monkeypatch.setattr(promote_mod.subprocess, "run", fake_run)
    url = promote_mod.promote_issue(_config(), 12, repo_path="/repo")

    assert url == "https://github.com/me/cc_forge/issues/5"
    args = captured["gh_args"]
    assert args[:3] == ["gh", "issue", "create"]
    assert args[args.index("--title") + 1] == "Bug: thing broken"
    body = args[args.index("--body") + 1]
    assert "Promoted from" in body and "#12" in body
    # lock comment (before) + result comment (after), then close
    assert fake.create_issue_comment.call_count == 2
    lock_body = fake.create_issue_comment.call_args_list[0].args[3]
    result_body = fake.create_issue_comment.call_args_list[1].args[3]
    assert "github.com/me/cc_forge" in lock_body           # target repo URL
    assert "https://github.com/me/cc_forge/issues/5" in result_body  # item URL
    fake.close_issue.assert_called_once_with("admin", "cc_forge", 12)


def test_promote_issue_blocked_when_already_marked_and_closed(monkeypatch):
    _wire_repo(monkeypatch)
    marked = [{"body": "<!-- forge-promote -->\nPromoted to GitHub: https://gh/x/issues/9"}]
    monkeypatch.setattr(promote_mod, "ForgejoClient",
                        lambda c: _fake_client(get_issue={**ISSUE, "state": "closed"},
                                               list_issue_comments=marked))
    monkeypatch.setattr(promote_mod.subprocess, "run",
                        lambda *a, **k: pytest.fail("must not create GitHub item"))
    with pytest.raises(click.ClickException, match="already promoted"):
        promote_mod.promote_issue(_config(), 9, repo_path="/repo")


def test_promote_issue_blocked_when_marked_but_open(monkeypatch):
    _wire_repo(monkeypatch)
    marked = [{"body": "<!-- forge-promote -->\nPromoting to https://github.com/me/cc_forge"}]
    monkeypatch.setattr(promote_mod, "ForgejoClient",
                        lambda c: _fake_client(get_issue={**ISSUE, "state": "open"},
                                               list_issue_comments=marked))
    monkeypatch.setattr(promote_mod.subprocess, "run",
                        lambda *a, **k: pytest.fail("must not create GitHub item"))
    with pytest.raises(click.ClickException, match="marked as promoted but still open"):
        promote_mod.promote_issue(_config(), 9, repo_path="/repo")


def test_promote_issue_locks_before_creating(monkeypatch):
    """The marker lock must be posted before the GitHub item is created."""
    _wire_repo(monkeypatch)
    fake = _fake_client(get_issue=ISSUE)
    monkeypatch.setattr(promote_mod, "ForgejoClient", lambda c: fake)
    order = []
    fake.create_issue_comment.side_effect = lambda *a, **k: order.append("lock/result")

    def fake_run(args, **kw):
        order.append("gh")
        return MagicMock(returncode=0, stdout="https://gh/x/issues/5\n", stderr="")

    monkeypatch.setattr(promote_mod.subprocess, "run", fake_run)
    promote_mod.promote_issue(_config(), 12, repo_path="/repo")
    assert order[0] == "lock/result"  # lock posted before gh create
    assert "gh" in order


def test_promote_issue_rejects_a_pr_number(monkeypatch):
    _wire_repo(monkeypatch)
    monkeypatch.setattr(promote_mod, "ForgejoClient",
                        lambda c: _fake_client(get_issue=PR_AS_ISSUE))
    with pytest.raises(click.ClickException, match="pull request"):
        promote_mod.promote_issue(_config(), 7, repo_path="/repo")


def test_promote_by_number_routes_to_issue_or_pr(monkeypatch):
    _wire_repo(monkeypatch)
    calls = {}
    monkeypatch.setattr(promote_mod, "promote_issue",
                        lambda c, n, repo_path=".": calls.setdefault("issue", n))
    monkeypatch.setattr(promote_mod, "promote_pull_request",
                        lambda c, n, repo_path=".", remote="origin": calls.setdefault("pr", n))

    monkeypatch.setattr(promote_mod, "ForgejoClient", lambda c: _fake_client(get_issue=ISSUE))
    promote_mod.promote_by_number(_config(), 12, repo_path="/repo")
    monkeypatch.setattr(promote_mod, "ForgejoClient", lambda c: _fake_client(get_issue=PR_AS_ISSUE))
    promote_mod.promote_by_number(_config(), 7, repo_path="/repo")

    assert calls == {"issue": 12, "pr": 7}


def test_list_promotable_merges_issues_and_prs_sorted(monkeypatch):
    fake = _fake_client(
        list_pull_requests=[{"number": 7, "title": "PR seven"}],
        list_issues=[{"number": 3, "title": "Issue three"}],
    )
    monkeypatch.setattr(promote_mod, "ForgejoClient", lambda c: fake)
    items = promote_mod.list_promotable(_config(), "cc_forge")
    assert [(i["kind"], i["number"]) for i in items] == [("issue", 3), ("pr", 7)]


def test_walk_promotes_only_confirmed_items(monkeypatch):
    _wire_repo(monkeypatch)
    monkeypatch.setattr(promote_mod, "list_promotable", lambda c, rn: [
        {"kind": "issue", "number": 3, "title": "i3"},
        {"kind": "pr", "number": 7, "title": "p7"},
    ])
    done = []
    monkeypatch.setattr(promote_mod, "promote_issue",
                        lambda c, n, repo_path=".": done.append(("issue", n)) or "u-i")
    monkeypatch.setattr(promote_mod, "promote_pull_request",
                        lambda c, n, repo_path=".", remote="origin": done.append(("pr", n)) or "u-p")

    answers = iter([True, False])  # promote issue 3, skip pr 7
    result = promote_mod.walk_promotable(
        _config(), "/repo", "origin", ("issue", "pr"),
        confirm=lambda prompt: next(answers), echo=lambda m: None,
    )
    assert done == [("issue", 3)]
    assert result == [(3, "u-i")]


def test_walk_filters_by_kind(monkeypatch):
    _wire_repo(monkeypatch)
    monkeypatch.setattr(promote_mod, "list_promotable", lambda c, rn: [
        {"kind": "issue", "number": 3, "title": "i3"},
        {"kind": "pr", "number": 7, "title": "p7"},
    ])
    done = []
    monkeypatch.setattr(promote_mod, "promote_pull_request",
                        lambda c, n, repo_path=".", remote="origin": done.append(n))
    monkeypatch.setattr(promote_mod, "promote_issue",
                        lambda c, n, repo_path=".": done.append(("issue", n)))
    promote_mod.walk_promotable(_config(), "/repo", "origin", ("pr",),
                                confirm=lambda p: True, echo=lambda m: None)
    assert done == [7]  # issue 3 was never offered


def test_walk_reports_nothing_to_promote(monkeypatch):
    _wire_repo(monkeypatch)
    monkeypatch.setattr(promote_mod, "list_promotable", lambda c, rn: [])
    msgs = []
    result = promote_mod.walk_promotable(_config(), "/repo", "origin", ("issue", "pr"),
                                         confirm=lambda p: True, echo=msgs.append)
    assert result == []
    assert any("Nothing to promote" in m for m in msgs)


def test_finalize_is_best_effort(monkeypatch, capsys):
    import httpx

    def boom(c):
        m = MagicMock()
        m.__enter__.return_value = m
        m.__exit__.return_value = False
        m.get_current_user.side_effect = httpx.ConnectError("down")
        return m

    monkeypatch.setattr(promote_mod, "ForgejoClient", boom)
    promote_mod._finalize_forgejo_item(_config(), "cc_forge", 5, "https://gh/x")  # no raise
    assert "could not close" in capsys.readouterr().err


def test_provenance_footer_links_when_url_present():
    footer = promote_mod._provenance_footer("issue", 12, "http://x/issues/12")
    assert "Forgejo issue #12" in footer and "(http://x/issues/12)" in footer


def test_provenance_footer_plain_without_url():
    footer = promote_mod._provenance_footer("PR", 7, "")
    assert "Forgejo PR #7" in footer and "(" not in footer
