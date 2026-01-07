"""
Base abstractions for agent orchestration.

This module defines the protocol that all orchestration frameworks must implement.
By coding to these interfaces, CC Forge can swap frameworks without rewriting
agent logic.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol, runtime_checkable


class AgentRole(Enum):
    """Standard agent roles matching CC Forge team structure."""

    DEV = "dev"
    TEST = "test"
    RED_TEAM = "red_team"
    BLUE_TEAM = "blue_team"
    TRIAGE = "triage"
    CUSTOM = "custom"


@dataclass
class AgentConfig:
    """Configuration for a single agent."""

    name: str
    role: AgentRole
    system_prompt: str
    model: str | None = None  # None = use orchestrator default
    tools: list[str] = field(default_factory=list)
    max_iterations: int = 10
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TeamConfig:
    """Configuration for a team of agents."""

    name: str
    agents: list[AgentConfig]
    workflow: str = "sequential"  # sequential, parallel, hierarchical
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResult:
    """Result from an agent or team execution."""

    success: bool
    output: Any
    agent_name: str
    iterations: int = 0
    token_usage: dict[str, int] = field(default_factory=dict)
    logs: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class OrchestratorError(Exception):
    """Base exception for orchestration errors."""

    pass


@runtime_checkable
class Orchestrator(Protocol):
    """
    Protocol defining what any orchestration framework must implement.

    This is the core abstraction that allows swapping between Goose, CrewAI,
    LangGraph, or any future framework without changing agent logic.
    """

    @property
    def name(self) -> str:
        """Human-readable name of the orchestration framework."""
        ...

    @property
    def version(self) -> str:
        """Version of the underlying framework."""
        ...

    async def initialize(self) -> None:
        """
        Initialize the orchestrator and verify dependencies.

        Raises:
            OrchestratorError: If initialization fails (missing deps, bad config)
        """
        ...

    async def shutdown(self) -> None:
        """Clean up resources when orchestrator is no longer needed."""
        ...

    async def run_agent(
        self,
        config: AgentConfig,
        task: str,
        context: dict[str, Any] | None = None,
    ) -> AgentResult:
        """
        Run a single agent on a task.

        Args:
            config: Agent configuration
            task: The task/prompt for the agent
            context: Optional context data for the agent

        Returns:
            AgentResult with output and metadata
        """
        ...

    async def run_team(
        self,
        config: TeamConfig,
        task: str,
        context: dict[str, Any] | None = None,
    ) -> list[AgentResult]:
        """
        Run a team of agents on a task.

        Args:
            config: Team configuration with agent definitions
            task: The task/prompt for the team
            context: Optional shared context

        Returns:
            List of AgentResults from each agent
        """
        ...

    def get_available_models(self) -> list[str]:
        """Return list of models available through this orchestrator."""
        ...

    def get_available_tools(self) -> list[str]:
        """Return list of tools/capabilities available."""
        ...


class BaseOrchestrator(ABC):
    """
    Abstract base class providing common orchestrator functionality.

    Frameworks should inherit from this rather than implementing Orchestrator
    directly to get default implementations and utility methods.
    """

    def __init__(self, config: dict[str, Any] | None = None):
        self._config = config or {}
        self._initialized = False

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of the orchestration framework."""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """Version of the underlying framework."""
        pass

    async def initialize(self) -> None:
        """Initialize with common setup logic."""
        if self._initialized:
            return
        await self._do_initialize()
        self._initialized = True

    @abstractmethod
    async def _do_initialize(self) -> None:
        """Framework-specific initialization."""
        pass

    async def shutdown(self) -> None:
        """Shutdown with common cleanup logic."""
        if not self._initialized:
            return
        await self._do_shutdown()
        self._initialized = False

    async def _do_shutdown(self) -> None:
        """Framework-specific cleanup. Override if needed."""
        pass

    @abstractmethod
    async def run_agent(
        self,
        config: AgentConfig,
        task: str,
        context: dict[str, Any] | None = None,
    ) -> AgentResult:
        pass

    @abstractmethod
    async def run_team(
        self,
        config: TeamConfig,
        task: str,
        context: dict[str, Any] | None = None,
    ) -> list[AgentResult]:
        pass

    @abstractmethod
    def get_available_models(self) -> list[str]:
        pass

    @abstractmethod
    def get_available_tools(self) -> list[str]:
        pass

    def _log(self, message: str) -> None:
        """Simple logging helper. Override for custom logging."""
        print(f"[{self.name}] {message}")
