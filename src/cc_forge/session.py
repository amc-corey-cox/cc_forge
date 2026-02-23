"""Orchestrates a forge session: infrastructure → Forgejo → agent container."""

from __future__ import annotations

from pathlib import Path

import click

from cc_forge.config import ForgeConfig
from cc_forge.docker import (
    cleanup_container,
    ensure_infrastructure_running,
    exec_agent,
    run_agent_container,
    save_claude_credentials,
)

from cc_forge.forgejo import ForgejoClient
from cc_forge.git import (
    GitError,
    add_remote,
    get_current_branch,
    get_remote_url,
    get_repo_name,
    get_repo_root,
    has_remote,
    is_git_repo,
    push_to_remote,
    set_remote_url,
)


def start_session(
    config: ForgeConfig,
    repo_path: str = ".",
    agent: str = "claude",
    claude_passthrough: bool = False,
) -> None:
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

        # 5. Add forgejo remote if missing (unauthenticated URL — no token in .git/config)
        if not has_remote(repo_root, "forgejo"):
            add_remote(repo_root, "forgejo", clone_url)
            click.echo("Added 'forgejo' remote.")

        # 6. Push to Forgejo using a temporary authenticated URL
        click.echo(f"Pushing {branch} to Forgejo...")
        original_url = get_remote_url(repo_root, "forgejo")
        if config.forgejo_token:
            auth_url = clone_url.replace("://", f"://{owner}:{config.forgejo_token}@")
            set_remote_url(repo_root, "forgejo", auth_url)
        try:
            push_to_remote(repo_root, "forgejo", branch)
        except Exception as e:
            click.echo(f"Error: push to Forgejo failed: {e}", err=True)
            raise SystemExit(1)
        finally:
            # Best-effort restore so token doesn't persist in .git/config
            if config.forgejo_token:
                try:
                    set_remote_url(repo_root, "forgejo", original_url)
                except GitError:
                    click.echo("Warning: could not restore forgejo remote URL.", err=True)

    # 7. Launch agent container
    backend = "Claude API" if claude_passthrough and agent == "claude" else "local Ollama"
    click.echo(f"Starting {agent} agent container ({backend})...")
    container_id = run_agent_container(
        config,
        repo_url=clone_url,
        branch=branch,
        repo_name=repo_name,
        agent=agent,
        claude_passthrough=claude_passthrough,
    )
    click.echo(f"Container started. Launching {agent}...")
    click.echo("---")

    # 8. Exec agent interactively and wait
    try:
        exec_agent(container_id, agent, config, claude_passthrough=claude_passthrough)
    finally:
        if claude_passthrough:
            save_claude_credentials(container_id)
        click.echo("\n--- Session ended. Cleaning up container...")
        cleanup_container(container_id)

    click.echo("Done. Review changes in Forgejo at "
               f"{config.forgejo_url}/{owner}/{repo_name}")
