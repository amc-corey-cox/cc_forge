"""Configuration loading for CC Forge.

Settings are resolved in order: env vars > .env file > ~/.config/forge/config.env > defaults.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

_DEFAULTS = {
    "FORGE_FORGEJO_URL": "http://localhost:3000",
    "FORGE_FORGEJO_TOKEN": "",
    "FORGE_OLLAMA_CPU_URL": "http://localhost:11434",
    "FORGE_OLLAMA_GPU_URL": "http://localhost:11435",
    "FORGE_AGENT_IMAGE": "cc-forge-agent:latest",
    "FORGE_COMPOSE_FILE": str(
        Path(__file__).resolve().parent.parent.parent / "docker" / "docker-compose.yml"
    ),
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
    """Resolve a config value: env var > .env files > default."""
    val = os.environ.get(key)
    if val is not None:
        return val
    for env_file in _ENV_FILES:
        file_env = _load_env_file(env_file)
        if key in file_env:
            return file_env[key]
    return _DEFAULTS.get(key, "")


@dataclass(frozen=True)
class ForgeConfig:
    forgejo_url: str = field(default_factory=lambda: _resolve("FORGE_FORGEJO_URL"))
    forgejo_token: str = field(default_factory=lambda: _resolve("FORGE_FORGEJO_TOKEN"))
    ollama_cpu_url: str = field(default_factory=lambda: _resolve("FORGE_OLLAMA_CPU_URL"))
    ollama_gpu_url: str = field(default_factory=lambda: _resolve("FORGE_OLLAMA_GPU_URL"))
    agent_image: str = field(default_factory=lambda: _resolve("FORGE_AGENT_IMAGE"))
    compose_file: str = field(default_factory=lambda: _resolve("FORGE_COMPOSE_FILE"))


def load_config() -> ForgeConfig:
    return ForgeConfig()
