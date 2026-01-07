"""
Orchestrator factory - creates the appropriate orchestrator based on config.

This is the main entry point for getting an orchestrator instance.
"""

from typing import Any

from .base import BaseOrchestrator, Orchestrator, OrchestratorError
from .config import SUPPORTED_FRAMEWORKS, OrchestratorConfig


def get_available_frameworks() -> dict[str, str]:
    """Return dict of available frameworks and their descriptions."""
    return SUPPORTED_FRAMEWORKS.copy()


def create_orchestrator(
    config: OrchestratorConfig | None = None,
    framework: str | None = None,
    **kwargs: Any,
) -> Orchestrator:
    """
    Create an orchestrator instance based on configuration.

    Args:
        config: OrchestratorConfig instance. If None, loads from default sources.
        framework: Override the framework from config. Useful for testing.
        **kwargs: Additional arguments passed to the orchestrator constructor.

    Returns:
        An Orchestrator instance ready for use.

    Raises:
        OrchestratorError: If framework is not supported or initialization fails.

    Example:
        # Using default config (from env or cc_forge.toml)
        orchestrator = create_orchestrator()

        # Explicit framework
        orchestrator = create_orchestrator(framework="goose")

        # Full config
        config = OrchestratorConfig(framework="goose", model="llama3:8b")
        orchestrator = create_orchestrator(config)
    """
    # Load config if not provided
    if config is None:
        config = OrchestratorConfig.load()

    # Allow framework override
    framework_name = framework or config.framework

    # Validate
    errors = config.validate()
    if errors:
        raise OrchestratorError(f"Invalid configuration: {'; '.join(errors)}")

    # Create the appropriate orchestrator
    framework_config = {**config.to_dict(), **kwargs}

    if framework_name == "goose":
        from .adapters.goose import GooseOrchestrator

        return GooseOrchestrator(framework_config)

    elif framework_name == "crewai":
        # Placeholder for future CrewAI adapter
        raise OrchestratorError(
            "CrewAI adapter not yet implemented. "
            "Contributions welcome! See src/orchestration/adapters/"
        )

    elif framework_name == "langgraph":
        # Placeholder for future LangGraph adapter
        raise OrchestratorError(
            "LangGraph adapter not yet implemented. "
            "Contributions welcome! See src/orchestration/adapters/"
        )

    elif framework_name == "autogen":
        # Placeholder for future AutoGen adapter
        raise OrchestratorError(
            "AutoGen adapter not yet implemented. "
            "Contributions welcome! See src/orchestration/adapters/"
        )

    else:
        raise OrchestratorError(
            f"Unknown framework: {framework_name}. "
            f"Supported: {list(SUPPORTED_FRAMEWORKS.keys())}"
        )


async def create_and_initialize(
    config: OrchestratorConfig | None = None,
    **kwargs: Any,
) -> Orchestrator:
    """
    Create and initialize an orchestrator in one step.

    Convenience function for common use case.
    """
    orchestrator = create_orchestrator(config, **kwargs)
    await orchestrator.initialize()
    return orchestrator
