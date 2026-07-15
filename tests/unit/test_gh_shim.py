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
    # Workspace origin = http://forge-forgejo:3000/alice/widgets.git
    #   Forgejo target → alice/widgets (from origin remote)
    #   GitHub target  → ghorg/widgets (FORGE_GITHUB_OWNER + workspace basename)
    # The differing owners make routing easy to tell apart in assertions.
    #
    # In production the shim reads these from a credentials file written by
    # forge; in tests we set them directly via env (the shim sources the file
    # only if one exists, otherwise it falls through to whatever's in env).
    return {
        "FORGEJO_URL": "http://forge-forgejo:3000",
        "FORGEJO_TOKEN": "forgejo-test-token",
        "FORGE_GITHUB_TOKEN": "github-test-token",
        "FORGE_GITHUB_OWNER": "ghorg",
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
        assert "Authorization: token forgejo-test-token" in logged
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

    def test_flag_without_value_fails_with_arity_error(self, fake_repo, fake_curl):
        # Last-arg flag should produce a shim error, not a bash "unbound variable"
        # message (which set -u would emit if $2 were read unguarded).
        bin_dir, _ = fake_curl
        result = _run(
            ["pr", "create", "--head", "topic", "--title"],
            _env(fake_repo),
            bin_dir,
        )
        assert result.returncode != 0
        assert "--title needs a value" in result.stderr
        assert "unbound variable" not in result.stderr


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
        assert "takes exactly one argument" in result.stderr

    def test_extra_args_rejected(self, fake_repo, fake_curl):
        bin_dir, _ = fake_curl
        result = _run(["pr", "view", "7", "--json"], _env(fake_repo), bin_dir)
        assert result.returncode != 0
        assert "takes exactly one argument" in result.stderr


class TestIssueView:
    def test_routes_to_github_with_github_credentials(self, fake_repo, fake_curl):
        bin_dir, log = fake_curl
        result = _run(["issue", "view", "12"], _env(fake_repo), bin_dir)
        assert result.returncode == 0, result.stderr
        logged = log.read_text()
        assert "https://api.github.com/repos/ghorg/widgets/issues/12" in logged
        # GitHub auth used, Forgejo auth not leaked into this call
        assert "token github-test-token" in logged
        assert "token forgejo-test-token" not in logged

    def test_extra_args_rejected(self, fake_repo, fake_curl):
        bin_dir, _ = fake_curl
        result = _run(["issue", "view", "12", "--web"], _env(fake_repo), bin_dir)
        assert result.returncode != 0
        assert "takes exactly one argument" in result.stderr


class TestIssueList:
    def test_routes_to_github(self, fake_repo, fake_curl):
        bin_dir, log = fake_curl
        result = _run(["issue", "list"], _env(fake_repo), bin_dir)
        assert result.returncode == 0, result.stderr
        logged = log.read_text()
        assert "https://api.github.com/repos/ghorg/widgets/issues" in logged

    def test_any_args_rejected(self, fake_repo, fake_curl):
        bin_dir, _ = fake_curl
        result = _run(["issue", "list", "--state", "all"], _env(fake_repo), bin_dir)
        assert result.returncode != 0
        assert "takes no arguments" in result.stderr


class TestGithubRouting:
    def test_forge_github_repo_overrides_owner(self, fake_repo, fake_curl):
        bin_dir, log = fake_curl
        env = _env(fake_repo)
        env["FORGE_GITHUB_REPO"] = "explicit/override"
        # FORGE_GITHUB_OWNER is also set — REPO should win.
        result = _run(["issue", "view", "5"], env, bin_dir)
        assert result.returncode == 0, result.stderr
        logged = log.read_text()
        assert "https://api.github.com/repos/explicit/override/issues/5" in logged
        assert "ghorg" not in logged

    def test_missing_github_token_fails_clearly(self, fake_repo, fake_curl):
        bin_dir, _ = fake_curl
        env = _env(fake_repo)
        env.pop("FORGE_GITHUB_TOKEN")
        result = _run(["issue", "list"], env, bin_dir)
        assert result.returncode != 0
        assert "FORGE_GITHUB_TOKEN not set" in result.stderr

    def test_missing_routing_config_fails_clearly(self, fake_repo, fake_curl):
        # Token set but neither REPO nor OWNER set → can't resolve target.
        bin_dir, _ = fake_curl
        env = _env(fake_repo)
        env.pop("FORGE_GITHUB_OWNER")
        result = _run(["issue", "list"], env, bin_dir)
        assert result.returncode != 0
        assert "cannot route to GitHub" in result.stderr

    def test_pr_commands_unaffected_when_github_not_configured(
        self, fake_repo, fake_curl,
    ):
        # PR ops should keep working even with no GitHub creds in env.
        bin_dir, log = fake_curl
        env = _env(fake_repo)
        env.pop("FORGE_GITHUB_TOKEN")
        env.pop("FORGE_GITHUB_OWNER")
        result = _run(["pr", "view", "7"], env, bin_dir)
        assert result.returncode == 0, result.stderr
        assert "http://forge-forgejo:3000/api/v1/repos/alice/widgets/pulls/7" in log.read_text()


class TestDashROnReads:
    """-R/--repo on read commands targets a specific GitHub repo."""

    def test_pr_view_with_dash_R_routes_to_github(self, fake_repo, fake_curl):
        bin_dir, log = fake_curl
        result = _run(
            ["pr", "view", "-R", "anthropics/sdk", "42"],
            _env(fake_repo), bin_dir,
        )
        assert result.returncode == 0, result.stderr
        logged = log.read_text()
        assert "https://api.github.com/repos/anthropics/sdk/pulls/42" in logged
        assert "forge-forgejo" not in logged

    def test_pr_view_long_repo_flag(self, fake_repo, fake_curl):
        bin_dir, log = fake_curl
        result = _run(
            ["pr", "view", "--repo", "anthropics/sdk", "42"],
            _env(fake_repo), bin_dir,
        )
        assert result.returncode == 0, result.stderr
        assert "https://api.github.com/repos/anthropics/sdk/pulls/42" in log.read_text()

    def test_pr_view_equals_form(self, fake_repo, fake_curl):
        bin_dir, log = fake_curl
        result = _run(
            ["pr", "view", "--repo=anthropics/sdk", "42"],
            _env(fake_repo), bin_dir,
        )
        assert result.returncode == 0, result.stderr
        assert "https://api.github.com/repos/anthropics/sdk/pulls/42" in log.read_text()

    def test_pr_view_default_still_forgejo(self, fake_repo, fake_curl):
        # Regression: no -R → Forgejo (unchanged behavior).
        bin_dir, log = fake_curl
        result = _run(["pr", "view", "7"], _env(fake_repo), bin_dir)
        assert result.returncode == 0, result.stderr
        assert "http://forge-forgejo:3000/api/v1/repos/alice/widgets/pulls/7" in log.read_text()

    def test_issue_view_with_dash_R_overrides_config_chain(
        self, fake_repo, fake_curl,
    ):
        # FORGE_GITHUB_OWNER is set; -R should override it.
        bin_dir, log = fake_curl
        result = _run(
            ["issue", "view", "-R", "explicit/override", "5"],
            _env(fake_repo), bin_dir,
        )
        assert result.returncode == 0, result.stderr
        logged = log.read_text()
        assert "https://api.github.com/repos/explicit/override/issues/5" in logged
        assert "ghorg" not in logged

    def test_issue_list_with_dash_R(self, fake_repo, fake_curl):
        bin_dir, log = fake_curl
        result = _run(
            ["issue", "list", "-R", "explicit/override"],
            _env(fake_repo), bin_dir,
        )
        assert result.returncode == 0, result.stderr
        assert "https://api.github.com/repos/explicit/override/issues" in log.read_text()

    def test_dash_R_without_value_fails(self, fake_repo, fake_curl):
        bin_dir, _ = fake_curl
        result = _run(
            ["pr", "view", "7", "-R"],
            _env(fake_repo), bin_dir,
        )
        assert result.returncode != 0
        assert "needs a value" in result.stderr


class TestDashROnWrites:
    """pr create rejects -R since writes always target Forgejo."""

    def test_pr_create_rejects_dash_R(self, fake_repo, fake_curl):
        bin_dir, _ = fake_curl
        result = _run(
            ["pr", "create", "-R", "anthropics/sdk",
             "--title", "T", "--head", "h"],
            _env(fake_repo), bin_dir,
        )
        assert result.returncode != 0
        assert "not supported on writes" in result.stderr

    def test_pr_create_rejects_long_repo(self, fake_repo, fake_curl):
        bin_dir, _ = fake_curl
        result = _run(
            ["pr", "create", "--repo", "anthropics/sdk",
             "--title", "T", "--head", "h"],
            _env(fake_repo), bin_dir,
        )
        assert result.returncode != 0
        assert "not supported on writes" in result.stderr

    def test_pr_create_rejects_equals_form(self, fake_repo, fake_curl):
        bin_dir, _ = fake_curl
        result = _run(
            ["pr", "create", "--repo=anthropics/sdk",
             "--title", "T", "--head", "h"],
            _env(fake_repo), bin_dir,
        )
        assert result.returncode != 0
        assert "not supported on writes" in result.stderr


class TestAllowlist:
    def test_rejects_unknown_subcommand(self, fake_repo, fake_curl):
        bin_dir, log = fake_curl
        result = _run(["repo", "view"], _env(fake_repo), bin_dir)
        assert result.returncode != 0
        assert "not supported" in result.stderr
        assert log.exists() is False or log.read_text() == ""

    def test_unknown_subcommand_surfaces_allowlist_error_not_env_error(
        self, fake_repo, fake_curl,
    ):
        # require_env runs inside cmd_* functions, so unsupported subcommands
        # should report the allowlist mismatch even when env is unset.
        bin_dir, _ = fake_curl
        env = {"FORGE_WORKSPACE": str(fake_repo)}  # no FORGEJO_URL/TOKEN
        result = _run(["repo", "view"], env, bin_dir)
        assert result.returncode != 0
        assert "not supported" in result.stderr
        assert "FORGEJO_URL not set" not in result.stderr

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
    """Forgejo origin parsing. Exercised through `pr view` because that's the
    code path that consults the workspace's origin remote directly."""

    def test_parses_owner_repo_from_http_remote(self, fake_repo, fake_curl):
        bin_dir, log = fake_curl
        result = _run(["pr", "view", "1"], _env(fake_repo), bin_dir)
        assert result.returncode == 0
        assert "/repos/alice/widgets/pulls/1" in log.read_text()

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
        result = _run(["pr", "view", "1"], env, bin_dir)
        assert result.returncode == 0, result.stderr
        assert "/repos/bob/thing/pulls/1" in log.read_text()

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
        result = _run(["pr", "view", "1"], env, bin_dir)
        assert result.returncode != 0
        assert "could not read origin remote" in result.stderr


class TestShimCredentialsContract:
    """End-to-end contract: forge writes the credentials file → shim reads it.

    This is what catches the class of bug where the shim and the docker
    injector silently disagree about how credentials are delivered (e.g.,
    container-hardening removed env vars, leaving the shim broken). Each side's
    unit tests can pass while the integration fails. This test exercises both
    sides against the actual file they share.
    """

    def _build_creds_file(self, tmp_path, **config_overrides):
        """Run the real injector against a captured tar, extract the file."""
        from unittest.mock import MagicMock
        import tarfile
        from cc_forge.config import ForgeConfig
        from cc_forge.docker import _inject_shim_credentials

        cfg = ForgeConfig(
            forgejo_url="http://forge-forgejo:3000",
            forgejo_token="contract-forgejo-token",
            ollama_cpu_url="http://localhost:11434",
            agent_image="t",
            agent_model="t",
            agent_api_key="",
            compose_file="",
            github_token="contract-github-token",
            github_repo="",
            github_owner="contract-org",
            agent_mem_limit="4g",
            agent_pids_limit=4096,
            **config_overrides,
        )
        bufs = []
        container = MagicMock()
        container.put_archive = lambda _path, buf: bufs.append(buf)
        _inject_shim_credentials(container, cfg)
        assert bufs, "_inject_shim_credentials produced no archive"

        creds_dest = tmp_path / "credentials"
        bufs[0].seek(0)
        with tarfile.open(fileobj=bufs[0], mode="r") as tar:
            for member in tar.getmembers():
                if member.name.endswith("/credentials"):
                    creds_dest.write_bytes(tar.extractfile(member).read())
                    break
        assert creds_dest.exists(), "credentials file not found in tar"
        return creds_dest

    def test_shim_reads_forgejo_credentials_from_injected_file(
        self, tmp_path, fake_repo, fake_curl,
    ):
        creds = self._build_creds_file(tmp_path)
        bin_dir, log = fake_curl
        env = {
            # No FORGEJO_URL/TOKEN in env — they must come from the file.
            "FORGE_SHIM_CREDS_FILE": str(creds),
            "FORGE_WORKSPACE": str(fake_repo),
        }
        result = _run(["pr", "view", "1"], env, bin_dir)
        assert result.returncode == 0, result.stderr
        logged = log.read_text()
        assert "http://forge-forgejo:3000/api/v1/repos/alice/widgets/pulls/1" in logged
        assert "Authorization: token contract-forgejo-token" in logged

    def test_shim_reads_github_credentials_from_injected_file(
        self, tmp_path, fake_repo, fake_curl,
    ):
        creds = self._build_creds_file(tmp_path)
        bin_dir, log = fake_curl
        env = {
            # No FORGE_GITHUB_TOKEN/OWNER in env — they must come from the file.
            "FORGE_SHIM_CREDS_FILE": str(creds),
            "FORGE_WORKSPACE": str(fake_repo),
        }
        result = _run(["issue", "list"], env, bin_dir)
        assert result.returncode == 0, result.stderr
        logged = log.read_text()
        # Workspace basename is "widgets"; FORGE_GITHUB_OWNER from the file is
        # "contract-org" → target is contract-org/widgets.
        assert "https://api.github.com/repos/contract-org/widgets/issues" in logged
        assert "Authorization: token contract-github-token" in logged
