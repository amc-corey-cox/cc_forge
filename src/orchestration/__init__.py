"""
Orchestration module - pluggable AI agent framework abstraction.

This module provides a framework-agnostic interface for agent orchestration,
allowing CC Forge to swap between Goose, CrewAI, LangGraph, or other frameworks
as the ecosystem evolves.

Usage:
    from src.orchestration import create_orchestrator

    orchestrator = create_orchestrator()  # Uses config to select framework
    result = await orchestrator.run_agent(agent_config, task)
"""

from .base import (
    AgentConfig,
    AgentResult,
    Orchestrator,
    OrchestratorError,
    TeamConfig,
)
from .factory import create_orchestrator, get_available_frameworks

__all__ = [
    "AgentConfig",
    "AgentResult",
    "Orchestrator",
    "OrchestratorError",
    "TeamConfig",
    "create_orchestrator",
    "get_available_frameworks",
]
