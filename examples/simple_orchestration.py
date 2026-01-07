#!/usr/bin/env python3
"""Example: Simple Two-Agent Orchestration

This example demonstrates how two agents can pass work to each other
in a feedback loop managed by an orchestrator.

The flow:
1. Submit work items to the orchestrator
2. Writer agent creates initial content
3. Reviewer agent evaluates and requests changes
4. Writer agent revises based on feedback
5. Loop continues until Reviewer approves

Key concepts demonstrated:
- Agent chaining: agents process work in sequence
- State management: SharedState tracks work items
- Feedback loops: agents can send work back to earlier stages
- Termination: clear conditions for when to stop

Run this example:
    cd /home/user/cc_forge
    python -m examples.simple_orchestration
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.orchestration.simple import SimpleOrchestrator


def main():
    print("=" * 60)
    print("Simple Two-Agent Orchestration Demo")
    print("=" * 60)
    print()

    # Create the orchestrator
    orchestrator = SimpleOrchestrator(max_iterations=10)

    # Submit work items
    print("Submitting work items...")
    orchestrator.submit_work("task-1", "Write a function to calculate fibonacci numbers")
    orchestrator.submit_work("task-2", "Create a class for managing user sessions")
    print()

    # Run the orchestration loop
    print("Starting orchestration loop...")
    print("-" * 60)
    summary = orchestrator.run()
    print("-" * 60)
    print()

    # Print summary
    print("=" * 60)
    print("ORCHESTRATION SUMMARY")
    print("=" * 60)
    print(f"Total items processed: {summary['total_items']}")
    print(f"Items approved: {summary['approved']}")
    print(f"Total agent actions: {summary['total_agent_actions']}")
    print()

    # Print details for each item
    for item_id, details in summary["items"].items():
        print(f"\n--- {item_id} ---")
        print(f"  Final status: {details['final_status']}")
        print(f"  Revisions: {details['revisions']}")
        print(f"  History entries: {details['history_length']}")

    # Show detailed history for first item
    print("\n" + "=" * 60)
    print("DETAILED HISTORY (task-1)")
    print("=" * 60)
    orchestrator.print_item_history("task-1")


if __name__ == "__main__":
    main()
