"""Configuration loading for CC Forge.

Settings are resolved in order: env vars > .env file > ~/.config/forge/config.env > defaults.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

def _find_compose_file() -> str:
    """Search for docker-compose.yml in known locations."""
    candidates = [
        # Source checkout (editable install or running from repo)
        Path(__file__).resolve().parent.parent.parent / "docker" / "docker-compose.yml",
        # Current working directory
        Path.cwd() / "docker" / "docker-compose.yml",
        # User config directory
        Path.home() / ".config" / "forge" / "docker-compose.yml",
    ]
    for p in candidates:
        if p.is_file():
            return str(p)
    return ""


AGENT_MODEL_DEFAULT = "qwen3-coder-32k"

_DEFAULTS = {
    "FORGE_FORGEJO_URL": "http://localhost:3000",
    "FORGE_FORGEJO_TOKEN": "",
    "FORGE_OLLAMA_CPU_URL": "http://localhost:11434",
    "FORGE_OLLAMA_GPU_URL": "http://localhost:11435",
    "FORGE_AGENT_IMAGE": "cc-forge-agent:latest",
    "FORGE_AGENT_MODEL": AGENT_MODEL_DEFAULT,
    "FORGE_AGENT_API_KEY": "",
    "FORGE_COMPOSE_FILE": "",
    "FORGE_GITHUB_TOKEN": "",
    "FORGE_GITHUB_REPO": "",
    "FORGE_GITHUB_OWNER": "",
    "FORGE_AGENT_MEM_LIMIT": "4g",
    "FORGE_AGENT_PIDS_LIMIT": "4096",
}

_ENV_FILES = [
    Path.cwd() / ".env",
    Path.home() / ".config" / "forge" / "config.env",
]


def _load_env_file(path: Path) -> dict[str, str]:
    """Parse a simple KEY=VALUE env file, ignoring comments and blanks."""
    env: dict[str, str] = {}
    if not path.is_file():
        return env
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        env[key.strip()] = value.strip().strip("\"'")
    return env


def _resolve(key: str) -> str:
    """Resolve a config value: env var > .env files > default.

    Empty strings are treated as unset so that auto-discovery still works
    (e.g. FORGE_COMPOSE_FILE="" won't suppress _find_compose_file()).
    """
    val = os.environ.get(key)
    if val is not None and val != "":
        return val
    for env_file in _ENV_FILES:
        file_env = _load_env_file(env_file)
        if key in file_env and file_env[key] != "":
            return file_env[key]
    default = _DEFAULTS.get(key, "")
    if key == "FORGE_COMPOSE_FILE" and not default:
        return _find_compose_file()
    return default


def _resolve_with_fallback(new_key: str, old_key: str) -> str:
    """Resolve a renamed config key, trying the old name as fallback.

    Checks env vars and .env files for both the new and old key names,
    preferring the new name. Falls back to _DEFAULTS for the new key.
    """
    for key in (new_key, old_key):
        val = os.environ.get(key)
        if val is not None and val != "":
            return val
        for env_file in _ENV_FILES:
            file_env = _load_env_file(env_file)
            if key in file_env and file_env[key] != "":
                return file_env[key]
    return _DEFAULTS.get(new_key, _DEFAULTS.get(old_key, ""))


def _resolve_int(key: str) -> int:
    """Resolve an integer config value with an actionable error on bad input."""
    raw = _resolve(key)
    try:
        return int(raw)
    except ValueError:
        raise ValueError(f"{key} must be an integer, got {raw!r}")


@dataclass(frozen=True)
class ForgeConfig:
    forgejo_url: str = field(default_factory=lambda: _resolve("FORGE_FORGEJO_URL"))
    forgejo_token: str = field(default_factory=lambda: _resolve("FORGE_FORGEJO_TOKEN"))
    ollama_cpu_url: str = field(default_factory=lambda: _resolve("FORGE_OLLAMA_CPU_URL"))
    ollama_gpu_url: str = field(default_factory=lambda: _resolve("FORGE_OLLAMA_GPU_URL"))
    agent_image: str = field(default_factory=lambda: _resolve("FORGE_AGENT_IMAGE"))
    agent_model: str = field(
        default_factory=lambda: _resolve_with_fallback("FORGE_AGENT_MODEL", "FORGE_CLAUDE_MODEL")
    )
    agent_api_key: str = field(
        default_factory=lambda: _resolve_with_fallback("FORGE_AGENT_API_KEY", "FORGE_CLAUDE_API_KEY")
        or os.environ.get("ANTHROPIC_API_KEY", "")
    )
    compose_file: str = field(default_factory=lambda: _resolve("FORGE_COMPOSE_FILE"))
    github_token: str = field(default_factory=lambda: _resolve("FORGE_GITHUB_TOKEN"))
    github_repo: str = field(default_factory=lambda: _resolve("FORGE_GITHUB_REPO"))
    github_owner: str = field(default_factory=lambda: _resolve("FORGE_GITHUB_OWNER"))
    agent_mem_limit: str = field(default_factory=lambda: _resolve("FORGE_AGENT_MEM_LIMIT"))
    agent_pids_limit: int = field(default_factory=lambda: _resolve_int("FORGE_AGENT_PIDS_LIMIT"))

    def resolve_github_repo(self, repo_name: str) -> str:
        """Resolve the GitHub 'owner/repo' destination, mirroring the gh-shim chain.

        FORGE_GITHUB_REPO (explicit owner/repo) > FORGE_GITHUB_OWNER + repo_name > error.
        """
        if self.github_repo:
            parts = self.github_repo.split("/")
            if len(parts) != 2 or not all(parts):
                raise ValueError(
                    f"FORGE_GITHUB_REPO must be 'owner/repo', got {self.github_repo!r}"
                )
            return self.github_repo
        if self.github_owner:
            return f"{self.github_owner}/{repo_name}"
        raise ValueError(
            "Cannot resolve GitHub repo: set FORGE_GITHUB_REPO or FORGE_GITHUB_OWNER."
        )


def load_config() -> ForgeConfig:
    return ForgeConfig()
