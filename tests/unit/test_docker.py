"""Tests for docker module helpers."""
from __future__ import annotations

import io
import tarfile
from unittest.mock import MagicMock, patch

import pytest

from cc_forge.agents import (
    REGISTRY,
    _claude_api_environment,
    _claude_credentials_path,
    _copy_claude_config,
    _forge_claude_state_dir,
    _ollama_environment,
    _save_claude_credentials,
)
from cc_forge.config import ForgeConfig
from cc_forge.docker import (
    AGENT_UID,
    SHIM_CREDENTIALS_PATH,
    _inject_git_credentials,
    _inject_shim_credentials,
    _internal_forgejo_url,
    _rewrite_url,
)


def _make_config(**kwargs) -> ForgeConfig:
    defaults = dict(
        ollama_cpu_url="http://localhost:11434",
        ollama_gpu_url="http://localhost:11435",
        forgejo_url="http://localhost:3000",
        forgejo_token="test-token",
        agent_image="test",
        agent_model="test-model",
        agent_api_key="",
        compose_file="",
        github_token="",
        github_repo="",
        github_owner="",
        agent_mem_limit="4g",
        agent_pids_limit=4096,
    )
    defaults.update(kwargs)
    return ForgeConfig(**defaults)


def _make_tar(files: dict[str, bytes]) -> io.BytesIO:
    """Create an in-memory tar archive from {path: content} dict."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        for name, data in files.items():
            info = tarfile.TarInfo(name=name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    buf.seek(0)
    return buf


def _inspect_tar(buf: io.BytesIO) -> dict[str, tarfile.TarInfo]:
    """Return {name: TarInfo} for all members in a tar buffer."""
    buf.seek(0)
    with tarfile.open(fileobj=buf, mode="r") as tar:
        return {m.name: m for m in tar.getmembers()}


class TestRewriteUrl:
    def test_localhost_with_port(self):
        assert _rewrite_url("http://localhost:11434", "forge-ollama-proxy") == \
            "http://forge-ollama-proxy:11434"

    def test_127_with_port(self):
        assert _rewrite_url("http://127.0.0.1:3000", "forge-forgejo") == \
            "http://forge-forgejo:3000"

    def test_localhost_with_path(self):
        assert _rewrite_url("http://localhost/api/v1", "forge-forgejo") == \
            "http://forge-forgejo/api/v1"

    def test_localhost_no_port_no_path(self):
        assert _rewrite_url("http://localhost", "forge-forgejo") == \
            "http://forge-forgejo"

    def test_non_local_unchanged(self):
        url = "http://remote-host:11434"
        assert _rewrite_url(url, "forge-ollama-proxy") == url

    def test_host_docker_internal(self):
        assert _rewrite_url("http://localhost:11434", "host.docker.internal") == \
            "http://host.docker.internal:11434"

    def test_https_preserved(self):
        assert _rewrite_url("https://localhost:11434", "forge-ollama-proxy") == \
            "https://forge-ollama-proxy:11434"

    def test_query_params_preserved(self):
        assert _rewrite_url("http://localhost:3000/api?token=abc", "forge-forgejo") == \
            "http://forge-forgejo:3000/api?token=abc"


class TestInternalForgejoUrl:
    def test_localhost(self):
        assert _internal_forgejo_url("http://localhost:3000") == "http://forge-forgejo:3000"

    def test_lan_hostname_with_path(self):
        # ROOT_URL set to a LAN host must still resolve to the in-network container.
        assert _internal_forgejo_url("http://tesseract:3000/alice/widgets.git") == \
            "http://forge-forgejo:3000/alice/widgets.git"

    def test_127_with_path(self):
        assert _internal_forgejo_url("http://127.0.0.1:3000/x") == \
            "http://forge-forgejo:3000/x"

    def test_forces_internal_port_and_preserves_scheme(self):
        assert _internal_forgejo_url("https://example.com:8443/owner/repo.git") == \
            "https://forge-forgejo:3000/owner/repo.git"


class TestClaudeCredentialsPath:
    def test_returns_path_when_exists(self, tmp_path, monkeypatch):
        cred_file = tmp_path / ".claude" / ".credentials.json"
        cred_file.parent.mkdir()
        cred_file.write_text('{"claudeAiOauth": {}}')
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        assert _claude_credentials_path() == cred_file

    def test_raises_when_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        with pytest.raises(RuntimeError, match="credentials not found"):
            _claude_credentials_path()

    def test_prefers_saved_state(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "cc_forge.agents._forge_claude_state_dir", lambda: tmp_path
        )
        saved = tmp_path / ".credentials.json"
        saved.write_text('{"saved": true}')
        assert _claude_credentials_path() == saved


class TestCopyClaudeConfig:
    """Tests for _copy_claude_config tar injection."""

    def _capture_container(self):
        """Return a mock container that captures put_archive calls."""
        container = MagicMock()
        container.captured_bufs = []

        def capture_put_archive(path, buf):
            container.captured_bufs.append((path, buf))

        container.put_archive = capture_put_archive
        return container

    def _get_tar_members(self, container) -> dict[str, tarfile.TarInfo]:
        """Extract tar members from the captured put_archive call."""
        assert container.captured_bufs, "put_archive was never called"
        _, buf = container.captured_bufs[0]
        return _inspect_tar(buf)

    def _get_tar_content(self, container, name: str) -> bytes:
        """Extract file content from the captured tar."""
        _, buf = container.captured_bufs[0]
        buf.seek(0)
        with tarfile.open(fileobj=buf, mode="r") as tar:
            f = tar.extractfile(name)
            assert f is not None, f"{name} not extractable"
            return f.read()

    def test_api_key_mode_skips_credentials(self, tmp_path):
        config = _make_config(agent_api_key="sk-test", compose_file=str(tmp_path / "docker-compose.yml"))
        container = self._capture_container()

        _copy_claude_config(container, config)

        members = self._get_tar_members(container)
        assert ".claude/.credentials.json" not in members

    def test_first_run_injects_host_credentials(self, tmp_path, monkeypatch):
        monkeypatch.setattr("cc_forge.agents._forge_claude_state_dir", lambda: tmp_path / "nonexistent")
        host_creds = tmp_path / ".claude" / ".credentials.json"
        host_creds.parent.mkdir(parents=True)
        host_creds.write_bytes(b'{"host": true}')
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

        config = _make_config(compose_file=str(tmp_path / "docker-compose.yml"))
        container = self._capture_container()

        _copy_claude_config(container, config)

        content = self._get_tar_content(container, ".claude/.credentials.json")
        assert content == b'{"host": true}'

    def test_first_run_injects_minimal_claude_json(self, tmp_path, monkeypatch):
        monkeypatch.setattr("cc_forge.agents._forge_claude_state_dir", lambda: tmp_path / "nonexistent")
        host_creds = tmp_path / ".claude" / ".credentials.json"
        host_creds.parent.mkdir(parents=True)
        host_creds.write_bytes(b'{"host": true}')
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

        config = _make_config(compose_file=str(tmp_path / "docker-compose.yml"))
        container = self._capture_container()

        _copy_claude_config(container, config)

        content = self._get_tar_content(container, ".claude.json")
        assert b"hasCompletedOnboarding" in content

    def test_saved_state_injected_as_baseline(self, tmp_path, monkeypatch):
        state_dir = tmp_path / "state"
        state_dir.mkdir()
        (state_dir / ".credentials.json").write_bytes(b'{"saved": true}')
        (state_dir / "settings.json").write_bytes(b'{"setting": 1}')
        subdir = state_dir / "projects"
        subdir.mkdir()
        (subdir / "config.json").write_bytes(b'{"project": 1}')
        monkeypatch.setattr("cc_forge.agents._forge_claude_state_dir", lambda: state_dir)

        config = _make_config(compose_file=str(tmp_path / "docker-compose.yml"))
        container = self._capture_container()

        _copy_claude_config(container, config)

        members = self._get_tar_members(container)
        assert ".claude/settings.json" in members
        assert ".claude/projects" in members
        assert ".claude/projects/config.json" in members

    def test_saved_credentials_preferred_over_host(self, tmp_path, monkeypatch):
        state_dir = tmp_path / "state"
        state_dir.mkdir()
        (state_dir / ".credentials.json").write_bytes(b'{"saved": true}')

        host_creds = tmp_path / ".claude" / ".credentials.json"
        host_creds.parent.mkdir(parents=True)
        host_creds.write_bytes(b'{"host": true}')

        monkeypatch.setattr("cc_forge.agents._forge_claude_state_dir", lambda: state_dir)
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

        config = _make_config(compose_file=str(tmp_path / "docker-compose.yml"))
        container = self._capture_container()

        _copy_claude_config(container, config)

        content = self._get_tar_content(container, ".claude/.credentials.json")
        assert content == b'{"saved": true}'

    def test_permissions_and_ownership(self, tmp_path, monkeypatch):
        host_creds = tmp_path / ".claude" / ".credentials.json"
        host_creds.parent.mkdir(parents=True)
        host_creds.write_bytes(b'{"creds": true}')
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        monkeypatch.setattr("cc_forge.agents._forge_claude_state_dir", lambda: tmp_path / "nonexistent")

        config = _make_config(compose_file=str(tmp_path / "docker-compose.yml"))
        container = self._capture_container()

        _copy_claude_config(container, config)

        members = self._get_tar_members(container)
        creds = members[".claude/.credentials.json"]
        assert creds.mode == 0o600
        assert creds.uid == AGENT_UID
        assert creds.gid == AGENT_UID

        claude_dir = members[".claude"]
        assert claude_dir.mode == 0o755
        assert claude_dir.uid == AGENT_UID

    def test_agent_instructions_injected_for_all_harnesses(self, tmp_path):
        docker_dir = tmp_path / "docker"
        docker_dir.mkdir()
        (docker_dir / "AGENTS.md").write_bytes(b"# Agent instructions")
        commands_dir = docker_dir / "commands"
        commands_dir.mkdir()
        (commands_dir / "self-review.md").write_bytes(b"# self review")
        (commands_dir / "complexity-audit.md").write_bytes(b"# complexity audit")

        config = _make_config(compose_file=str(docker_dir / "docker-compose.yml"))
        container = self._capture_container()

        from cc_forge.docker import _inject_agent_instructions
        _inject_agent_instructions(container, config)

        # Claude reads ~/.claude/CLAUDE.md; the canonical AGENTS.md lives in home;
        # aider is pointed at it via ~/.aider.conf.yml.
        assert self._get_tar_content(container, ".claude/CLAUDE.md") == b"# Agent instructions"
        assert self._get_tar_content(container, "AGENTS.md") == b"# Agent instructions"
        assert b"/home/agent/AGENTS.md" in self._get_tar_content(container, ".aider.conf.yml")
        # every command file lands in ~/.claude/commands/ for command-capable harnesses
        assert self._get_tar_content(container, ".claude/commands/self-review.md") == b"# self review"
        assert self._get_tar_content(container, ".claude/commands/complexity-audit.md") == b"# complexity audit"


class TestInjectGitCredentials:
    """Tests for _inject_git_credentials tar injection."""

    def _capture_container(self):
        container = MagicMock()
        container.captured_bufs = []

        def capture_put_archive(path, buf):
            container.captured_bufs.append((path, buf))

        container.put_archive = capture_put_archive
        return container

    def test_injects_credentials_file(self):
        config = _make_config(forgejo_url="http://localhost:3000", forgejo_token="tok123")
        container = self._capture_container()

        _inject_git_credentials(container, config)

        assert container.captured_bufs, "put_archive was never called"
        _, buf = container.captured_bufs[0]
        members = _inspect_tar(buf)
        assert ".git-credentials" in members
        assert members[".git-credentials"].mode == 0o600
        assert members[".git-credentials"].uid == AGENT_UID

    def test_credential_format(self):
        config = _make_config(forgejo_url="http://localhost:3000", forgejo_token="tok123")
        container = self._capture_container()

        _inject_git_credentials(container, config)

        _, buf = container.captured_bufs[0]
        buf.seek(0)
        with tarfile.open(fileobj=buf, mode="r") as tar:
            content = tar.extractfile(".git-credentials").read().decode()
        assert "forge-agent:tok123@forge-forgejo:3000" in content

    def test_credential_format_strips_path(self):
        # A Forgejo URL with a path must not leak the path into the host segment.
        config = _make_config(
            forgejo_url="http://localhost:3000/forgejo", forgejo_token="tok123"
        )
        container = self._capture_container()

        _inject_git_credentials(container, config)

        _, buf = container.captured_bufs[0]
        buf.seek(0)
        with tarfile.open(fileobj=buf, mode="r") as tar:
            content = tar.extractfile(".git-credentials").read().decode()
        assert content.strip() == "http://forge-agent:tok123@forge-forgejo:3000"

    def test_token_is_url_encoded(self):
        # Reserved chars in the token must be percent-encoded, not embedded raw.
        config = _make_config(
            forgejo_url="http://localhost:3000", forgejo_token="ab/cd@ef:gh"
        )
        container = self._capture_container()

        _inject_git_credentials(container, config)

        _, buf = container.captured_bufs[0]
        buf.seek(0)
        with tarfile.open(fileobj=buf, mode="r") as tar:
            content = tar.extractfile(".git-credentials").read().decode()
        assert "forge-agent:ab%2Fcd%40ef%3Agh@forge-forgejo:3000" in content

    def test_skips_when_no_token(self):
        config = _make_config(forgejo_token="")
        container = self._capture_container()

        _inject_git_credentials(container, config)

        assert not container.captured_bufs


class TestInjectShimCredentials:
    """Tests for _inject_shim_credentials — the file the gh shim sources."""

    CREDS_PATH = ".config/forge-shim/credentials"

    def _capture_container(self):
        container = MagicMock()
        container.captured_bufs = []

        def capture_put_archive(path, buf):
            container.captured_bufs.append((path, buf))

        container.put_archive = capture_put_archive
        return container

    def _read_creds(self, container):
        assert container.captured_bufs, "put_archive was never called"
        _, buf = container.captured_bufs[0]
        buf.seek(0)
        with tarfile.open(fileobj=buf, mode="r") as tar:
            return tar.extractfile(self.CREDS_PATH).read().decode()

    def test_writes_credentials_file_with_all_keys(self):
        config = _make_config(
            forgejo_token="ft", github_token="gt",
            github_repo="gr/repo", github_owner="go",
        )
        container = self._capture_container()
        _inject_shim_credentials(container, config)

        _, buf = container.captured_bufs[0]
        members = _inspect_tar(buf)
        assert self.CREDS_PATH in members
        assert members[self.CREDS_PATH].mode == 0o600
        assert members[self.CREDS_PATH].uid == AGENT_UID

        content = self._read_creds(container)
        for key in ("FORGEJO_URL", "FORGEJO_TOKEN", "FORGE_GITHUB_TOKEN",
                    "FORGE_GITHUB_REPO", "FORGE_GITHUB_OWNER"):
            assert f"{key}=" in content

    def test_rewrites_forgejo_url_to_container_hostname(self):
        config = _make_config(
            forgejo_url="http://localhost:3000", forgejo_token="t",
        )
        container = self._capture_container()
        _inject_shim_credentials(container, config)
        assert "forge-forgejo:3000" in self._read_creds(container)
        assert "localhost" not in self._read_creds(container)

    def test_quotes_values_safely_for_shell_sourcing(self):
        """Values with shell metacharacters must round-trip through bash sourcing."""
        import subprocess
        tricky_token = "ab cd$ef'gh\"ij;kl"
        config = _make_config(forgejo_token=tricky_token)
        container = self._capture_container()
        _inject_shim_credentials(container, config)
        content = self._read_creds(container)
        # Source the content and echo back the token.
        result = subprocess.run(
            ["bash", "-c",
             "set -a; . /dev/stdin; set +a; printf '%s' \"$FORGEJO_TOKEN\""],
            input=content, capture_output=True, text=True,
        )
        assert result.returncode == 0, result.stderr
        assert result.stdout == tricky_token

    def test_writes_only_set_keys(self):
        # GitHub config absent → only Forgejo lines.
        config = _make_config(forgejo_token="t")  # no github_*
        container = self._capture_container()
        _inject_shim_credentials(container, config)
        content = self._read_creds(container)
        assert "FORGEJO_TOKEN=" in content
        assert "FORGE_GITHUB_TOKEN=" not in content
        assert "FORGE_GITHUB_REPO=" not in content
        assert "FORGE_GITHUB_OWNER=" not in content

    def test_skips_when_nothing_to_write(self):
        # No tokens, no urls → no file.
        config = _make_config(forgejo_token="", forgejo_url="")
        container = self._capture_container()
        _inject_shim_credentials(container, config)
        assert not container.captured_bufs

    def test_path_constant_matches_shim_path(self):
        # The Python constant docker.py uses must match the path the shim sources.
        # If either side moves, this test breaks loudly.
        assert SHIM_CREDENTIALS_PATH == "/home/agent/.config/forge-shim/credentials"
        # And the relative tar path is consistent with the absolute one.
        # /home/agent + /.config/... — the tar is rooted at /home/agent.
        assert SHIM_CREDENTIALS_PATH.endswith("/" + self.CREDS_PATH)


class TestRunAgentContainer:
    """Tests for run_agent_container configuration."""

    def _run(self, passthrough=False, agent="claude", **config_kwargs):
        config = _make_config(**config_kwargs)
        adapter = REGISTRY[agent]
        client = MagicMock()
        client.images.get.return_value = True
        container = MagicMock()
        container.id = "test-container-id"
        # Capture the create call
        client.containers.create.return_value = container

        with patch("cc_forge.docker._docker_client", return_value=client), \
                patch("cc_forge.agents._copy_claude_config"), \
                patch("cc_forge.docker._inject_agent_instructions"):
            from cc_forge.docker import run_agent_container
            result = run_agent_container(
                config,
                repo_url="http://localhost:3000/user/repo.git",
                branch="main",
                repo_name="repo",
                agent=agent,
                adapter=adapter,
                passthrough=passthrough,
            )
        return client, container, result

    def test_token_not_in_env_vars(self):
        client, container, _ = self._run(
            github_token="g", github_repo="o/r", github_owner="o",
        )
        create_kwargs = client.containers.create.call_args
        env = create_kwargs.kwargs["environment"]
        # All secrets/identifiers must reach the shim via the credentials file,
        # never as container env vars (visible to docker inspect).
        for forbidden in (
            "FORGEJO_URL", "FORGEJO_TOKEN",
            "FORGE_GITHUB_TOKEN", "FORGE_GITHUB_REPO", "FORGE_GITHUB_OWNER",
        ):
            assert forbidden not in env

    def test_resource_limits_applied(self):
        client, _, _ = self._run(agent_mem_limit="2g", agent_pids_limit=1024)
        create_kwargs = client.containers.create.call_args
        assert create_kwargs.kwargs["mem_limit"] == "2g"
        assert create_kwargs.kwargs["pids_limit"] == 1024

    def test_host_gateway_present_for_ollama(self):
        client, _, _ = self._run(passthrough=False)
        create_kwargs = client.containers.create.call_args
        extra_hosts = create_kwargs.kwargs["extra_hosts"]
        assert extra_hosts == {"host.docker.internal": "host-gateway"}

    def test_host_gateway_absent_for_claude_passthrough(self):
        client, _, _ = self._run(passthrough=True)
        create_kwargs = client.containers.create.call_args
        assert create_kwargs.kwargs["extra_hosts"] is None

    def test_host_gateway_absent_for_remote_ollama(self):
        # Ollama on a non-local host needs no gateway mapping.
        client, _, _ = self._run(ollama_cpu_url="http://ollama.internal:11434")
        create_kwargs = client.containers.create.call_args
        assert create_kwargs.kwargs["extra_hosts"] is None

    def test_git_credentials_injected(self):
        _, container, _ = self._run()
        # put_archive should be called for git credentials
        container.put_archive.assert_called()

    def test_agent_instructions_injected_for_non_passthrough(self):
        # The instructions must reach every harness, not just passthrough.
        config = _make_config()
        adapter = REGISTRY["claude"]
        client = MagicMock()
        client.images.get.return_value = True
        client.containers.create.return_value = MagicMock(id="x")
        with patch("cc_forge.docker._docker_client", return_value=client), \
                patch("cc_forge.docker._inject_agent_instructions") as inject:
            from cc_forge.docker import run_agent_container
            run_agent_container(
                config, repo_url="http://localhost:3000/u/r.git",
                branch="main", repo_name="repo", agent="claude",
                adapter=adapter, passthrough=False,
            )
        inject.assert_called_once()

    def test_instructions_injected_after_adapter_state_in_passthrough(self):
        # Canonical instructions must win over restored (possibly stale) state.
        config = _make_config()
        adapter = REGISTRY["claude"]
        client = MagicMock()
        client.images.get.return_value = True
        client.containers.create.return_value = MagicMock(id="x")
        manager = MagicMock()
        with patch("cc_forge.docker._docker_client", return_value=client), \
                patch("cc_forge.agents._copy_claude_config", manager.copy), \
                patch("cc_forge.docker._inject_agent_instructions", manager.inject):
            from cc_forge.docker import run_agent_container
            run_agent_container(
                config, repo_url="http://localhost:3000/u/r.git",
                branch="main", repo_name="repo", agent="claude",
                adapter=adapter, passthrough=True,
            )
        order = [c[0] for c in manager.mock_calls]
        assert order.index("copy") < order.index("inject")


class TestSaveClaudeCredentials:
    """Tests for _save_claude_credentials state extraction."""

    def _mock_container(self, claude_files: dict[str, bytes], claude_json: bytes | None = None):
        """Build a mock container with get_archive returning synthetic tars."""
        container = MagicMock()

        def get_archive(path):
            if ".claude/." in path:
                # Wrap files under .claude/ prefix (Docker get_archive behavior)
                wrapped = {f".claude/{k}": v for k, v in claude_files.items()}
                tar_buf = _make_tar(wrapped)
                return iter([tar_buf.read()]), {}
            if ".claude.json" in path:
                if claude_json is None:
                    import docker.errors
                    raise docker.errors.APIError("not found")
                tar_buf = _make_tar({".claude.json": claude_json})
                return iter([tar_buf.read()]), {}
            import docker.errors
            raise docker.errors.APIError("not found")

        container.get_archive = get_archive
        return container

    def test_saves_state_to_disk(self, tmp_path, monkeypatch):
        state_dir = tmp_path / "claude-state"
        monkeypatch.setattr("cc_forge.agents._forge_claude_state_dir", lambda: state_dir)

        container = self._mock_container(
            {".credentials.json": b'{"creds": true}', "settings.json": b'{"s": 1}'}
        )
        client = MagicMock()
        client.containers.get.return_value = container
        monkeypatch.setattr("cc_forge.agents._docker_client", lambda: client)

        _save_claude_credentials("test-id")

        assert (state_dir / ".credentials.json").read_bytes() == b'{"creds": true}'
        assert (state_dir / "settings.json").read_bytes() == b'{"s": 1}'

    def test_creates_state_dir_on_first_run(self, tmp_path, monkeypatch):
        state_dir = tmp_path / "deep" / "nested" / "claude-state"
        monkeypatch.setattr("cc_forge.agents._forge_claude_state_dir", lambda: state_dir)

        container = self._mock_container(
            {".credentials.json": b'{"creds": true}'},
            claude_json=b'{"hasCompletedOnboarding": true}',
        )
        client = MagicMock()
        client.containers.get.return_value = container
        monkeypatch.setattr("cc_forge.agents._docker_client", lambda: client)

        assert not state_dir.exists()
        _save_claude_credentials("test-id")

        assert state_dir.is_dir()
        assert (state_dir / ".credentials.json").exists()
        assert (state_dir / ".claude.json").read_bytes() == b'{"hasCompletedOnboarding": true}'

    def test_filters_skip_patterns(self, tmp_path, monkeypatch):
        state_dir = tmp_path / "claude-state"
        monkeypatch.setattr("cc_forge.agents._forge_claude_state_dir", lambda: state_dir)

        container = self._mock_container({
            ".credentials.json": b'{"creds": true}',
            "debug/log.txt": b"debug data",
            "session-env/env.json": b"{}",
            "file-history/h.json": b"{}",
            "shell-snapshots/s.json": b"{}",
            "settings.json": b'{"keep": true}',
        })
        client = MagicMock()
        client.containers.get.return_value = container
        monkeypatch.setattr("cc_forge.agents._docker_client", lambda: client)

        _save_claude_credentials("test-id")

        assert (state_dir / "settings.json").exists()
        assert not (state_dir / "debug").exists()
        assert not (state_dir / "session-env").exists()
        assert not (state_dir / "file-history").exists()
        assert not (state_dir / "shell-snapshots").exists()

    def test_filters_git_dirs(self, tmp_path, monkeypatch):
        state_dir = tmp_path / "claude-state"
        monkeypatch.setattr("cc_forge.agents._forge_claude_state_dir", lambda: state_dir)

        container = self._mock_container({
            ".credentials.json": b'{"creds": true}',
            ".git/config": b"git config",
            "projects/.git/HEAD": b"ref",
        })
        client = MagicMock()
        client.containers.get.return_value = container
        monkeypatch.setattr("cc_forge.agents._docker_client", lambda: client)

        _save_claude_credentials("test-id")

        assert not (state_dir / ".git").exists()

    def test_container_not_found_returns_silently(self, monkeypatch):
        from docker.errors import NotFound

        client = MagicMock()
        client.containers.get.side_effect = NotFound("gone")
        monkeypatch.setattr("cc_forge.agents._docker_client", lambda: client)

        _save_claude_credentials("missing-id")  # Should not raise
