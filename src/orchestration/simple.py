"""Simple orchestrator that chains two agents in a feedback loop.

This module demonstrates:
1. Agent chaining: Writer -> Reviewer -> Writer -> ...
2. State management: Shared state tracks work items through the pipeline
3. Termination: The loop ends when work is approved or max iterations reached
"""

from typing import Any

from src.agents.base import BaseAgent
from src.agents.writer import WriterAgent
from src.agents.reviewer import ReviewerAgent
from src.common.state import SharedState, WorkItem, WorkStatus


class SimpleOrchestrator:
    """Orchestrates a feedback loop between Writer and Reviewer agents.

    The orchestrator manages the flow of work:
    1. Writer creates initial content
    2. Reviewer evaluates and either approves or requests changes
    3. If changes requested, Writer revises
    4. Loop continues until approved or max iterations

    This demonstrates a simple but complete agent chaining pattern.
    """

    def __init__(self, max_iterations: int = 10):
        """Initialize the orchestrator.

        Args:
            max_iterations: Maximum number of write/review cycles.
        """
        self.state = SharedState()
        self.max_iterations = max_iterations

        # Create the two agents that will pass work to each other
        self.writer = WriterAgent("writer-1", self.state)
        self.reviewer = ReviewerAgent("reviewer-1", self.state, max_revisions=3)

        # Track execution history
        self.execution_log: list[dict[str, Any]] = []

    def submit_work(self, work_id: str, prompt: str) -> WorkItem:
        """Submit a new work item to the pipeline.

        Args:
            work_id: Unique identifier for this work.
            prompt: The content request/prompt.

        Returns:
            The created WorkItem.
        """
        item = WorkItem(id=work_id, content=prompt)
        self.state.add_work_item(item)
        self._log(f"Work submitted: {work_id}")
        return item

    def run(self) -> dict[str, Any]:
        """Run the orchestration loop until all work is complete.

        Returns:
            Summary of the orchestration run.
        """
        iteration = 0

        while iteration < self.max_iterations:
            iteration += 1
            self._log(f"=== Iteration {iteration} ===")

            # Check if any work remains
            pending = self.state.get_items_by_status(WorkStatus.PENDING)
            needs_revision = self.state.get_items_by_status(WorkStatus.NEEDS_REVISION)
            completed = self.state.get_items_by_status(WorkStatus.COMPLETED)

            if not pending and not needs_revision and not completed:
                self._log("No work remaining, orchestration complete")
                break

            # Run agents in sequence: Writer first, then Reviewer
            # Writer handles PENDING and NEEDS_REVISION
            if pending or needs_revision:
                self._log("Running Writer agent...")
                writer_results = self.writer.run()
                for result in writer_results:
                    self.execution_log.append({
                        "iteration": iteration,
                        "agent": "writer",
                        "result": result,
                    })

            # Reviewer handles COMPLETED items
            completed_after_write = self.state.get_items_by_status(WorkStatus.COMPLETED)
            if completed_after_write:
                self._log("Running Reviewer agent...")
                reviewer_results = self.reviewer.run()
                for result in reviewer_results:
                    self.execution_log.append({
                        "iteration": iteration,
                        "agent": "reviewer",
                        "result": result,
                    })

            # Check if all work is approved
            approved = self.state.get_items_by_status(WorkStatus.APPROVED)
            total_items = len(self.state.work_items)
            if len(approved) == total_items:
                self._log(f"All {total_items} items approved!")
                break

        return self._generate_summary()

    def _log(self, message: str) -> None:
        """Log orchestration events."""
        print(f"[Orchestrator] {message}")

    def _generate_summary(self) -> dict[str, Any]:
        """Generate a summary of the orchestration run."""
        approved = self.state.get_items_by_status(WorkStatus.APPROVED)
        pending = self.state.get_items_by_status(WorkStatus.PENDING)
        in_progress = self.state.get_items_by_status(WorkStatus.IN_PROGRESS)
        needs_revision = self.state.get_items_by_status(WorkStatus.NEEDS_REVISION)

        return {
            "total_items": len(self.state.work_items),
            "approved": len(approved),
            "pending": len(pending),
            "in_progress": len(in_progress),
            "needs_revision": len(needs_revision),
            "total_agent_actions": len(self.execution_log),
            "items": {
                item_id: {
                    "final_status": item.status.value,
                    "final_content": item.metadata.get("generated_content", ""),
                    "revisions": item.metadata.get("revision", 0),
                    "history_length": len(item.history),
                }
                for item_id, item in self.state.work_items.items()
            },
        }

    def print_item_history(self, work_id: str) -> None:
        """Print the full history of a work item for debugging."""
        item = self.state.get_work_item(work_id)
        if not item:
            print(f"Work item {work_id} not found")
            return

        print(f"\n=== History for {work_id} ===")
        for entry in item.history:
            print(f"  {entry['timestamp']}: {entry['agent']}")
            print(f"    {entry['from_status']} -> {entry['to_status']}")
            if entry.get('note'):
                print(f"    Note: {entry['note']}")
        print(f"\nFinal content:\n{item.metadata.get('generated_content', 'N/A')}")
