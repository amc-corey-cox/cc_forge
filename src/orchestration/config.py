"""
Orchestration configuration management.

Handles loading and validating orchestrator configuration from environment
variables and config files.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Try to import tomllib (Python 3.11+) or fall back to tomli
try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib  # type: ignore
    except ImportError:
        tomllib = None  # type: ignore


# Supported frameworks - add new ones here
SUPPORTED_FRAMEWORKS = {
    "goose": "Goose - Block's MCP-based agent framework",
    "crewai": "CrewAI - Role-based multi-agent collaboration (not yet implemented)",
    "langgraph": "LangGraph - Graph-based agent workflows (not yet implemented)",
    "autogen": "AutoGen - Microsoft's conversational agents (not yet implemented)",
}

DEFAULT_FRAMEWORK = "goose"


@dataclass
class OrchestratorConfig:
    """Configuration for the orchestration system."""

    # Framework selection
    framework: str = DEFAULT_FRAMEWORK

    # LLM provider settings
    provider: str = "ollama"
    model: str = "qwen2.5:14b"
    api_base: str | None = None
    api_key: str | None = None  # For cloud providers

    # Execution settings
    max_iterations: int = 10
    timeout_seconds: int = 300
    retry_attempts: int = 3

    # Logging
    log_level: str = "INFO"
    log_agent_outputs: bool = True

    # Framework-specific settings
    framework_config: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_env(cls) -> "OrchestratorConfig":
        """Load configuration from environment variables."""
        return cls(
            framework=os.getenv("CC_ORCHESTRATOR", DEFAULT_FRAMEWORK).lower(),
            provider=os.getenv("CC_LLM_PROVIDER", "ollama"),
            model=os.getenv("CC_LLM_MODEL", "qwen2.5:14b"),
            api_base=os.getenv("CC_LLM_API_BASE"),
            api_key=os.getenv("CC_LLM_API_KEY"),
            max_iterations=int(os.getenv("CC_MAX_ITERATIONS", "10")),
            timeout_seconds=int(os.getenv("CC_TIMEOUT", "300")),
            log_level=os.getenv("CC_LOG_LEVEL", "INFO"),
        )

    @classmethod
    def from_file(cls, path: Path | str) -> "OrchestratorConfig":
        """Load configuration from a TOML file."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        if tomllib is None:
            raise ImportError(
                "TOML parsing requires Python 3.11+ or 'tomli' package. "
                "Install with: pip install tomli"
            )

        with open(path, "rb") as f:
            data = tomllib.load(f)

        orch_config = data.get("orchestration", {})
        llm_config = data.get("llm", {})

        return cls(
            framework=orch_config.get("framework", DEFAULT_FRAMEWORK),
            provider=llm_config.get("provider", "ollama"),
            model=llm_config.get("model", "qwen2.5:14b"),
            api_base=llm_config.get("api_base"),
            api_key=llm_config.get("api_key"),
            max_iterations=orch_config.get("max_iterations", 10),
            timeout_seconds=orch_config.get("timeout_seconds", 300),
            log_level=orch_config.get("log_level", "INFO"),
            framework_config=orch_config.get("framework_config", {}),
        )

    @classmethod
    def load(cls, config_path: Path | str | None = None) -> "OrchestratorConfig":
        """
        Load configuration with fallback priority:
        1. Explicit config file path
        2. cc_forge.toml in current directory
        3. Environment variables
        """
        # Try explicit path
        if config_path:
            return cls.from_file(config_path)

        # Try default config file
        default_config = Path("cc_forge.toml")
        if default_config.exists():
            return cls.from_file(default_config)

        # Fall back to environment
        return cls.from_env()

    def validate(self) -> list[str]:
        """Validate configuration, return list of errors."""
        errors = []

        if self.framework not in SUPPORTED_FRAMEWORKS:
            errors.append(
                f"Unknown framework '{self.framework}'. "
                f"Supported: {list(SUPPORTED_FRAMEWORKS.keys())}"
            )

        if self.max_iterations < 1:
            errors.append("max_iterations must be at least 1")

        if self.timeout_seconds < 1:
            errors.append("timeout_seconds must be at least 1")

        return errors

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for framework initialization."""
        return {
            "provider": self.provider,
            "model": self.model,
            "api_base": self.api_base,
            "api_key": self.api_key,
            "max_iterations": self.max_iterations,
            "timeout_seconds": self.timeout_seconds,
            **self.framework_config,
        }


def get_example_config() -> str:
    """Return example TOML configuration."""
    return '''# CC Forge Orchestration Configuration
# Copy to cc_forge.toml and customize

[orchestration]
# Framework: goose, crewai, langgraph, autogen
framework = "goose"

# Execution limits
max_iterations = 10
timeout_seconds = 300
log_level = "INFO"

[llm]
# Provider: ollama, openai, anthropic, azure
provider = "ollama"

# Model name (provider-specific)
model = "qwen2.5:14b"

# For cloud providers (leave empty for local)
# api_base = "https://api.openai.com/v1"
# api_key = "${OPENAI_API_KEY}"  # Use env var reference

[orchestration.framework_config]
# Framework-specific settings go here
# goose_config_path = "~/.config/goose"
'''
