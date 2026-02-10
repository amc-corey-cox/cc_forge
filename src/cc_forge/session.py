"""Orchestrates a forge session: infrastructure → Forgejo → agent container."""

from __future__ import annotations

from pathlib import Path

import click

from cc_forge.config import ForgeConfig
from cc_forge.docker import (
    attach_terminal,
    cleanup_container,
    ensure_infrastructure_running,
    run_agent_container,
)
from cc_forge.forgejo import ForgejoClient
from cc_forge.git import (
    add_remote,
    get_current_branch,
    get_repo_name,
    get_repo_root,
    has_remote,
    is_git_repo,
    push_to_remote,
)


def start_session(config: ForgeConfig, repo_path: str = ".", agent: str = "claude") -> None:
    """Run the full forge session flow."""
    path = Path(repo_path).resolve()

    # 1. Validate git repo
    if not is_git_repo(path):
        click.echo(f"Error: {path} is not a git repository.", err=True)
        raise SystemExit(1)

    repo_root = get_repo_root(path)
    repo_name = get_repo_name(repo_root)
    branch = get_current_branch(repo_root)
    click.echo(f"Repository: {repo_name} (branch: {branch})")

    # 2. Start infrastructure
    click.echo("Ensuring forge infrastructure is running...")
    ensure_infrastructure_running(config)

    # 3. Connect to Forgejo
    with ForgejoClient(config) as forgejo:
        if not forgejo.health_check():
            click.echo("Error: Forgejo is not reachable. Is forge infrastructure running?", err=True)
            raise SystemExit(1)

        owner = forgejo.get_current_user()
        click.echo(f"Forgejo user: {owner}")

        # 4. Ensure repo exists on Forgejo
        if not forgejo.repo_exists(owner, repo_name):
            click.echo(f"Creating repository {owner}/{repo_name} on Forgejo...")
            forgejo.create_repo(repo_name)

        clone_url = forgejo.get_repo_clone_url(owner, repo_name)

        # 5. Add forgejo remote if missing
        if not has_remote(repo_root, "forgejo"):
            # Build authenticated remote URL
            remote_url = clone_url
            if config.forgejo_token:
                remote_url = clone_url.replace(
                    "://", f"://{owner}:{config.forgejo_token}@"
                )
            add_remote(repo_root, "forgejo", remote_url)
            click.echo("Added 'forgejo' remote.")

        # 6. Push to Forgejo
        click.echo(f"Pushing {branch} to Forgejo...")
        try:
            push_to_remote(repo_root, "forgejo", branch)
        except Exception as e:
            click.echo(f"Warning: push failed ({e}). Continuing anyway.", err=True)

    # 7. Launch agent container
    click.echo(f"Starting {agent} agent container...")
    container_id = run_agent_container(
        config,
        repo_url=clone_url,
        branch=branch,
        repo_name=repo_name,
        agent=agent,
    )
    click.echo(f"Container started. Attaching terminal...")
    click.echo("---")

    # 8. Attach and wait
    try:
        attach_terminal(container_id)
    finally:
        click.echo("\n--- Session ended. Cleaning up container...")
        cleanup_container(container_id)

    click.echo("Done. Review changes in Forgejo at "
               f"{config.forgejo_url}/{owner}/{repo_name}")
