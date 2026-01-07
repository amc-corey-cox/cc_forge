"""Reviewer agent that reviews and provides feedback on content.

This agent processes COMPLETED work items, deciding whether to approve
them or send them back for revision.
"""

from typing import Any

from src.agents.base import BaseAgent
from src.common.state import SharedState, WorkItem, WorkStatus


class ReviewerAgent(BaseAgent):
    """Agent that reviews content and provides feedback.

    The Reviewer examines completed work and either approves it or
    requests revisions. This creates a feedback loop with the Writer.
    """

    def __init__(self, agent_id: str, state: SharedState, max_revisions: int = 3):
        """Initialize the reviewer.

        Args:
            agent_id: Unique identifier for this agent.
            state: Shared state container.
            max_revisions: Maximum revisions before auto-approve.
        """
        super().__init__(agent_id, state)
        self.max_revisions = max_revisions

    @property
    def role(self) -> str:
        return "reviewer"

    def can_process(self, item: WorkItem) -> bool:
        """Reviewer processes COMPLETED items."""
        return item.status == WorkStatus.COMPLETED

    def process(self, item: WorkItem) -> dict[str, Any]:
        """Review a completed work item.

        Args:
            item: The work item to review.

        Returns:
            Dict with review decision and feedback.
        """
        content = item.metadata.get("generated_content", "")
        revision = item.metadata.get("revision", 0)

        self.log(f"Reviewing: {item.id} (revision {revision})")

        # Perform review (in real system, would call LLM)
        review_result = self._review_content(content, revision)

        if review_result["approved"] or revision >= self.max_revisions:
            if revision >= self.max_revisions and not review_result["approved"]:
                self.log(f"Max revisions reached for {item.id}, auto-approving")
                review_result["note"] = "Auto-approved after max revisions"

            item.update_status(
                WorkStatus.APPROVED,
                self.agent_id,
                f"Approved: {review_result.get('note', 'Meets requirements')}"
            )
            return {
                "action": "approved",
                "item_id": item.id,
                "revision": revision,
                "feedback": review_result.get("note", ""),
            }
        else:
            # Request revision - this creates the feedback loop
            item.metadata["review_feedback"] = review_result["feedback"]
            item.update_status(
                WorkStatus.NEEDS_REVISION,
                self.agent_id,
                f"Needs revision: {review_result['feedback']}"
            )
            return {
                "action": "revision_requested",
                "item_id": item.id,
                "revision": revision,
                "feedback": review_result["feedback"],
            }

    def _review_content(self, content: str, revision: int) -> dict[str, Any]:
        """Review content and decide on approval.

        In a real implementation, this would call an LLM to analyze
        the content quality and provide structured feedback.
        """
        # Simulated review logic - approves after 2 revisions
        if revision >= 2:
            return {
                "approved": True,
                "note": "Content meets quality standards",
            }
        elif revision == 1:
            return {
                "approved": False,
                "feedback": "Add more detail and examples",
            }
        else:
            return {
                "approved": False,
                "feedback": "Content needs more structure and clarity",
            }
