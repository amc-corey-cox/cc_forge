"""Prune stale Forgejo branches (no open PR, not recently active).

Forgejo is the agent's workspace: each session pushes a branch and usually
opens a PR. Once the PR is closed, merged, or abandoned, the branch lingers and
clutters the namespace. This prunes those leftovers while keeping anything still
in play. Closed/merged PR *records* are left untouched as historical reference.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import click
import httpx

from cc_forge.config import ForgeConfig
from cc_forge.forgejo import ForgejoClient, ForgejoError


@dataclass(frozen=True)
class BranchPlan:
    """A single branch's disposition."""

    name: str
    delete: bool
    reason: str


@dataclass(frozen=True)
class PruneResult:
    plans: list[BranchPlan]
    applied: bool
    deleted: list[str]
    failed: list[tuple[str, str]]  # (branch, error)


def _committed_at(branch: dict) -> datetime | None:
    """Parse a branch's last-commit timestamp, or None if unavailable."""
    ts = (branch.get("commit") or {}).get("timestamp")
    if not ts:
        return None
    try:
        parsed = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None
    # A timestamp without an offset would be naive; comparing it to the aware
    # cutoff raises TypeError. Assume UTC when Forgejo omits the offset.
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def plan_prune(
    branches: list[dict],
    open_pr_heads: set[str],
    default_branch: str,
    cutoff: datetime,
) -> list[BranchPlan]:
    """Decide, per branch, whether to keep or delete it.

    Kept: the default branch, any branch with an open PR, and any branch whose
    last commit is at or after ``cutoff``. Everything else is slated for
    deletion.
    """
    plans: list[BranchPlan] = []
    for branch in branches:
        name = branch["name"]
        if name == default_branch:
            plans.append(BranchPlan(name, False, "default branch"))
        elif name in open_pr_heads:
            plans.append(BranchPlan(name, False, "open PR"))
        elif (committed := _committed_at(branch)) is not None and committed >= cutoff:
            plans.append(BranchPlan(name, False, f"active since {committed.date()}"))
        else:
            plans.append(BranchPlan(name, True, "no open PR, stale"))
    return plans


def prune_branches(
    config: ForgeConfig,
    repo_name: str,
    *,
    days: int = 7,
    apply: bool = False,
    now: datetime | None = None,
) -> PruneResult:
    """Plan (and optionally apply) a prune of stale Forgejo branches.

    Read-only unless ``apply`` is True. Branches with open PRs and the default
    branch are never deleted, even under ``apply``.
    """
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)

    try:
        with ForgejoClient(config) as forgejo:
            owner = forgejo.get_current_user()
            default_branch = forgejo.get_repo(owner, repo_name)["default_branch"]
            branches = forgejo.list_branches(owner, repo_name)
            open_prs = forgejo.list_pull_requests(owner, repo_name, state="open")
            open_pr_heads = {pr["head"]["ref"] for pr in open_prs}

            plans = plan_prune(branches, open_pr_heads, default_branch, cutoff)
            deleted: list[str] = []
            failed: list[tuple[str, str]] = []
            if apply:
                for plan in plans:
                    if not plan.delete:
                        continue
                    try:
                        forgejo.delete_branch(owner, repo_name, plan.name)
                        deleted.append(plan.name)
                    except ForgejoError as e:
                        failed.append((plan.name, str(e)))
    except httpx.RequestError as e:
        raise click.ClickException(f"Forgejo unreachable at {config.forgejo_url}: {e}")
    except ForgejoError as e:
        raise click.ClickException(f"Forgejo: {e}")

    return PruneResult(plans=plans, applied=apply, deleted=deleted, failed=failed)


def render_summary(result: PruneResult) -> str:
    """Human-readable kept/deleted summary with per-branch reasons."""
    kept = [p for p in result.plans if not p.delete]
    doomed = [p for p in result.plans if p.delete]
    reasons = {p.name: p.reason for p in doomed}
    lines: list[str] = []

    lines.append(f"Kept ({len(kept)}):")
    for p in kept:
        lines.append(f"  = {p.name}  ({p.reason})")

    if result.applied:
        # Count what actually got deleted; failures are reported separately.
        lines.append(f"Deleted ({len(result.deleted)}):")
        for name in result.deleted:
            lines.append(f"  - {name}  ({reasons.get(name, '')})")
    else:
        lines.append(f"Would delete ({len(doomed)}):")
        for p in doomed:
            lines.append(f"  - {p.name}  ({p.reason})")

    if result.failed:
        lines.append(f"Failed ({len(result.failed)}):")
        for name, err in result.failed:
            lines.append(f"  ! {name}  ({err})")

    if not result.applied and doomed:
        lines.append("")
        lines.append("Dry run — re-run with --apply to delete.")

    return "\n".join(lines)
