"""
Orchestration framework adapters.

Each adapter wraps a specific orchestration framework (Goose, CrewAI, etc.)
and implements the Orchestrator protocol.
"""

from .goose import GooseOrchestrator

__all__ = ["GooseOrchestrator"]
