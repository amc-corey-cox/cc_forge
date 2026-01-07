"""Writer agent that creates or revises content.

This agent processes PENDING or NEEDS_REVISION work items, generating
or updating content that will be reviewed by other agents.
"""

from typing import Any

from src.agents.base import BaseAgent
from src.common.state import SharedState, WorkItem, WorkStatus


class WriterAgent(BaseAgent):
    """Agent that writes and revises content.

    The Writer handles the initial creation of content and any revisions
    requested by the Reviewer. It demonstrates how an agent can be called
    multiple times in a chain.
    """

    def __init__(self, agent_id: str, state: SharedState):
        super().__init__(agent_id, state)
        self._revision_count: dict[str, int] = {}

    @property
    def role(self) -> str:
        return "writer"

    def can_process(self, item: WorkItem) -> bool:
        """Writer processes PENDING and NEEDS_REVISION items."""
        return item.status in (WorkStatus.PENDING, WorkStatus.NEEDS_REVISION)

    def process(self, item: WorkItem) -> dict[str, Any]:
        """Process a work item by writing or revising content.

        Args:
            item: The work item to process.

        Returns:
            Dict with the generated/revised content and metadata.
        """
        revision_num = self._revision_count.get(item.id, 0)

        if item.status == WorkStatus.PENDING:
            self.log(f"Writing initial content for: {item.id}")
            item.update_status(WorkStatus.IN_PROGRESS, self.agent_id, "Starting to write")

            # Simulate content generation (in real system, would call LLM)
            generated_content = self._generate_content(item.content)
            item.metadata["generated_content"] = generated_content
            item.metadata["revision"] = 0

            item.update_status(WorkStatus.COMPLETED, self.agent_id, "Initial draft complete")
            return {
                "action": "created",
                "item_id": item.id,
                "content": generated_content,
                "revision": 0,
            }

        else:  # NEEDS_REVISION
            revision_num += 1
            self._revision_count[item.id] = revision_num
            self.log(f"Revising content for: {item.id} (revision {revision_num})")

            item.update_status(WorkStatus.IN_PROGRESS, self.agent_id, f"Starting revision {revision_num}")

            # Get feedback from metadata and revise
            feedback = item.metadata.get("review_feedback", "")
            current_content = item.metadata.get("generated_content", "")
            revised_content = self._revise_content(current_content, feedback)

            item.metadata["generated_content"] = revised_content
            item.metadata["revision"] = revision_num

            item.update_status(WorkStatus.COMPLETED, self.agent_id, f"Revision {revision_num} complete")
            return {
                "action": "revised",
                "item_id": item.id,
                "content": revised_content,
                "revision": revision_num,
                "addressed_feedback": feedback,
            }

    def _generate_content(self, prompt: str) -> str:
        """Generate initial content from a prompt.

        In a real implementation, this would call an LLM.
        """
        # Simulated content generation
        return f"[DRAFT] Content generated for: {prompt}"

    def _revise_content(self, current: str, feedback: str) -> str:
        """Revise content based on feedback.

        In a real implementation, this would call an LLM with the
        current content and feedback to generate improvements.
        """
        # Simulated revision
        return f"{current}\n[REVISED based on: {feedback}]"
