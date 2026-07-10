"""Agent adapter interface and registry for CC Forge.

Each adapter encapsulates the command, environment, and state management
for a specific agent harness (Claude Code, Aider, etc.). Adding a new
harness is a new adapter class plus a REGISTRY entry.
"""

from __future__ import annotations

import io
import tarfile
from abc import ABC, abstractmethod
from pathlib import Path

import click

from cc_forge.config import ForgeConfig
from cc_forge.docker import (
    AGENT_UID,
    _add_tar_dir,
    _add_tar_file,
    _docker_client,
    _rewrite_url,
)


class AgentAdapter(ABC):
    """Interface that each agent harness must implement."""

    supports_passthrough: bool = False
    default_model: str = ""

    def _model(self, config: ForgeConfig) -> str:
        """Return the model to use: config value if explicitly set, else adapter default."""
        from cc_forge.config import AGENT_MODEL_DEFAULT
        if config.agent_model != AGENT_MODEL_DEFAULT or not self.default_model:
            return config.agent_model
        return self.default_model

    @abstractmethod
    def build_cmd(self, config: ForgeConfig, passthrough: bool) -> list[str]:
        """Build the shell command to launch the agent inside the container."""

    @abstractmethod
    def container_env(self, config: ForgeConfig, passthrough: bool) -> dict[str, str]:
        """Return environment variables for the agent container."""

    def inject_state(self, container, config: ForgeConfig, passthrough: bool) -> None:
        """Inject agent-specific state into the container before start."""

    def save_state(
        self, container_id: str, config: ForgeConfig, passthrough: bool
    ) -> None:
        """Save agent state from the container back to the host after session."""


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _ollama_environment(config: ForgeConfig) -> dict[str, str]:
    """Environment variables for local Ollama backend."""
    ollama_url = _rewrite_url(config.ollama_cpu_url, "host.docker.internal")
    return {
        "OLLAMA_HOST": ollama_url,
        "ANTHROPIC_AUTH_TOKEN": "ollama",
        "ANTHROPIC_BASE_URL": ollama_url,
        "DISABLE_PROMPT_CACHING": "true",
        "API_TIMEOUT_MS": "3600000",
        "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
        "CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS": "1",
        "MAX_THINKING_TOKENS": "0",
    }


# ---------------------------------------------------------------------------
# Claude adapter helpers
# ---------------------------------------------------------------------------


def _forge_claude_state_dir() -> Path:
    return Path.home() / ".config" / "forge" / "claude-state"


def _claude_credentials_path() -> Path:
    """Return the path to Claude OAuth credentials (saved state preferred, then host)."""
    for candidate in (
        _forge_claude_state_dir() / ".credentials.json",
        Path.home() / ".claude" / ".credentials.json",
    ):
        if candidate.is_symlink():
            raise RuntimeError(f"Refusing to use symlinked credentials: {candidate}")
        if candidate.is_file():
            return candidate
    raise RuntimeError(
        "Claude credentials not found.\n"
        "Either set FORGE_AGENT_API_KEY or run 'claude' locally to authenticate."
    )


def _claude_api_environment(config: ForgeConfig) -> dict[str, str]:
    """Environment variables for Claude API pass-through."""
    env = {
        # Override Dockerfile defaults that would route to Ollama
        "ANTHROPIC_BASE_URL": "",
        "ANTHROPIC_AUTH_TOKEN": "",
        # Container agent can't write to npm global; skip auto-update
        "CLAUDE_CODE_SKIP_UPDATE": "1",
    }
    if config.agent_api_key:
        env["ANTHROPIC_API_KEY"] = config.agent_api_key
    return env


def _copy_claude_config(container, config: ForgeConfig) -> None:
    """Copy Claude config into the container.

    When FORGE_AGENT_API_KEY is set, only injects onboarding bypass.
    Otherwise, also injects OAuth credentials from host or saved state.
    """
    need_credentials = not config.agent_api_key

    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        _add_tar_dir(tar, ".claude/")

        if need_credentials:
            cred_path = _claude_credentials_path()
            state_dir = _forge_claude_state_dir()

            # Inject saved state as baseline (skip credentials — we'll add fresh ones)
            if state_dir.is_dir():
                for path in state_dir.rglob("*"):
                    rel = path.relative_to(state_dir)
                    if rel.name == ".credentials.json":
                        continue
                    arc_name = f".claude/{rel}"
                    if path.is_dir():
                        _add_tar_dir(tar, arc_name + "/")
                    else:
                        _add_tar_file(tar, arc_name, path.read_bytes())

            # Inject credentials once (saved-preferred, host fallback)
            _add_tar_file(
                tar,
                ".claude/.credentials.json",
                cred_path.read_bytes(),
                mode=0o600,
            )

        # $HOME/.claude.json — onboarding bypass + saved state
        # hasCompletedOnboarding lives here (NOT in settings.json)
        saved_claude_json = _forge_claude_state_dir() / ".claude.json"
        if saved_claude_json.is_file():
            _add_tar_file(
                tar, ".claude.json", saved_claude_json.read_bytes(), mode=0o600
            )
        else:
            _add_tar_file(
                tar, ".claude.json", b'{"hasCompletedOnboarding":true}', mode=0o600
            )
    buf.seek(0)

    container.put_archive("/home/agent", buf)


def _save_claude_credentials(container_id: str) -> None:
    """Save full Claude state from container back to host for reuse."""
    import shutil
    import tempfile

    import docker.errors
    from docker.errors import NotFound

    client = _docker_client()
    state_dir = _forge_claude_state_dir()
    _SKIP_PATTERNS = {"debug", "session-env", "file-history", "shell-snapshots"}

    try:
        container = client.containers.get(container_id)
    except NotFound:
        return

    try:
        bits, _ = container.get_archive("/home/agent/.claude/.")
    except docker.errors.APIError:
        click.echo("Warning: could not read Claude state from container.", err=True)
        return

    buf = io.BytesIO()
    for chunk in bits:
        buf.write(chunk)
    buf.seek(0)

    state_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        dir=state_dir.parent, prefix="claude-state-tmp-"
    ) as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)
        with tarfile.open(fileobj=buf, mode="r") as tar:
            for member in tar.getmembers():
                parts = Path(member.name).parts
                if any(p in _SKIP_PATTERNS for p in parts):
                    continue
                if ".git" in parts:
                    continue
                tar.extract(member, tmp_dir, filter="data")

        extracted = tmp_dir / ".claude" if (tmp_dir / ".claude").exists() else tmp_dir
        if state_dir.exists():
            shutil.rmtree(state_dir)
        shutil.move(str(extracted), str(state_dir))

    state_dir.chmod(0o700)
    cred_file = state_dir / ".credentials.json"
    if cred_file.is_file():
        cred_file.chmod(0o600)

    # Also save ~/.claude.json (onboarding/account state)
    try:
        bits2, _ = container.get_archive("/home/agent/.claude.json")
    except docker.errors.APIError:
        return

    buf2 = io.BytesIO()
    for chunk in bits2:
        buf2.write(chunk)
    buf2.seek(0)
    with tarfile.open(fileobj=buf2, mode="r") as tar:
        for member in tar.getmembers():
            if member.isreg():
                f = tar.extractfile(member)
                if f:
                    state_dir.mkdir(parents=True, exist_ok=True)
                    target = state_dir / ".claude.json"
                    tmp = state_dir / ".claude.json.tmp"
                    tmp.write_bytes(f.read())
                    tmp.chmod(0o600)
                    tmp.replace(target)
                break


# ---------------------------------------------------------------------------
# Adapters
# ---------------------------------------------------------------------------


class ClaudeAdapter(AgentAdapter):
    """Adapter for Claude Code agent."""

    supports_passthrough = True
    default_model = "qwen3-coder-32k"

    def build_cmd(self, config: ForgeConfig, passthrough: bool) -> list[str]:
        cmd = ["claude", "--dangerously-skip-permissions"]
        if not passthrough:
            cmd += ["--model", self._model(config)]
        return cmd

    def container_env(self, config: ForgeConfig, passthrough: bool) -> dict[str, str]:
        if passthrough:
            return _claude_api_environment(config)
        return _ollama_environment(config)

    def inject_state(
        self, container, config: ForgeConfig, passthrough: bool
    ) -> None:
        if passthrough:
            _copy_claude_config(container, config)

    def save_state(
        self, container_id: str, config: ForgeConfig, passthrough: bool
    ) -> None:
        if passthrough and not config.agent_api_key:
            try:
                _save_claude_credentials(container_id)
            except Exception as e:
                click.echo(f"Warning: failed to save Claude state: {e}", err=True)


class AiderAdapter(AgentAdapter):
    """Adapter for Aider agent."""

    supports_passthrough = False
    default_model = "ollama/qwen3-coder-32k"

    def build_cmd(self, config: ForgeConfig, passthrough: bool) -> list[str]:
        return ["aider", "--model", self._model(config)]

    def container_env(self, config: ForgeConfig, passthrough: bool) -> dict[str, str]:
        return _ollama_environment(config)


REGISTRY: dict[str, AgentAdapter] = {
    "claude": ClaudeAdapter(),
    "aider": AiderAdapter(),
}
