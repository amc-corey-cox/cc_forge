"""CLI entry point for CC Forge."""

from __future__ import annotations

import click

from cc_forge import __version__


@click.group(invoke_without_command=True)
@click.version_option(__version__, prog_name="forge")
@click.pass_context
def main(ctx: click.Context) -> None:
    """CC Forge — Local-first AI development forge.

    Run `forge` with no arguments to start an interactive agent session
    in the current git repository.
    """
    if ctx.invoked_subcommand is None:
        ctx.invoke(run)


def _agent_choices() -> list[str]:
    """Return registered agent names."""
    from cc_forge.agents import REGISTRY
    return list(REGISTRY.keys())


@main.command()
@click.option("--repo", default=".", help="Path to git repository (default: current directory).")
@click.option("--agent", default="claude",
              type=click.Choice(list(_agent_choices())),
              help="Agent to use inside the container.")
@click.option("--passthrough", is_flag=True,
              help="Use remote API instead of local Ollama.")
@click.option("--claude", "claude_compat", is_flag=True, hidden=True,
              help="Deprecated alias for --passthrough with --agent claude.")
def run(repo: str, agent: str, passthrough: bool, claude_compat: bool) -> None:
    """Start an interactive agent session."""
    from cc_forge.agents import REGISTRY
    from cc_forge.config import load_config
    from cc_forge.session import start_session

    if claude_compat:
        if agent != "claude":
            raise click.UsageError("--claude can only be used with --agent claude")
        passthrough = True

    adapter = REGISTRY[agent]
    if passthrough and not adapter.supports_passthrough:
        raise click.UsageError(f"--passthrough is not supported for agent '{agent}'")

    cfg = load_config()
    start_session(cfg, repo_path=repo, agent=agent, adapter=adapter, passthrough=passthrough)


def _walk(cfg, repo: str, remote: str, kinds: tuple[str, ...]) -> None:
    from cc_forge.promote import walk_promotable

    walk_promotable(cfg, repo, remote, kinds, confirm=click.confirm, echo=click.echo)


@main.command()
@click.argument("number", type=int, required=False)
@click.option("--repo", default=".", help="Path to git repository (default: current directory).")
@click.option("--remote", default="origin",
              help="Git remote pointing at the GitHub destination (default: origin).")
def promote(number: int | None, repo: str, remote: str) -> None:
    """Promote a Forgejo PR or issue to GitHub.

    With NUMBER, promote that PR or issue directly (a number resolves to whichever
    it is). With no NUMBER, walk every promotable (open) issue and PR, confirming
    each.
    """
    from cc_forge.config import load_config
    from cc_forge.promote import promote_by_number

    cfg = load_config()
    if number is None:
        _walk(cfg, repo, remote, ("issue", "pr"))
    else:
        click.echo(promote_by_number(cfg, number, repo_path=repo, remote=remote))


@main.command(name="promote-pr")
@click.argument("pr", type=int, required=False)
@click.option("--repo", default=".", help="Path to git repository (default: current directory).")
@click.option("--remote", default="origin",
              help="Git remote pointing at the GitHub destination (default: origin).")
def promote_pr(pr: int | None, repo: str, remote: str) -> None:
    """Promote a Forgejo PR to GitHub. With no PR, walk promotable PRs."""
    from cc_forge.config import load_config
    from cc_forge.promote import promote_pull_request

    cfg = load_config()
    if pr is None:
        _walk(cfg, repo, remote, ("pr",))
    else:
        click.echo(promote_pull_request(cfg, pr, repo_path=repo, remote=remote))


@main.command(name="promote-issue")
@click.argument("issue", type=int, required=False)
@click.option("--repo", default=".", help="Path to git repository (default: current directory).")
def promote_issue(issue: int | None, repo: str) -> None:
    """Promote a Forgejo issue to GitHub. With no ISSUE, walk promotable issues."""
    from cc_forge.config import load_config
    from cc_forge.promote import promote_issue as do_promote_issue

    cfg = load_config()
    if issue is None:
        _walk(cfg, repo, "origin", ("issue",))
    else:
        click.echo(do_promote_issue(cfg, issue, repo_path=repo))


@main.command(name="pr-show")
@click.argument("pr", type=int)
@click.option("--forgejo-repo", "repo_name", default=None,
              help="Forgejo repo name (default: derive from --repo's origin).")
@click.option("--repo", default=".", help="Path to git repository (used to derive --forgejo-repo).")
def pr_show(pr: int, repo_name: str | None, repo: str) -> None:
    """Print a Forgejo PR's metadata as JSON (head, base, title, body)."""
    import json

    from cc_forge.config import load_config
    from cc_forge.git import get_repo_name, get_repo_root, is_git_repo
    from cc_forge.promote import pr_metadata

    if not repo_name:
        if not is_git_repo(repo):
            raise click.ClickException("Run inside a git repo or pass --forgejo-repo.")
        repo_name = get_repo_name(get_repo_root(repo))

    cfg = load_config()
    click.echo(json.dumps(pr_metadata(cfg, pr, repo_name)))


@main.command()
@click.option("--forgejo-repo", "repo_name", default=None,
              help="Forgejo repo name (default: derive from --repo's origin).")
@click.option("--repo", default=".", help="Path to git repository (used to derive --forgejo-repo).")
@click.option("--days", default=7, show_default=True, type=click.IntRange(min=0),
              help="Keep branches with a commit newer than this many days.")
@click.option("--apply", is_flag=True,
              help="Actually delete stale branches (default: dry run).")
def prune(repo_name: str | None, repo: str, days: int, apply: bool) -> None:
    """Prune stale Forgejo branches (no open PR, not recently active)."""
    from cc_forge.config import load_config
    from cc_forge.git import get_repo_name, get_repo_root, is_git_repo
    from cc_forge.prune import prune_branches, render_summary

    if not repo_name:
        if not is_git_repo(repo):
            raise click.ClickException("Run inside a git repo or pass --forgejo-repo.")
        repo_name = get_repo_name(get_repo_root(repo))

    cfg = load_config()
    result = prune_branches(cfg, repo_name, days=days, apply=apply)
    click.echo(render_summary(result))


@main.command()
def status() -> None:
    """Show running forge sessions."""
    from cc_forge.docker import list_forge_containers

    containers = list_forge_containers()
    if not containers:
        click.echo("No running forge sessions.")
        return
    for c in containers:
        click.echo(f"  {c['name']}  {c['status']}  ({c['repo']})")


@main.command()
@click.option("--all", "stop_all", is_flag=True, help="Stop all forge sessions.")
@click.argument("name", required=False)
def stop(name: str | None, stop_all: bool) -> None:
    """Stop forge sessions."""
    from cc_forge.docker import list_forge_containers, stop_container

    containers = list_forge_containers()
    if not containers:
        click.echo("No running forge sessions.")
        return

    if stop_all:
        for c in containers:
            stop_container(c["id"])
            click.echo(f"Stopped {c['name']}")
        return

    if name is None:
        click.echo("Specify a container name or use --all.")
        return

    for c in containers:
        if c["name"] == name or c["id"].startswith(name):
            stop_container(c["id"])
            click.echo(f"Stopped {c['name']}")
            return

    click.echo(f"No forge session matching '{name}'.")
