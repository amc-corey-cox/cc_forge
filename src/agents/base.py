"""Base agent class for the orchestration system.

All agents inherit from this base class which provides common functionality
for interacting with shared state and processing work items.
"""

from abc import ABC, abstractmethod
from typing import Any

from src.common.state import SharedState, WorkItem, WorkStatus


class BaseAgent(ABC):
    """Abstract base class for all agents.

    Agents are stateless processors that read from and write to shared state.
    Each agent has a specific role and processes work items accordingly.
    """

    def __init__(self, agent_id: str, state: SharedState):
        """Initialize the agent.

        Args:
            agent_id: Unique identifier for this agent instance.
            state: Shared state container for reading/writing work.
        """
        self.agent_id = agent_id
        self.state = state

    @property
    @abstractmethod
    def role(self) -> str:
        """Return the role/type of this agent."""
        pass

    @abstractmethod
    def can_process(self, item: WorkItem) -> bool:
        """Check if this agent can process the given work item.

        Args:
            item: The work item to check.

        Returns:
            True if this agent should process the item, False otherwise.
        """
        pass

    @abstractmethod
    def process(self, item: WorkItem) -> dict[str, Any]:
        """Process a work item and return results.

        Args:
            item: The work item to process.

        Returns:
            Dict containing the results of processing.
        """
        pass

    def run(self) -> list[dict[str, Any]]:
        """Run the agent on all processable items in state.

        Returns:
            List of results from processing each item.
        """
        results = []
        for item in self.state.work_items.values():
            if self.can_process(item):
                result = self.process(item)
                self.state.record_agent_output(self.agent_id, {
                    "work_item_id": item.id,
                    "result": result,
                })
                results.append(result)
        return results

    def log(self, message: str) -> None:
        """Log a message from this agent."""
        print(f"[{self.agent_id}] {message}")
