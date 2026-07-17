"""Tests for docker/gh-shim.sh — the Forgejo-backed gh CLI shim.

Each test runs the shim with a patched PATH containing a fake `curl` that
records its argv to a log file, plus a temporary workspace git repo with a
Forgejo-style origin. Tests assert the URL, method, and (for POSTs) body the
shim would have sent to Forgejo.
"""

from __future__ import annotations

import json
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


@pytest.fixture
def smart_fake_curl(tmp_path):
    """Fake curl that returns URL-conditional responses.

    Returns (bin_dir, log, set_route).
    set_route(url_substring, body='{}', exit_code=0) configures a response.
    """
    bin_dir = tmp_path / "smartbin"
    bin_dir.mkdir()
    log = tmp_path / "smartcurl.log"
    routes_dir = tmp_path / "routes"
    routes_dir.mkdir()
    fake = bin_dir / "curl"
    # Track routes as (substring, body_file, exit_code) triples.
    route_list: list[tuple[str, str, int]] = []

    def _write_script():
        # Build case branches from route_list.
        branches = ""
        for substring, body_file, exit_code in route_list:
            branches += f'        *"{substring}"*) cat "{body_file}"; exit {exit_code} ;;\n'
        fake.write_text(
            "#!/bin/bash\n"
            f'for a in "$@"; do printf "%s\\n" "$a"; done >> "{log}"\n'
            f'printf "---\\n" >> "{log}"\n'
            "# Find the URL argument (last positional not starting with -).\n"
            "url=''\n"
            'for a in "$@"; do\n'
            '    case "$a" in\n'
            '        -*) ;;\n'
            '        *://*) url="$a" ;;\n'
            "    esac\n"
            "done\n"
            'case "$url" in\n'
            f"{branches}"
            "    *) echo '{}' ;;\n"
            "esac\n"
        )
        fake.chmod(0o755)

    def set_route(url_substring: str, body: str = "{}", exit_code: int = 0):
        body_file = routes_dir / f"route_{len(route_list)}"
        body_file.write_text(body)
        route_list.append((url_substring, str(body_file), exit_code))
        _write_script()

    _write_script()  # default: always return '{}'
    return bin_dir, log, set_route


def _run(args, env, bin_dir):
    full_env = {
        **os.environ,
        **env,
        "PATH": f"{bin_dir}:{os.environ.get('PATH', '')}",
    }
    # Strip ambient forge env vars so the suite is hermetic.
    for key in list(full_env.keys()):
        if key.startswith("FORGE_") or key.startswith("FORGEJO_"):
            if key not in env:
                del full_env[key]
    # Prevent the shim from sourcing the default credentials file unless
    # the test explicitly sets FORGE_SHIM_CREDS_FILE.
    if "FORGE_SHIM_CREDS_FILE" not in env:
        full_env["FORGE_SHIM_CREDS_FILE"] = "/dev/null/nonexistent"
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

    def test_ignored_flags_are_tolerated(self, fake_repo, fake_curl):
        # --json/--jq/-q are documented as tolerated; pr create must not error on them.
        bin_dir, log = fake_curl
        result = _run(
            ["pr", "create", "--title", "T", "--head", "topic", "--json", "number", "-q", ".number"],
            _env(fake_repo), bin_dir,
        )
        assert result.returncode == 0, result.stderr
        assert '"title":"T"' in log.read_text()


class TestPrView:
    def test_gets_pulls_by_number(self, fake_repo, fake_curl):
        bin_dir, log = fake_curl
        # N=7 with both creds → tries GitHub first (gets '{}'), returns that.
        result = _run(["pr", "view", "7"], _env(fake_repo), bin_dir)
        assert result.returncode == 0, result.stderr
        assert "https://api.github.com/repos/ghorg/widgets/pulls/7" in log.read_text()

    def test_missing_number_fails(self, fake_repo, fake_curl):
        bin_dir, _ = fake_curl
        result = _run(["pr", "view"], _env(fake_repo), bin_dir)
        assert result.returncode != 0
        assert "takes exactly one argument" in result.stderr

    def test_json_flag_is_tolerated(self, fake_repo, fake_curl):
        """--json is silently stripped (agents pass it but shim returns raw JSON)."""
        bin_dir, _ = fake_curl
        result = _run(["pr", "view", "7", "--json", "title"], _env(fake_repo), bin_dir)
        assert result.returncode == 0, result.stderr


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


class TestIssueCreate:
    def test_posts_to_issues_endpoint(self, fake_repo, fake_curl):
        bin_dir, log = fake_curl
        result = _run(
            ["issue", "create", "--title", "Bug report", "--body", "Details here"],
            _env(fake_repo),
            bin_dir,
        )
        assert result.returncode == 0, result.stderr
        logged = log.read_text()
        assert "http://forge-forgejo:3000/api/v1/repos/alice/widgets/issues" in logged
        assert "POST" in logged
        assert '"title":"Bug report"' in logged
        assert '"body":"Details here"' in logged

    def test_title_only(self, fake_repo, fake_curl):
        bin_dir, log = fake_curl
        result = _run(
            ["issue", "create", "--title", "Minimal"],
            _env(fake_repo),
            bin_dir,
        )
        assert result.returncode == 0, result.stderr
        logged = log.read_text()
        assert '"title":"Minimal"' in logged

    def test_ignored_flags_are_tolerated(self, fake_repo, fake_curl):
        # --json/--jq/-q are documented as tolerated; issue create must not error on them.
        bin_dir, log = fake_curl
        result = _run(
            ["issue", "create", "--title", "T", "--jq", ".number", "-q", ".title"],
            _env(fake_repo), bin_dir,
        )
        assert result.returncode == 0, result.stderr
        assert '"title":"T"' in log.read_text()

    def test_missing_title_fails(self, fake_repo, fake_curl):
        bin_dir, _ = fake_curl
        result = _run(
            ["issue", "create", "--body", "no title"],
            _env(fake_repo),
            bin_dir,
        )
        assert result.returncode != 0
        assert "--title is required" in result.stderr

    def test_rejects_dash_R(self, fake_repo, fake_curl):
        bin_dir, _ = fake_curl
        result = _run(
            ["issue", "create", "-R", "owner/repo", "--title", "T"],
            _env(fake_repo),
            bin_dir,
        )
        assert result.returncode != 0
        assert "not supported on writes" in result.stderr

    def test_output_has_offset(self, fake_repo, smart_fake_curl):
        bin_dir, _, set_route = smart_fake_curl
        set_route("issues", body='{"number":5,"title":"new issue"}')
        result = _run(
            ["issue", "create", "--title", "T"],
            _env(fake_repo),
            bin_dir,
        )
        assert result.returncode == 0, result.stderr
        output = json.loads(result.stdout)
        assert output["number"] == 10005


class TestIssueList:
    def test_contacts_both_backends(self, fake_repo, fake_curl):
        """Without -R, issue list merges results from both backends."""
        bin_dir, log = fake_curl
        result = _run(["issue", "list"], _env(fake_repo), bin_dir)
        assert result.returncode == 0, result.stderr
        logged = log.read_text()
        # Both backends should be contacted.
        assert "api.github.com" in logged
        assert "forge-forgejo" in logged

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

    def test_no_creds_at_all_fails(self, fake_repo, fake_curl):
        """With no GitHub AND no Forgejo creds, issue list fails."""
        bin_dir, _ = fake_curl
        env = {
            "FORGE_WORKSPACE": str(fake_repo),
        }
        result = _run(["issue", "list"], env, bin_dir)
        assert result.returncode != 0
        assert "no credentials" in result.stderr

    def test_forgejo_only_fallback_on_missing_github(self, fake_repo, fake_curl):
        """With Forgejo creds but no GitHub creds, issue list succeeds (Forgejo only)."""
        bin_dir, log = fake_curl
        env = _env(fake_repo)
        env.pop("FORGE_GITHUB_TOKEN")
        env.pop("FORGE_GITHUB_OWNER")
        result = _run(["issue", "list"], env, bin_dir)
        assert result.returncode == 0, result.stderr
        logged = log.read_text()
        assert "forge-forgejo" in logged

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

    def test_pr_view_forgejo_with_offset(self, fake_repo, fake_curl):
        """N > 10000 → Forgejo (subtract offset for real number)."""
        bin_dir, log = fake_curl
        result = _run(["pr", "view", "10007"], _env(fake_repo), bin_dir)
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
    """Write commands reject -R since writes always target Forgejo."""

    def test_issue_create_rejects_dash_R(self, fake_repo, fake_curl):
        bin_dir, _ = fake_curl
        result = _run(
            ["issue", "create", "-R", "anthropics/sdk", "--title", "T"],
            _env(fake_repo), bin_dir,
        )
        assert result.returncode != 0
        assert "not supported on writes" in result.stderr

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
    def test_rejects_unknown_top_level_command(self, fake_repo, fake_curl):
        bin_dir, log = fake_curl
        result = _run(["api", "/repos/test"], _env(fake_repo), bin_dir)
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
        result = _run(["api", "/repos/test"], env, bin_dir)
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
        """Forgejo-forced path (N>10000) fails without FORGEJO_URL."""
        bin_dir, _ = fake_curl
        env = _env(fake_repo)
        env.pop("FORGEJO_URL")
        result = _run(["pr", "view", "10001"], env, bin_dir)
        assert result.returncode != 0
        assert "FORGEJO_URL not set" in result.stderr

    def test_missing_forgejo_token_fails(self, fake_repo, fake_curl):
        """Forgejo-forced path (N>10000) fails without FORGEJO_TOKEN."""
        bin_dir, _ = fake_curl
        env = _env(fake_repo)
        env.pop("FORGEJO_TOKEN")
        result = _run(["pr", "view", "10001"], env, bin_dir)
        assert result.returncode != 0
        assert "FORGEJO_TOKEN not set" in result.stderr


class TestRepoDetection:
    """Forgejo origin parsing. Exercised through `pr view` because that's the
    code path that consults the workspace's origin remote directly."""

    def test_parses_owner_repo_from_http_remote(self, fake_repo, fake_curl):
        bin_dir, log = fake_curl
        result = _run(["pr", "view", "10001"], _env(fake_repo), bin_dir)
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
        result = _run(["pr", "view", "10001"], env, bin_dir)
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
        result = _run(["pr", "view", "10001"], env, bin_dir)
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
        result = _run(["pr", "view", "10001"], env, bin_dir)
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
        # Both backends contacted in merged listing mode.
        assert "api.github.com" in logged
        assert "Authorization: token contract-github-token" in logged


# ---- New test classes for expanded shim ----


class TestOffsetRouting:
    """Unified number-space offset model."""

    def test_forgejo_number_routes_to_forgejo(self, fake_repo, fake_curl):
        """N > 10000 → Forgejo with real number (N - 10000)."""
        bin_dir, log = fake_curl
        result = _run(["pr", "view", "10005"], _env(fake_repo), bin_dir)
        assert result.returncode == 0, result.stderr
        logged = log.read_text()
        assert "http://forge-forgejo:3000/api/v1/repos/alice/widgets/pulls/5" in logged
        assert "api.github.com" not in logged

    def test_low_number_tries_github_first(self, fake_repo, fake_curl):
        """N <= 10000 with GitHub creds → tries GitHub."""
        bin_dir, log = fake_curl
        result = _run(["pr", "view", "5"], _env(fake_repo), bin_dir)
        assert result.returncode == 0, result.stderr
        logged = log.read_text()
        assert "api.github.com" in logged

    def test_low_number_falls_back_to_forgejo_on_github_failure(
        self, fake_repo, smart_fake_curl,
    ):
        """N <= 10000, GitHub returns empty → falls back to Forgejo."""
        bin_dir, log, set_route = smart_fake_curl
        # GitHub returns empty (curl fails silently)
        set_route("api.github.com", body="", exit_code=22)
        # Forgejo returns valid data
        set_route("forge-forgejo", body='{"number":5,"title":"test"}')
        result = _run(["pr", "view", "5"], _env(fake_repo), bin_dir)
        assert result.returncode == 0, result.stderr
        # Output should have offset applied
        output = json.loads(result.stdout)
        assert output["number"] == 10005

    def test_dash_R_bypasses_offset(self, fake_repo, fake_curl):
        """-R routes directly to GitHub, no offset."""
        bin_dir, log = fake_curl
        result = _run(
            ["pr", "view", "-R", "owner/repo", "42"],
            _env(fake_repo), bin_dir,
        )
        assert result.returncode == 0, result.stderr
        logged = log.read_text()
        assert "https://api.github.com/repos/owner/repo/pulls/42" in logged
        assert "forge-forgejo" not in logged

    def test_no_github_creds_routes_to_forgejo(self, fake_repo, fake_curl):
        """Without GitHub creds, low N goes to Forgejo."""
        bin_dir, log = fake_curl
        env = _env(fake_repo)
        env.pop("FORGE_GITHUB_TOKEN")
        env.pop("FORGE_GITHUB_OWNER")
        result = _run(["pr", "view", "5"], env, bin_dir)
        assert result.returncode == 0, result.stderr
        logged = log.read_text()
        assert "forge-forgejo" in logged

    def test_issue_view_forgejo_number(self, fake_repo, fake_curl):
        """issue view with N > 10000 → Forgejo."""
        bin_dir, log = fake_curl
        result = _run(["issue", "view", "10003"], _env(fake_repo), bin_dir)
        assert result.returncode == 0, result.stderr
        logged = log.read_text()
        assert "http://forge-forgejo:3000/api/v1/repos/alice/widgets/issues/3" in logged


class TestPrCreateAutoHead:
    """pr create auto-detects --head from current branch."""

    def test_auto_detects_branch(self, fake_repo, fake_curl):
        bin_dir, log = fake_curl
        # Create and checkout a branch
        subprocess.run(
            ["git", "checkout", "-q", "-b", "feature/auto"],
            cwd=fake_repo, check=True,
        )
        result = _run(
            ["pr", "create", "--title", "Auto-head test"],
            _env(fake_repo), bin_dir,
        )
        assert result.returncode == 0, result.stderr
        logged = log.read_text()
        assert '"head":"feature/auto"' in logged

    def test_explicit_head_wins(self, fake_repo, fake_curl):
        bin_dir, log = fake_curl
        subprocess.run(
            ["git", "checkout", "-q", "-b", "feature/auto"],
            cwd=fake_repo, check=True,
        )
        result = _run(
            ["pr", "create", "--title", "T", "--head", "explicit-branch"],
            _env(fake_repo), bin_dir,
        )
        assert result.returncode == 0, result.stderr
        logged = log.read_text()
        assert '"head":"explicit-branch"' in logged

    def test_detached_head_fails(self, fake_repo, fake_curl):
        bin_dir, _ = fake_curl
        # Create a commit so we can detach
        subprocess.run(
            ["git", "commit", "--allow-empty", "-m", "init", "-q"],
            cwd=fake_repo,
            check=True,
            env={**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
                 "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"},
        )
        subprocess.run(
            ["git", "checkout", "--detach", "-q"],
            cwd=fake_repo, check=True,
        )
        result = _run(
            ["pr", "create", "--title", "T"],
            _env(fake_repo), bin_dir,
        )
        assert result.returncode != 0
        assert "detached HEAD" in result.stderr


class TestRepoView:
    def test_default_routes_to_forgejo(self, fake_repo, fake_curl):
        bin_dir, log = fake_curl
        result = _run(["repo", "view"], _env(fake_repo), bin_dir)
        assert result.returncode == 0, result.stderr
        logged = log.read_text()
        assert "http://forge-forgejo:3000/api/v1/repos/alice/widgets" in logged

    def test_dash_R_routes_to_github(self, fake_repo, fake_curl):
        bin_dir, log = fake_curl
        result = _run(
            ["repo", "view", "-R", "owner/repo"],
            _env(fake_repo), bin_dir,
        )
        assert result.returncode == 0, result.stderr
        logged = log.read_text()
        assert "https://api.github.com/repos/owner/repo" in logged

    def test_extra_args_rejected(self, fake_repo, fake_curl):
        bin_dir, _ = fake_curl
        result = _run(["repo", "view", "extra"], _env(fake_repo), bin_dir)
        assert result.returncode != 0
        assert "takes no arguments" in result.stderr


class TestPrList:
    def test_merged_listing_contacts_both(self, fake_repo, smart_fake_curl):
        bin_dir, log, set_route = smart_fake_curl
        set_route("api.github.com", body='[{"number":1,"title":"gh"}]')
        set_route("forge-forgejo", body='[{"number":1,"title":"fj"}]')
        result = _run(["pr", "list"], _env(fake_repo), bin_dir)
        assert result.returncode == 0, result.stderr
        output = json.loads(result.stdout)
        sources = {item["_source"] for item in output}
        assert "github" in sources
        assert "forgejo" in sources

    def test_dash_R_github_only(self, fake_repo, fake_curl):
        bin_dir, log = fake_curl
        result = _run(
            ["pr", "list", "-R", "owner/repo"],
            _env(fake_repo), bin_dir,
        )
        assert result.returncode == 0, result.stderr
        logged = log.read_text()
        assert "https://api.github.com/repos/owner/repo/pulls" in logged
        assert "forge-forgejo" not in logged

    def test_extra_args_rejected(self, fake_repo, fake_curl):
        bin_dir, _ = fake_curl
        result = _run(["pr", "list", "--state", "all"], _env(fake_repo), bin_dir)
        assert result.returncode != 0
        assert "takes no arguments" in result.stderr


class TestPrChecks:
    def test_forgejo_pr_checks(self, fake_repo, smart_fake_curl):
        bin_dir, log, set_route = smart_fake_curl
        set_route("pulls/3", body='{"number":3,"head":{"sha":"def456"}}')
        set_route("statuses", body='[{"status":"success"}]')
        result = _run(["pr", "checks", "10003"], _env(fake_repo), bin_dir)
        assert result.returncode == 0, result.stderr
        logged = log.read_text()
        assert "forge-forgejo" in logged
        assert "pulls/3" in logged
        assert "def456" in logged

    def test_dash_R_github_checks(self, fake_repo, smart_fake_curl):
        bin_dir, log, set_route = smart_fake_curl
        set_route("pulls/7", body='{"number":7,"head":{"sha":"gh789"}}')
        set_route("check-runs", body='{"check_runs":[]}')
        result = _run(
            ["pr", "checks", "-R", "owner/repo", "7"],
            _env(fake_repo), bin_dir,
        )
        assert result.returncode == 0, result.stderr
        logged = log.read_text()
        assert "api.github.com" in logged
        assert "gh789" in logged

    def test_missing_number_fails(self, fake_repo, fake_curl):
        bin_dir, _ = fake_curl
        result = _run(["pr", "checks"], _env(fake_repo), bin_dir)
        assert result.returncode != 0
        assert "takes exactly one argument" in result.stderr


class TestPrDiff:
    def test_forgejo_raw_endpoint(self, fake_repo, fake_curl):
        """Forgejo diff uses web endpoint (no /api/v1/)."""
        bin_dir, log = fake_curl
        result = _run(["pr", "diff", "10003"], _env(fake_repo), bin_dir)
        assert result.returncode == 0, result.stderr
        logged = log.read_text()
        # Should NOT use /api/v1/ path
        assert "http://forge-forgejo:3000/alice/widgets/pulls/3.diff" in logged

    def test_github_accept_header(self, fake_repo, fake_curl):
        bin_dir, log = fake_curl
        result = _run(
            ["pr", "diff", "-R", "owner/repo", "7"],
            _env(fake_repo), bin_dir,
        )
        assert result.returncode == 0, result.stderr
        logged = log.read_text()
        assert "application/vnd.github.v3.diff" in logged
        assert "api.github.com" in logged

    def test_missing_number_fails(self, fake_repo, fake_curl):
        bin_dir, _ = fake_curl
        result = _run(["pr", "diff"], _env(fake_repo), bin_dir)
        assert result.returncode != 0
        assert "takes exactly one argument" in result.stderr


class TestMergedIssueListing:
    def test_both_backends_contacted(self, fake_repo, smart_fake_curl):
        bin_dir, log, set_route = smart_fake_curl
        set_route("api.github.com", body='[{"number":1,"title":"gh-issue"}]')
        set_route("forge-forgejo", body='[{"number":2,"title":"fj-issue"}]')
        result = _run(["issue", "list"], _env(fake_repo), bin_dir)
        assert result.returncode == 0, result.stderr
        output = json.loads(result.stdout)
        sources = {item["_source"] for item in output}
        assert "github" in sources
        assert "forgejo" in sources
        # Forgejo items should have offset applied
        fj_items = [i for i in output if i["_source"] == "forgejo"]
        assert all(i["number"] > 10000 for i in fj_items)

    def test_forgejo_only_when_no_github_creds(self, fake_repo, smart_fake_curl):
        bin_dir, log, set_route = smart_fake_curl
        set_route("forge-forgejo", body='[{"number":1,"title":"fj-only"}]')
        env = _env(fake_repo)
        env.pop("FORGE_GITHUB_TOKEN")
        env.pop("FORGE_GITHUB_OWNER")
        result = _run(["issue", "list"], env, bin_dir)
        assert result.returncode == 0, result.stderr
        output = json.loads(result.stdout)
        assert all(item["_source"] == "forgejo" for item in output)

    def test_no_creds_at_all_fails(self, fake_repo, fake_curl):
        bin_dir, _ = fake_curl
        env = {"FORGE_WORKSPACE": str(fake_repo)}
        result = _run(["issue", "list"], env, bin_dir)
        assert result.returncode != 0
        assert "no credentials" in result.stderr


class TestIgnoredFlags:
    """--json, --jq, -q are silently stripped."""

    def test_json_flag_on_pr_view(self, fake_repo, fake_curl):
        bin_dir, _ = fake_curl
        result = _run(["pr", "view", "10001", "--json", "title"], _env(fake_repo), bin_dir)
        assert result.returncode == 0, result.stderr

    def test_jq_flag_on_issue_view(self, fake_repo, fake_curl):
        bin_dir, _ = fake_curl
        result = _run(["issue", "view", "12", "--jq", ".title"], _env(fake_repo), bin_dir)
        assert result.returncode == 0, result.stderr

    def test_q_flag_on_repo_view(self, fake_repo, fake_curl):
        bin_dir, _ = fake_curl
        result = _run(["repo", "view", "-q", ".name"], _env(fake_repo), bin_dir)
        assert result.returncode == 0, result.stderr

    def test_json_equals_form(self, fake_repo, fake_curl):
        bin_dir, _ = fake_curl
        result = _run(["pr", "view", "10001", "--json=title"], _env(fake_repo), bin_dir)
        assert result.returncode == 0, result.stderr

    def test_jq_equals_form(self, fake_repo, fake_curl):
        bin_dir, _ = fake_curl
        result = _run(["issue", "view", "12", "--jq=.title"], _env(fake_repo), bin_dir)
        assert result.returncode == 0, result.stderr


class TestOutputTransformation:
    """Verify offset is applied to output."""

    def test_pr_create_output_has_offset(self, fake_repo, smart_fake_curl):
        bin_dir, log, set_route = smart_fake_curl
        set_route("pulls", body='{"number":3,"title":"new PR"}')
        result = _run(
            ["pr", "create", "--title", "T", "--head", "h"],
            _env(fake_repo), bin_dir,
        )
        assert result.returncode == 0, result.stderr
        output = json.loads(result.stdout)
        assert output["number"] == 10003

    def test_pr_view_forgejo_output_has_offset(self, fake_repo, smart_fake_curl):
        bin_dir, log, set_route = smart_fake_curl
        set_route("pulls/5", body='{"number":5,"title":"existing PR"}')
        result = _run(["pr", "view", "10005"], _env(fake_repo), bin_dir)
        assert result.returncode == 0, result.stderr
        output = json.loads(result.stdout)
        assert output["number"] == 10005

    def test_issue_view_forgejo_output_has_offset(self, fake_repo, smart_fake_curl):
        bin_dir, log, set_route = smart_fake_curl
        set_route("issues/2", body='{"number":2,"title":"issue"}')
        result = _run(["issue", "view", "10002"], _env(fake_repo), bin_dir)
        assert result.returncode == 0, result.stderr
        output = json.loads(result.stdout)
        assert output["number"] == 10002
