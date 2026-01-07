"""Shared state management for agent orchestration.

This module provides a simple state container that agents can read from
and write to, enabling them to pass work to each other.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class WorkStatus(Enum):
    """Status of a work item in the pipeline."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    NEEDS_REVISION = "needs_revision"
    APPROVED = "approved"


@dataclass
class WorkItem:
    """A unit of work that flows through the agent pipeline."""
    id: str
    content: str
    status: WorkStatus = WorkStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)
    history: list[dict[str, Any]] = field(default_factory=list)

    def update_status(self, new_status: WorkStatus, agent_id: str, note: str = "") -> None:
        """Update status and record in history."""
        self.history.append({
            "timestamp": datetime.now().isoformat(),
            "agent": agent_id,
            "from_status": self.status.value,
            "to_status": new_status.value,
            "note": note,
        })
        self.status = new_status
        self.updated_at = datetime.now()


@dataclass
class SharedState:
    """Container for state shared between agents.

    This is a simple in-memory state store. In production, this could be
    backed by a database or message queue.
    """
    work_items: dict[str, WorkItem] = field(default_factory=dict)
    agent_outputs: dict[str, list[dict[str, Any]]] = field(default_factory=dict)

    def add_work_item(self, item: WorkItem) -> None:
        """Add a new work item to the state."""
        self.work_items[item.id] = item

    def get_work_item(self, item_id: str) -> WorkItem | None:
        """Retrieve a work item by ID."""
        return self.work_items.get(item_id)

    def get_items_by_status(self, status: WorkStatus) -> list[WorkItem]:
        """Get all work items with a given status."""
        return [item for item in self.work_items.values() if item.status == status]

    def record_agent_output(self, agent_id: str, output: dict[str, Any]) -> None:
        """Record output from an agent for auditing."""
        if agent_id not in self.agent_outputs:
            self.agent_outputs[agent_id] = []
        self.agent_outputs[agent_id].append({
            "timestamp": datetime.now().isoformat(),
            **output,
        })
