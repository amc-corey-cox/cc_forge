"""Orchestrates a forge session: infrastructure → Forgejo → agent container."""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

import click

from cc_forge.agents import AgentAdapter
from cc_forge.config import ForgeConfig
from cc_forge.docker import (
    cleanup_container,
    ensure_infrastructure_running,
    exec_agent,
    run_agent_container,
)

from cc_forge.forgejo import ForgejoClient
from cc_forge.git import (
    GitError,
    add_all,
    add_remote,
    commit,
    get_current_branch,
    get_remote_url,
    get_repo_name,
    get_repo_root,
    has_remote,
    init_repo,
    is_git_repo,
    push_to_remote,
    set_remote_url,
)


_LOCAL_REPOS_DIR = Path.home() / ".config" / "forge" / "local-repos"


def _excluded(path: Path) -> bool:
    """Whether *path* is kept out of the managed repo.

    Symlinks are dropped rather than followed: this command exists for files
    that must not leave the machine, and a link can resolve outside the source
    tree entirely.
    """
    return path.name.startswith(".") or path.is_symlink()


def _ignore_excluded(dirpath: str, names: list[str]) -> set[str]:
    """``shutil.copytree`` filter applying :func:`_excluded` at every level."""
    base = Path(dirpath)
    return {name for name in names if _excluded(base / name)}


def prepare_local_directory(source: Path) -> Path:
    """Turn a directory of loose files into a git repo for forge.

    Creates (or updates) a managed repo under
    ``~/.config/forge/local-repos/<name>-<hash>``, copies the source files into
    it, and commits any changes.  Returns the repo path.
    """
    if not source.is_dir():
        raise click.ClickException(f"Not a directory: {source}")

    # Deterministic name from full path so two dirs with the same basename
    # (e.g. ~/work/docs and ~/personal/docs) don't collide.
    path_hash = hashlib.sha256(str(source).encode()).hexdigest()[:8]
    repo_dir = _LOCAL_REPOS_DIR / f"{source.name}-{path_hash}"
    repo_dir.mkdir(parents=True, exist_ok=True)

    if not is_git_repo(repo_dir):
        init_repo(repo_dir)
        click.echo(f"Initialized local repo at {repo_dir}")

    # Clear existing non-hidden content so files deleted from source don't
    # linger in the managed repo across runs.
    for item in repo_dir.iterdir():
        if item.name.startswith("."):
            continue
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()

    # Copy source files into the repo (hidden entries and symlinks are
    # excluded at every level, not just the top).
    for item in source.iterdir():
        if _excluded(item):
            continue
        dest = repo_dir / item.name
        if item.is_dir():
            shutil.copytree(item, dest, ignore=_ignore_excluded)
        else:
            shutil.copy2(item, dest)

    add_all(repo_dir)
    commit(repo_dir, "Update from local directory")

    return repo_dir


def start_session(
    config: ForgeConfig,
    repo_path: str,
    agent: str,
    adapter: AgentAdapter,
    passthrough: bool = False,
    private: bool = False,
) -> None:
    """Run the full forge session flow.

    *private* creates the Forgejo repo as private -- used by ``forge local``,
    whose whole premise is files that must not be shared.
    """
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
            visibility = "private " if private else ""
            click.echo(f"Creating {visibility}repository {owner}/{repo_name} on Forgejo...")
            forgejo.create_repo(repo_name, private=private)
        elif private and not forgejo.get_repo(owner, repo_name).get("private"):
            # Pre-existing public repo: we don't silently change its visibility,
            # but a local-only session must not push into it unnoticed.
            click.echo(
                f"Warning: {owner}/{repo_name} already exists on Forgejo and is "
                "PUBLIC. Make it private in Forgejo before pushing private files.",
                err=True,
            )

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
    backend = "API pass-through" if passthrough else "local Ollama"
    click.echo(f"Starting {agent} agent container ({backend})...")
    container_id = run_agent_container(
        config,
        repo_url=clone_url,
        branch=branch,
        repo_name=repo_name,
        agent=agent,
        adapter=adapter,
        passthrough=passthrough,
    )
    click.echo(f"Container started. Launching {agent}...")
    click.echo("---")

    # 8. Exec agent interactively and wait
    try:
        exec_agent(container_id, adapter, config, passthrough=passthrough)
    finally:
        adapter.save_state(container_id, config, passthrough)
        click.echo("\n--- Session ended. Cleaning up container...")
        cleanup_container(container_id)

    click.echo("Done. Review changes in Forgejo at "
               f"{config.forgejo_url}/{owner}/{repo_name}")
