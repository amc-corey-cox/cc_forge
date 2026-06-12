"""Tests for docker/gh-shim.sh — the Forgejo-backed gh CLI shim.

Each test runs the shim with a patched PATH containing a fake `curl` that
records its argv to a log file, plus a temporary workspace git repo with a
Forgejo-style origin. Tests assert the URL, method, and (for POSTs) body the
shim would have sent to Forgejo.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

SHIM = Path(__file__).resolve().parents[2] / "docker" / "gh-shim.sh"


@pytest.fixture
def fake_repo(tmp_path):
    repo = tmp_path / "workspace" / "repo"
    repo.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    subprocess.run(
        ["git", "remote", "add", "origin",
         "http://forge-forgejo:3000/alice/widgets.git"],
        cwd=repo, check=True,
    )
    return repo


@pytest.fixture
def fake_curl(tmp_path):
    """Install a fake `curl` on PATH that records argv and prints '{}'."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "curl.log"
    fake = bin_dir / "curl"
    fake.write_text(
        "#!/bin/bash\n"
        f'for a in "$@"; do printf "%s\\n" "$a"; done >> "{log}"\n'
        "echo '{}'\n"
    )
    fake.chmod(0o755)
    return bin_dir, log


def _run(args, env, bin_dir):
    full_env = {
        **os.environ,
        **env,
        "PATH": f"{bin_dir}:{os.environ.get('PATH', '')}",
    }
    return subprocess.run(
        ["bash", str(SHIM), *args],
        env=full_env,
        capture_output=True,
        text=True,
    )


def _env(fake_repo):
    return {
        "FORGEJO_URL": "http://forge-forgejo:3000",
        "FORGEJO_TOKEN": "test-token",
        "FORGE_WORKSPACE": str(fake_repo),
    }


class TestPrCreate:
    def test_posts_to_pulls_endpoint_with_required_fields(self, fake_repo, fake_curl):
        bin_dir, log = fake_curl
        result = _run(
            ["pr", "create", "--title", "Fix typo", "--head", "topic"],
            _env(fake_repo),
            bin_dir,
        )
        assert result.returncode == 0, result.stderr
        logged = log.read_text()
        assert "http://forge-forgejo:3000/api/v1/repos/alice/widgets/pulls" in logged
        assert "POST" in logged
        assert "Authorization: token test-token" in logged
        assert '"title":"Fix typo"' in logged
        assert '"head":"topic"' in logged
        assert '"base":"main"' in logged  # default base

    def test_accepts_custom_base_and_body(self, fake_repo, fake_curl):
        bin_dir, log = fake_curl
        result = _run(
            ["pr", "create",
             "--title", "T", "--head", "h", "--base", "develop", "--body", "B"],
            _env(fake_repo),
            bin_dir,
        )
        assert result.returncode == 0
        logged = log.read_text()
        assert '"base":"develop"' in logged
        assert '"body":"B"' in logged

    def test_missing_title_fails(self, fake_repo, fake_curl):
        bin_dir, _ = fake_curl
        result = _run(
            ["pr", "create", "--head", "topic"],
            _env(fake_repo),
            bin_dir,
        )
        assert result.returncode != 0
        assert "--title is required" in result.stderr


class TestPrView:
    def test_gets_pulls_by_number(self, fake_repo, fake_curl):
        bin_dir, log = fake_curl
        result = _run(["pr", "view", "7"], _env(fake_repo), bin_dir)
        assert result.returncode == 0, result.stderr
        logged = log.read_text()
        assert "http://forge-forgejo:3000/api/v1/repos/alice/widgets/pulls/7" in logged

    def test_missing_number_fails(self, fake_repo, fake_curl):
        bin_dir, _ = fake_curl
        result = _run(["pr", "view"], _env(fake_repo), bin_dir)
        assert result.returncode != 0
        assert "requires a number" in result.stderr


class TestIssueView:
    def test_gets_issue_by_number(self, fake_repo, fake_curl):
        bin_dir, log = fake_curl
        result = _run(["issue", "view", "12"], _env(fake_repo), bin_dir)
        assert result.returncode == 0, result.stderr
        logged = log.read_text()
        assert (
            "http://forge-forgejo:3000/api/v1/repos/alice/widgets/issues/12"
            in logged
        )


class TestIssueList:
    def test_lists_issues(self, fake_repo, fake_curl):
        bin_dir, log = fake_curl
        result = _run(["issue", "list"], _env(fake_repo), bin_dir)
        assert result.returncode == 0, result.stderr
        logged = log.read_text()
        assert (
            "http://forge-forgejo:3000/api/v1/repos/alice/widgets/issues"
            in logged
        )


class TestAllowlist:
    def test_rejects_unknown_subcommand(self, fake_repo, fake_curl):
        bin_dir, log = fake_curl
        result = _run(["repo", "view"], _env(fake_repo), bin_dir)
        assert result.returncode != 0
        assert "not supported" in result.stderr
        assert log.exists() is False or log.read_text() == ""

    def test_rejects_unknown_pr_subcommand(self, fake_repo, fake_curl):
        bin_dir, _ = fake_curl
        result = _run(["pr", "merge", "5"], _env(fake_repo), bin_dir)
        assert result.returncode != 0
        assert "not supported" in result.stderr

    def test_no_subcommand_fails_with_help(self, fake_repo, fake_curl):
        bin_dir, _ = fake_curl
        result = _run([], _env(fake_repo), bin_dir)
        assert result.returncode != 0
        assert "supported" in result.stderr


class TestEnvironment:
    def test_missing_forgejo_url_fails(self, fake_repo, fake_curl):
        bin_dir, _ = fake_curl
        env = _env(fake_repo)
        env.pop("FORGEJO_URL")
        result = _run(["pr", "view", "1"], env, bin_dir)
        assert result.returncode != 0
        assert "FORGEJO_URL not set" in result.stderr

    def test_missing_forgejo_token_fails(self, fake_repo, fake_curl):
        bin_dir, _ = fake_curl
        env = _env(fake_repo)
        env.pop("FORGEJO_TOKEN")
        result = _run(["pr", "view", "1"], env, bin_dir)
        assert result.returncode != 0
        assert "FORGEJO_TOKEN not set" in result.stderr


class TestRepoDetection:
    def test_parses_owner_repo_from_http_remote(self, fake_repo, fake_curl):
        bin_dir, log = fake_curl
        result = _run(["issue", "list"], _env(fake_repo), bin_dir)
        assert result.returncode == 0
        assert "/repos/alice/widgets/issues" in log.read_text()

    def test_handles_ssh_style_remote(self, tmp_path, fake_curl):
        repo = tmp_path / "ws"
        repo.mkdir()
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
        subprocess.run(
            ["git", "remote", "add", "origin",
             "git@forge-forgejo:bob/thing.git"],
            cwd=repo, check=True,
        )
        bin_dir, log = fake_curl
        env = {
            "FORGEJO_URL": "http://forge-forgejo:3000",
            "FORGEJO_TOKEN": "tok",
            "FORGE_WORKSPACE": str(repo),
        }
        result = _run(["issue", "list"], env, bin_dir)
        assert result.returncode == 0, result.stderr
        assert "/repos/bob/thing/issues" in log.read_text()

    def test_no_origin_fails_clearly(self, tmp_path, fake_curl):
        repo = tmp_path / "ws"
        repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
        bin_dir, _ = fake_curl
        env = {
            "FORGEJO_URL": "http://forge-forgejo:3000",
            "FORGEJO_TOKEN": "tok",
            "FORGE_WORKSPACE": str(repo),
        }
        result = _run(["issue", "list"], env, bin_dir)
        assert result.returncode != 0
        assert "could not read origin remote" in result.stderr
